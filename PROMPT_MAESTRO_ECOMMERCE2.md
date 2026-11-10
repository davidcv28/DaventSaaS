# PROMPT MAESTRO — Ecommerce fase 2: stock con bloqueo pesimista + plantillas de cliente + cobertura de diseños

Sos el ORQUESTADOR de un grupo de subagentes trabajando sobre la rama `ECCOMMERCE-ADD` del repo `SaaS DAVENT` (raíz: `C:\Users\David\OneDrive\Escritorio\SaaS DAVENT`). Tu rol: dividir la tarea en tracks con ownership disjunto, lanzarlos en paralelo, revisar cada diff, correr migraciones/tests en serie, commitear y pushear por track. NO codeás los tracks vos mismo salvo fixes de integración menores.

## Contexto que YA existe (no re-implementar)

- Ecommerce completo fase 1 ya está en `ECCOMMERCE-ADD`: `customers` (JWT `customer_access`/`customer_refresh`, Google login, PII cifrada, `tokens_valid_after`), `cart`, `orders` (snapshot inmutable, state machine, tracking público por token opaco, comprobante no fiscal, arrepentimiento), `storepayments` (MP del vendedor, webhook HMAC, refunds con `select_for_update`), `memberships`, `legalpages`, `support`, notificaciones + mails.
- `Product.stock` (NULL = sin control) ya existe en `StoreApp/domains/catalog/models/models.py:83`. Descuento atómico al confirmar pago en `orders/services/payments.py::_decrement_stock` (UPDATE condicional `stock__gte=qty` + `F()`), conflicto registrado como `OrderEvent 'stock_conflict'`.
- Storefront: `StorePublicLayout` + `StoreAuthModal` (auth comprador), `StoreCartDrawer`, `StoreCheckoutView`, tracking público, `PlanSubscribe`. Plantillas Vue en `frontend/src/views/store/{raiz,mercado,gimnasio,impacto,indumentaria,moderntec,movimiento,sastreria}` (todas reusan Raíz). Patrones HTML en `StoreApp/domains/design/sources/*.html` servidos por `pattern_document.py` con `pattern_bridge.js` que inyecta CTAs de compra cuando `orders_enabled(store)`.
- Emails: `orders/services/mails.py` (eventos de pedido al comprador/dueño), `notify` domain con Celery. Clientes: `customers` ya manda mails de verificación/reset vía los servicios del dominio.
- Reglas: ver `AGENTS.md` — imágenes siempre WebP vía `normalize_image`, commits por track, respuestas cortas, no commitear `.env`/`venv`/`node_modules`/`dist`.

## Reglas de orquestación

1. Ownership de archivos DISJUNTO entre tracks paralelos. Si dos tracks necesitan el mismo archivo, el orquestador lo resuelve en integración.
2. Ningún subagente corre `migrate`, `makemigrations` de otra app, ni `manage.py test` global (test DB Postgres compartida — la suite corre en serie al integrar). Escriben código + tests; vos corrés.
3. Cada track: subagente `subagent_general` con prompt autocontenido (rutas exactas, contratos, qué NO tocar). Revisás el diff, corré `makemigrations`/`migrate` + tests del dominio + `ruff` (o lint del front), commiteás por track.
4. Frontend: todo componente nuevo sigue las convenciones de `frontend/src/views/store/raiz/` y `components/store/`. Templates HTML siguen el contrato `data-ds-*` de `pattern_bridge.js`/`pattern_document.py` (sanitización, CSP por nonce, sin `fetch` directo — postMessage `davent:ds-api`).
5. Verificación final con browser-automation (DOM real, no curl): login comprador, carrito, checkout, panel de cuenta, y los diseños corregidos en modo claro y noche.

---

## Track A — Backend: stock con bloqueo pesimista

**Archivos**: `StoreApp/domains/orders/services/checkout.py`, `payments.py`, `StoreApp/domains/catalog/` (modelo/serializer si hace falta), tests en `orders/tests.py` (+ tests de concurrencia).

Hoy el stock se valida en checkout sin reservar y se descuenta al pagar con UPDATE condicional — dos compradores simultáneos pueden crear ambos el pedido y el segundo queda `stock_conflict` ya pagado. Objetivo: cerrar la ventana de carrera.

- Checkout: dentro de `transaction.atomic()`, `select_for_update()` sobre las filas `Product` de los ítems (ordenado por pk para evitar deadlock), validar stock contra la fila lockeada. Re-evaluar si conviene reservar stock al crear el pedido (`reserved` counter o decremento inmediato con re-ingreso al cancelar/expirar) vs mantener descuento al pago con lock de fila — documentar la decisión en el docstring del servicio.
- `mark_order_paid`: mantener el UPDATE condicional dentro del mismo lock transaccional (ya hay `select_for_update` del pedido — extender a los productos).
- `cancel_order`/`expire_orders` y `refund`: si se adopta reserva, devolver stock exactamente una vez (idempotente por estado previo).
- Tests: dos checkouts concurrentes del último ítem (TransactionTestCase con threads o locks simulados), cancelación devuelve stock, pedido expirado libera reserva, refund NO re-suma (la mercadería la maneja el dueño fuera del sistema — mantener ese criterio salvo que el modelo reserve).

## Track B — Frontend: plantillas de autenticación de cliente

**Archivos**: `frontend/src/views/store/` (nuevas vistas `StoreLoginView`, `StoreRegisterView`, `StoreRecoverView` o extensión de `StoreAuthModal`), `frontend/src/api/customer*.js`, router de tienda, `pattern_bridge.js` (punto de entrada "Mi cuenta"/login en los documentos patrón).

- Hoy el auth de comprador vive en `StoreAuthModal` (modal). Convertirlo en experiencia completa: vistas dedicadas con tabs login/registro/recuperación, deep-link (`/<slug>/cuenta/login?next=...`), mismo tema/piel del template activo (tokens `--st-*`/`--sp-*`).
- Backend (si falta): mail de recuperación con token de un solo uso + endpoint reset; mail de bienvenida/verificación. Reusar `notify`/`mails` del dominio `customers` — verificar qué hay y completar lo que falte (esto puede quedar como Track B2 backend si el front lo necesita).
- `pattern_bridge.js`: inyectar entrada "Mi cuenta" / "Ingresar" en los documentos patrón junto al carrito, visible solo cuando `orders_enabled` — hoy los diseños no muestran login.

## Track C — Frontend: panel de cuenta del comprador

**Archivos**: `frontend/src/views/store/account/` (nuevo dir), `frontend/src/api/customer*.js`, rutas `/<slug>/cuenta/*`, nav del storefront.

Vista `/cuenta` del comprador dentro de la tienda (misma piel):
- Perfil (nombre, email, teléfono, direcciones si el modelo las tiene).
- Historial de compras: lista de sus pedidos con estado + link a tracking (`customer/orders/` ya existe).
- Suscripciones/membresías activas del cliente en esa tienda (dominio `memberships` — endpoint de "mis suscripciones"; si falta, agregarlo).
- Comprobantes (receipts no fiscales) descargables/imprimibles por pedido.
- Requiere sesión `customer_*`; si no hay sesión → redirect a login con `next`.

## Track D — Frontend: página de carrito completa

**Archivos**: `frontend/src/views/store/StoreCartView.vue` (nueva ruta `/<slug>/carrito`), reuso del cart store existente.

- Hoy el carrito es un drawer (`StoreCartDrawer`). Agregar página completa pre-confirmación: líneas con foto/qty/precio unitario, edición de cantidades (validando stock expuesto por el endpoint), quitar ítems, subtotales, estimación de envío/método, CTA a checkout, estado vacío. El drawer sigue existiendo para compra rápida.
- `pattern_bridge.js`: el botón carrito inyectado debe ofrecer "Ver carrito" (página) además del drawer.

## Track E — Frontend: plantilla de comprobante/factura

**Archivos**: `frontend/src/views/store/StoreReceiptView.vue` o sección en cuenta; backend si hace falta endpoint de render.

- Comprobante no fiscal del pedido ya existe (endpoint `receipt`). Crear la vista imprimible para el comprador: encabezado tienda, datos del pedido, ítems, totales, leyenda "no es factura fiscal — la factura la emite el comercio", botón imprimir. Misma piel.
- Si el vendedor adjunta factura fiscal real (campo `invoice_ref`/archivo) mostrarla/descargarla.

## Track F — Auditoría y corrección de diseños

**Archivos**: `StoreApp/domains/design/sources/*.html`, `StoreApp/domains/design/seed_data.json`, `assets/store-*.css`, `pattern_bridge.js`, `seed.py`.

Barrido de los 21+ patrones + 8 templates Vue:
- Ecommerce: verificar que cada diseño con catálogo muestre CTA de compra, carrito Y entrada de login/cuenta (track B). Los que no tengan → agregar markup `data-ds-*`/`ds-product` faltante o corregir la inyección del bridge.
- Contraste: botón de modo noche, íconos (carrito, cuenta, menú, WhatsApp) que no se ven por hover o fondo del mismo brillo/oscuridad que el elemento. Corregir con tokens del tema (`--st-*`), `color-mix` o bordes/sombras de contraste — caso por caso con screenshot en ambos modos.
- QA obligatorio: screenshot de cada diseño tocado en claro Y noche antes de commitear (browser-automation).

## Track G — Plantillas faltantes restantes

**Archivos**: según hallazgo.

Cubrir lo que el usuario listó "y agrega las que me esté olvidando":
- Página de confirmación de pedido (post-checkout success con link a tracking y a "mis pedidos").
- Tracking público ya existe — verificar que tenga vista con la piel de la tienda (no pantalla cruda).
- Formulario de arrepentimiento/devolución ya existe — verificar accesibilidad desde la cuenta del comprador (Track C) y del mail.
- Página de suscripción a membresías (`PlanSubscribe` existe — verificar entrada visible en diseños).
- Contacto/soporte al vendedor ya existe — verificar acceso desde cuenta.
- Notificaciones al comprador (si aplica: bandeja o mails — decidir alcance mínimo).

---

## Integración y cierre (orquestador)

1. Serie: `makemigrations` → `migrate` → tests de cada dominio tocado (`manage.py test StoreApp.domains.orders`, `customers`, `catalog`, `design`, `stores`) → `ruff check` → `vite build` (con `TMP` local en Windows).
2. Browser QA final: login/registro/recupero de comprador, carrito página + drawer, checkout, cuenta (perfil/pedidos/membresías/comprobantes), 2-3 diseños corregidos en claro y noche.
3. Actualizar `PLAN_ECOMMERCE.md` y `AGENTS.md` con lo nuevo. Commit por track, push al final.
4. Respetar el límite legal: DAVENT no vende, no factura por el comercio, no toca fondos — nada de lo nuevo puede violarlo.
