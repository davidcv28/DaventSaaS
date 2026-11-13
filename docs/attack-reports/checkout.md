# Attack report — Checkout / Carrito / Pedidos

Fecha: 2026-11-13. Entorno local (`manage.py runserver` :8000, SQLite + cache vivo).
Superficie atacada: `POST/GET /api/stores/public/<slug>/orders/*`, `/api/cart/<slug>/*`,
`/api/customer/orders/*`. Tiendas: `davent` (vendible), `mt-qa` (vendible), `vertice`/`mi-qa` (no vendibles).
Método: requests reales con JWT de comprador minteados en shell (`issue_customer_tokens`),
customers descartables `atk*/race*@test.local` creados solo para la prueba.

**Resultado global: el área resiste bien. Sin bypass de captcha, sin IDOR, sin duplicación de
pedidos, sin sobreventa de stock, sin precios manipulables.** Hallazgos concretos abajo.

## Tabla de hallazgos

| ID | Superficie | Ataque | Esperado | Obtenido | Severidad | Ubicación |
|----|-----------|--------|----------|----------|-----------|-----------|
| F-01 | Proof upload | Cualquiera con el `tracking_token` (credencial pública que viaja en mails/WhatsApp/URL) puede **reemplazar** el comprobante del comprador (`update_or_create` OneToOne). Subí PNG, luego lo reemplacé anónimamente → 201 ambos. Un tercero que vea el link (mail forward, screenshot) puede pisar el comprobante legítimo con basura antes de que el dueño lo revise, o quemar cuota de storage del plan (4 MB/subida, 10/h por IP — bypasseable rotando IPs). | Reemplazo solo por el comprador dueño o imposibilidad de re-subir una vez subido | `POST /proof/` anónimo → 201 `proof_uploaded:true` dos veces seguidas sobre `orders/qqLu…/proof/` | **media** | `StoreApp/domains/orders/views/public.py:207-269` (`PublicOrderProofView`, `authentication_classes=[]`) |
| F-02 | Address | `line1` con `<script>alert(1)</script><img src=x onerror=alert(2)>` se persiste **crudo** en `shipping_address` (JSONField) y se devuelve verbatim en `GET /orders/<token>/` y `/receipt/` (200). Es stored-XSS latente: seguro hoy solo porque el front escapa (Vue); cualquier render futuro como HTML (recibo PDF, mail al vendedor, panel del dueño con v-html) lo ejecuta. El panel del dueño (`StoreOrderDetailSerializer`) también lo sirve crudo. | Sanitizar o al menos strip de `<>` en el snapshot | 201 y tracking devuelve el payload intacto | **media** | `services/checkout.py:202-216` (`_address_snapshot`, solo strip+truncate) |
| F-03 | Items | `qty: 1.9` y `product_id: 817.5` se **truncan silenciosamente** vía `int()` → pedido creado con qty 1 / producto 817 (201). No hay validación de entero estricto. Un cliente que mande `qty: 99.9` paga por 99 (a favor del atacante no hay gran abuso, pero es input laxo; `qty: 0.5` → `int(0.5)=0` → 400 por suerte). | 400 por tipo inválido | 201 PED-0011 (`qty:1`) y PED-0012 | **baja** | `services/checkout.py:151-156` (`_merge_lines._add`: `int(raw_id)`, `int(raw_qty)`) |
| F-04 | 500 transitorio | Un `POST /orders/` con `address.line1` XSS + campos overlong devolvió **500 genérico** una vez; al reintentar el payload idéntico → 201. No reproducible vía test client (201 + tarea de mail OK). Probable `sqlite3: database is locked` transitorio (eager Celery + dev server multithread) — el request no dejó pedido creado (no hay PED huérfano). Riesgo real: si el 500 ocurre post-commit en otro path, el cliente reintenta y duplica (mitigado por idempotency_key si el front la manda). | Nunca 500 | 1× `500 {'detail':'Error interno del servidor…'}` | **baja** (transitorio, sin evidencia de corrupción) | no localizado; revisar logging de excepciones del server en dev |
| F-05 | Throttle create | `OrderCreateThrottle` = `ResilientUserRateThrottle` 10/h **por usuario**. Confirmado 429 tras ~10 POSTs. Un atacante con N cuentas de comprador (registro abierto) multiplica el límite — cada cuenta tiene su bucket. El captcha sigue exigiéndose por request, así que el costo de crear pedidos falsos es lineal pero no bloqueado. | Rate por IP además de por user | 429 `Solicitud fue regulada… en 3094 segundos` (además leakea el tiempo de espera, info menor) | **baja** | `views/public.py:63-67` |
| F-06 | Receipt público | `GET /orders/<token>/receipt/` expone datos fiscales completos del **vendedor** (CUIT, domicilio fiscal, condición) a cualquiera con el token. Es decisión de diseño (el comprador la necesita para el comprobante), pero el token se comparte fácil (va en texto plano en el mail/WhatsApp del pedido). | OK por diseño; documentado | 200 con `seller.cuit`, `fiscal_address`, etc. | **baja** (info disclosure aceptado) | `services/checkout.py:584-633` |
| F-07 | Tracking | `GET /vertice/orders/<token>/` devuelve el pedido completo (nombre, dirección, totales, PII mínima) aunque la tienda ya **no puede vender** (`orders_enabled=False`). Es intencional (docstring: el seguimiento sobrevive al apagado de ventas) — anotado para que quede constancia de que es decisión, no bug. | — | 200 | **info** | `views/public.py:173`, `checkout.py:44-49` |

## Ataques que NO funcionaron (verificado con evidencia)

| ID | Ataque | Resultado |
|----|--------|-----------|
| IDM | Retry mismo `idempotency_key` mismo user → 200 mismo `tracking_token` (PED-0007). Misma key otro customer → 400 `ya fue usada por otra compra`. Key >80 chars → 400 serializer. Key vacía/espacios → crea pedido nuevo (correcto: no hay key que respetar). Misma key en otra tienda (mt-qa) → crea su propio pedido (PED-0001, scope por store OK). **3 requests paralelos misma key** → 1×201 + 2×200 con el mismo token, un solo PED-0016. |
| RACE stock | 3 checkouts paralelos `qty=5` sobre producto con `stock=5` → 1×201 (PED-0015), 2×400 `Stock insuficiente … quedan 0`. Reserva blanda + `select_for_update` funciona. |
| RACE cart | 2 checkouts `use_cart` paralelos del mismo carrito → 1×201 + 1×400 `El pedido no tiene items` (error confuso pero correcto: el carrito se vacía en el atomic del ganador). |
| QTY | `0`, `-5`, `101`, `999999`, `10**19` → 400. `'abc'`, `null`, sin qty → 400. Carrito: `0/-1/999/1.5/'x'` → 400 por serializer. |
| XST | `product_id` de otra tienda (312 de vertice en davent) → 400 `no disponible`. Inexistente → 400. `is_exclusive` sin membresía → 400. `is_active=False` queda fuera del queryset. Exclusivo en carrito → 400. |
| PRC | `unit_price`/`total`/`subtotal` en el body → ignorados; el pedido salió con el total server-side (10360.00). |
| CAPTCHA | Replay del mismo challenge → 400 (nonce quemado, reclamo atómico). Challenge de mt-qa usado en davent → 400 (slug en payload firmado). Challenge forjado con `t` viejo (firmado con la SECRET_KEY real) → 400 por `max_age`. Respuesta <3s → 400 (anti-bot). 6 intentos malos → challenge quemado a los 5. `answer` int/float/`'1e2'`/unicode-árabe/emoji/espacios → 400 sin excepción. `null` → 400 serializer. |
| PAY/SHP | `payment_method` transfer/cash/mp en davent (deshabilitados) → 400 `no tiene habilitado ese método`. `'bitcoin'`/`''`/null → 400. `shipping_method:'drone'` → 400. `home` sin address → 400 por campo. `address_id` ajeno/inexistente → 400 `no existe o no es tuya` (IDOR cerrado). `address` string en vez de dict → 400 limpio. `address.line1` dict anidado → `str()` lo aplana (no 500). |
| CART | Sin JWT → 401. Producto de otra tienda → 400. Tienda no vendible → 404. `use_cart`+`items` mezclados → solo entra el carrito (items ignorados por diseño). Carrito se vacía post-checkout. Carrito vacío → 400. |
| TRK | Token aleatorio → 404. Token de vertice bajo `/davent/` → 404 (scope por store). `/orders//` → 404. GET/PUT sobre colección → 405. `/captcha/` de tienda inexistente/no vendible → 404 (no oráculo de existencia de tienda). |
| AUTH | Sin JWT → 401. JWT basura → 401. JWT `auth.User` (owner) → 401 (`token_type` distinto). Customer desactivado con token vivo → 401. Detalle `/customer/orders/<token ajeno>/` → 404 (no revela existencia). Honeypot `website` lleno → 400 genérico. |
| PROOF | `.exe` → 400 formato. `.svg` con script → 400 formato. PNG trucho (magic bytes falsos) → 400 `no es una imagen válida`. >4 MB → 400. Sin archivo → 400. Pedido DELIVERED → 400 `no admite comprobante`. PNG válido → 201, convertido a WebP y subido a R2 con URL firmada privada. |

## Notas

- La respuesta 429 incluye el tiempo exacto de espera (`en 3094 segundos`) — fingerprint menor.
- El tracking público (F-07/F-06) asume que `tracking_token` (urlsafe, ~256 bits) es credencial suficiente; consistente en todo el dominio, pero cualquier fuga del link (mail reenviado, analytics, referrer) expone nombre + dirección del comprador y permite pisar el comprobante (F-01).
- El descuento observado en las respuestas (`list 14800 → unit 10360`) corresponde a un descuento de catálogo vigente, no a un bug de pricing: `member_discount_percent` da 0 para customers nuevos.

## Repro

Scripts de ataque usados (scratch, fuera de git): `pwtmp/attack.py`, `pwtmp/attack2.py`, `pwtmp/attack3.py`, `pwtmp/race.py`. Resultados crudos en `pwtmp/results*.json`.
