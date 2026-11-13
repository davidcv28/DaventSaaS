# Attack report — Concurrencia y Stock (cart / orders / catalog)

Fecha: 2026-11-13. Entorno local (SQLite, `manage.py shell`, threads con
`concurrent.futures` pegándole a `create_order`/`mark_order_paid`/`add_item`
directo — cada thread con su propia conexión DB). Tienda: `mt-qa` (vendible,
payment defaults: transfer/whatsapp). Customers `race*@test.local`, productos
`RACE-*`/`R2-*` descartables.

**Caveat metodológico**: en SQLite `select_for_update` es no-op, pero el write
lock de la base serializa las transacciones igual → los resultados de
"un solo ganador" son representativos. El hallazgo S-01 (borrado fantasma de
línea de carrito) NO es reproducible en SQLite por la granularidad de locks
(la transacción lectora retiene SHARED desde el primer SELECT): se demostró
insertando la línea dentro de la misma ventana transaccional, que es
exactamente lo que Postgres permite con un request concurrente.

**Resultado global: la reserva blanda funciona bien — sin sobreventa
reproducible, pagos y vencimientos idempotentes y serializados.** Los
hallazgos son de ventanas lógicas, no de corrupción de stock.

## Tabla de hallazgos

| ID | Escenario | Esperado | Obtenido (evidencia) | Severidad | Ubicación |
|----|-----------|----------|----------------------|-----------|-----------|
| S-01 | **Item agregado al carrito mientras el checkout corre** (`use_cart`). `create_order` lockea la fila de `Cart` con `select_for_update` (checkout.py:388) y el comentario afirma que "un item agregado entre el fetch y el delete() no se pierde sin entrar al pedido". Pero `add_item`/`update_item`/`remove_item` NUNCA toman ese lock: en Postgres el `INSERT` del otro request commitea entre `_merge_lines` (línea 390) y `cart.items.all().delete()` (línea 453) → la línea nueva se borra sin haber entrado al pedido. El comprador agregó un producto, el pedido salió sin él y el carrito quedó vacío: pérdida silenciosa. | Item incluido en el pedido o conservado en el carrito | Demo: línea `p2 x3` creada post-merge dentro de la ventana → `pedido contiene [(p1,2)]`, `carrito restante []`. El lock del carrito es inútil para escritores del carrito. | **media** | `StoreApp/domains/orders/services/checkout.py:387-389,453` (lock sin contraparte) + `StoreApp/domains/cart/services/cart.py:131-168` (writes sin lock ni atomic) |
| S-02 | **Pagar un pedido vencido por tiempo antes de que corra el cron**. `mark_order_paid` solo verifica `status == PENDING_PAYMENT`, jamás `expires_at`. Un pedido con `expires_at` ya pasado (cron aún no corrió — ventana = intervalo del cron, potencialmente minutos/horas) puede ser confirmado por el dueño (`confirm-payment/`) o acreditado por webhook MP → pasa a PAID/PACKING pese a estar vencido. El endpoint de preferencia MP sí chequea `expires_at` (storepayments/views/checkout.py:82), así que la inconsistencia es solo del path de acreditación. | Pago rechazado/flaggeado (`paid_after_close`) si `expires_at` ya pasó | `expires_at = now-1h`, `mark_order_paid` → `status: PACKING`, stock descontado (5→3), evento `paid` normal — nunca `paid_after_close` porque el status seguía PENDING. | **media-baja** | `StoreApp/domains/orders/services/payments.py:151-155` (falta check de `expires_at` vs `timezone.now()`) |
| S-03 | **Pedido vencido-por-tiempo pero aún PENDING retiene la reserva blanda** → falso agotado. `claimed` cuenta OrderItems de `PENDING_PAYMENT` sin mirar `expires_at` (checkout.py:296-301): entre el vencimiento y la corrida de `expire_orders` el stock queda bloqueado y nuevos checkouts reciben "Stock insuficiente" aunque el pedido esté muerto. Con cron lento o caído, un carrito abandonado bloquea el producto indefinidamente. | La reserva expira con `expires_at` (filtrar `expires_at > now` en el aggregate, o checkout propio que venza al pedido zombie) | `o1` qty=5 vencido hace 1h (status PENDING) → checkout de qty=5 **y de qty=1** → `Stock insuficiente … quedan 0`. | **media-baja** | `StoreApp/domains/orders/services/checkout.py:297-300` (falta `order__expires_at__gt = now`) |
| S-04 | **El check de stock del carrito ignora la reserva blanda**: `_check_stock` compara contra `product.stock` físico, no contra `stock - claimed`. El carrito deja cargar qty=5 con disponibilidad real 0 (todo comprometido por pedidos pendientes) → el comprador arma el pedido y recién falla en checkout. | Carrito muestra disponibilidad real (stock − reservas) | `add_item qty=5` con claimed=5/stock=5 → OK, `item qty 5`; `create_order` sobre ese carrito → `Stock insuficiente: quedan 0`. | **baja** (UX/engaño, no oversell) | `StoreApp/domains/cart/services/cart.py:118-128` |
| S-05 | **Corrección manual de stock del dueño con pedidos pendientes** → el pago queda PAID sin mercadería. Diseño aceptado (docstring payments.py:98-101): pedido qty=5, dueño baja stock a 3, `mark_order_paid` → `PACKING` + evento `stock_conflict` + stock=3 (la línea no se descontó). El comprador pagó y el pedido avanza a preparación pese al faltante. | — (documentado; anotado para que quede constancia) | `status: PACKING`, `stock: 3`, eventos `['created','paid','packing','stock_conflict']`. | **baja** (flujo residual documentado) | `StoreApp/domains/orders/services/payments.py:120-131` |

## Ataques que NO funcionaron (verificado con evidencia)

| ID | Ataque | Resultado |
|----|--------|-----------|
| R-1 | 6 checkouts paralelos `qty=1` sobre `stock=3`, customers distintos | 3×`ok` (PED-0006/7/8) + 3×`400 Stock insuficiente … quedan 0`. `claimed=3`, sin sobreventa. La reserva blanda cubre carritos/customers ajenos: `claimed` agrega OrderItems PENDING de TODA la tienda bajo `select_for_update` de Product (checkout.py:282-311). |
| R-2 | 2 customers compiten por `stock=1` en simultáneo | 1×ok + 1×400. Se serializan bien bajo el lock de Store→Product. |
| R-6 | `expire` vs `mark_order_paid` concurrente sobre el mismo pedido | Resultados `['expired','EXPIRED']` — el segundo ve el estado transicionado (select_for_update de la fila de Order serializa; sin doble evento ni pago-zombie). |
| R-8 | `cancel_order` vs `mark_order_paid` concurrente | `[ValidationError, PACKING]` — el cancel revalidó TRANSITIONS bajo lock y rechazó. Sin estado inconsistente. |
| R-11 | Doble `mark_order_paid` concurrente del mismo pedido | Ambos devuelven `PACKING`, **1 solo** evento `paid`, stock descontado una vez (5→3). Idempotente. |
| R-12 | `is_exclusive` comprado por 2 customers sin membresía | Ambos 400 `exclusivo para miembros`. El check corre dentro del atomic de `_resolve_lines` (checkout.py:306-307). Con membresía válida ambos comprarían — exclusividad es por acceso, no por unidad (diseño). |
| R-7 | 2 `add_item` paralelos mismo producto (qty 2 y 4) | Ambos ok, una sola línea `qty=2` (last-writer-wins; `uq_cartitem_cart_product` + `get_or_create` — sin duplicados ni 500). El qty absoluto hace que no haya suma corrupta. |
| — | Locks anidados (Store→Order en cancel/expire, Store→Cart→Product en checkout, Order→Product en mark_paid) | Sin ciclos de deadlock identificables: quien lockea Store lo hace primero; `mark_order_paid` nunca pide Store/Order después de tenerlos. |

## Notas

- `update_item`/`remove_item` tampoco toman lock ni atomic (cart.py:149-168): un
  PATCH de qty durante el checkout se pierde igual que S-01 (misma raíz).
- Descuentos/campañas: `_price_lines` relee `running_discounts_of(store)` dentro
  del atomic (checkout.py:323) — un descuento que expira o se borra entre el
  precio mostrado y el POST cambia el total cobrado. Es TOCTOU inherente de
  e-commerce (el snapshot correcto es el del checkout); sin crash ni FK rota.
- `_payment_method_allowed` se valida ANTES del atomic sobre la instancia
  `store` de la vista (checkout.py:375-376): si el dueño deshabilita el método a
  mitad del checkout, el pedido igual sale con él. Ventana ínfima, bajo impacto.
- En SQLite toda esta superficie queda serializada por el write lock global —
  los locks de fila documentados solo se ejercen en Postgres (prod). Los tests
  de concurrencia del repo (tests.py:593-601) cubren stock_conflict; S-01/S-02/
  S-03 no tienen test.

## Repro

Scripts usados (scratch, fuera de git): `pwtmp/race_stock.py`, `pwtmp/race_stock2.py`
(correr con `venv/Scripts/python.exe manage.py shell -c "exec(open('pwtmp/race_stock.py',encoding='utf-8').read())"`).
