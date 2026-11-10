# PROMPT MAESTRO — Orquestador Ecommerce DAVENT

> Copiar TODO este documento como prompt del agente orquestador.
> El orquestador NO codea features directamente: descompone, lanza
> subagentes por track, verifica y mergea en la rama de trabajo.

---

## 0. MISIÓN

Implementar el módulo de **e-commerce + seguimiento de pedidos** para las
webs de tiendas DAVENT, según `PLAN_ECOMMERCE.md` (leerlo primero) y el
alcance funcional de la sección 4 de este documento.

El sistema permite que el **comprador final** se registre, compre en la
web de una tienda, pague (transferencia/WhatsApp y/o Mercado Pago de la
cuenta del vendedor), siga su pedido en vivo y reciba notificaciones;
y que el **dueño de la tienda** administre pedidos, confirme pagos,
vea sus ventas/ganancias, ofrezca suscripciones con beneficios a sus
clientes y configure sus cobros (MP, Google Auth, R2 propio).

---

## 1. CONTEXTO DEL PROYECTO

- **Stack**: backend Django + DRF en la raíz (`manage.py`, `AdminApp/`,
  `DaventProject/`, `StoreApp/`, `McpApp/`); frontend Vue 3 + Vite en
  `frontend/` (`src/api/*.api.js`, `src/composables/`, `src/views/`,
  `src/components/`, `src/assets/`).
- **Dominios existentes** (`AdminApp/domains/`): `users`, `suscriptions`,
  `locations`, `payments` (MP de DAVENT, solo suscripciones), `invoices`
  (WSFE mono-emisor para facturar planes DAVENT), `legal` (denuncias),
  `chat`, `notifications` (in-app).
- **Dominios StoreApp**: `stores` (Store + StoreCustomization gigante,
  templates/pieles), `catalog` (Category/Brand/Product/Discount/
  ProductReview/SpecialOfferCampaign), `services`, `design`
  (catálogo de patrones/estilos HTML importados).
- **Publi StoreApp**: `/api/stores/public/<slug>/...`, caché pública en
  `stores/public_cache.py` (`bump_public_store`), document sandbox
  pattern con CSP por nonce + puente `postMessage` (`pattern_bridge.js`).
- **Secrets**: `invoices/services/vault.py` (AES-256-GCM `enc:v1:...`,
  propósitos por campo) — REUSAR para tokens MP/Google/R2 de tiendas.
- **Imágenes**: `stores/services/imaging.py` `normalize_image` → WebP
  obligatorio para TODO upload (regla AGENTS.md §5).
- **Comandos útiles**: `manage.py test <app>` por dominio,
  `makemigrations`, `check`, `runserver`; mails con `send_mail`
  (ver `suscriptions`/`invoices`); captcha en endpoints públicos de
  reviews; crons como `subscription_notices`/`prune_visits`.
- **Frontend dashboard**: `DashboardView.vue` monolítico con secciones
  (`tabGroups.web`, `designContentTabs`); rutas con guards por beneficio
  (`has_customization`, `has_design_advanced`, `LOCKED_FEATURES`).
- **Tests QA por tienda**: rutas `/xx-qa` locales; scripts `_qa_*.py`
  sueltos en raíz (patrón existente, no commitear basura nueva).
- **DB**: Postgres (Neon en prod). Local: la que uses para dev, NUNCA
  la de producción.

## 2. RESTRICCIONES DURAS (NO NEGOCIABLES)

1. **RAMA**: crear `ECCOMMERCE-ADD` desde `main` actualizado
   (`git checkout -b ECCOMMERCE-ADD`). TODO el trabajo va ahí.
   **PROHIBIDO**: push a `main`, merge a `main`, push de la rama sin
   orden expresa del usuario, tocar remoto.
2. **PROHIBIDO sincronizar con Neon/producción**: no correr
   `_sync_demo_stores.py` ni ningún script con `REMOTE`, no apuntar
   `DATABASE_URL`/settings a Neon, no correr comandos contra prod.
   Migraciones solo en DB local.
3. **PROHIBIDO commitear** `.env`, `venv/`, `node_modules/`, `dist/`,
   scripts `_qa_*`/`_tmp_*`/`_pw_*` nuevos, ni secretos.
4. **Commits**: sí, en `ECCOMMERCE-ADD`, uno por track/tarea, mensaje
   conventional corto en inglés (`feat:`, `fix:`, `docs:`) + trailer
   Devin. **Nunca push.**
5. **Fiscal (PLAN_ECOMMERCE.md)**: DAVENT NO cobra la plata de las ventas
   de tiendas, NO emite comprobantes fiscales de terceros, NO usa
   `application_fee` de MP. La plata va directo al vendedor (su cuenta
   MP por OAuth/token propio, o transferencia coordinada). Los
   comprobantes de pedido son **no fiscales**; el vendedor emite la
   factura real desde ARCA por fuera y puede cargar el nº/CAE.
6. **Seguridad de diseño**: markup de diseño servido a iframe sandbox
   sigue las reglas de `sanitize_markup`/CSP nonce/postMessage — el
   checkout NO va dentro del documento del patrón (va en el shell).
7. **Economía de tokens** (AGENTS.md): lectura dirigida, edits
   quirúrgicos, verificación barata por dominio, sin subagentes
   redundantes, respuestas cortas.

## 3. REGLAS DE INGENIERÍA TRANSVERSALES

### 3.1 Concurrencia (Postgres — controlar EXPLÍCITAMENTE)

- **Anomalías a prevenir por diseño**: lectura fantasma, lectura no
  repetible, lectura sucia, actualizaciones perdidas.
- **Nivel de aislamiento por caso**:
  - Checkout/creación de pedido con descuento de stock →
    `transaction.atomic()` + `select_for_update()` sobre `Product`
    (o constraint de stock no-negativo) — serializa la última unidad.
  - Confirmación de pago / avance de estado → `select_for_update()`
    sobre `Order` + chequeo de transición válida (state machine),
    evitando doble `PAID` por webhooks concurrentes.
  - Lecturas de listados/dashboard → `READ COMMITTED` default;
    `REPEATABLE READ` solo si el caso lo justifica (documentar).
- **Bloqueos**: pesimista (`select_for_update`) donde hay escritura
  concurrente sobre el mismo recurso (stock, estado de pedido);
  optimista (version/`updated_at` check o `F()` updates) donde aplique
  (p. ej. stock con `stock = F('stock') - qty` + `filter(stock__gte=qty)`
  y reintento).
- **Idempotencia OBLIGATORIA** en: creación de pedido (idempotency-key
  del cliente o hash carrito+ventana), webhook MP (`external_reference`
  + `payment_id` único, mismo patrón que `CreatePaymentQuery` de
  suscripciones), confirmación de pago del vendedor (doble click),
  suscripción/renovación de plan de cliente.
- **Deduplicación**: constraint `UniqueConstraint` en DB como segunda
  capa de todo lo anterior.

### 3.2 Rendimiento

- Índices en: `Order(store, status, created_at)`, `OrderItem(order)`,
  `OrderEvent(order, created_at)`, `Customer(email_hash)`,
  `StoreSubscription(store, customer, status)`, `Cart(customer)` etc.
  Justificar cada índice; nada de índices que no se usan.
- **Cero N+1**: `select_related`/`prefetch_related` en todos los
  listados (items del pedido, cliente, productos); paginación DRF en
  todo listado; anotaciones para totales agregados del dashboard de
  ventas (no iterar en Python).
- Caché pública: todo cambio que afecte la web pública del cliente
  llama `bump_public_store`/`bump_public_epoch` (patrón existente).

### 3.3 Seguridad multi-tenant

- Todo objeto de tienda filtra por `store` del usuario autenticado;
  tests de IDOR: un dueño NO ve pedidos/productos/clientes de otra
  tienda; un comprador solo ve SUS pedidos (token de seguimiento +
  sesión de cliente).
- Tokens/secrets de tienda (MP access/refresh, Google client secret,
  R2 keys) → `vault.encrypt_secret` con purpose propio; NUNCA en claro,
  NUNCA en respuestas API (solo flags `connected`).
- Endpoints públicos de compra: captcha + rate limit (copiar patrón
  de `ProductReview`), validación estricta de serializers, precios
  SIEMPRE recalculados server-side contra `Product`/`Discount`
  vigentes — jamás confiar en montos del cliente.
- PII de compradores: email/teléfono con hash indexable (patrón
  `document_hash`/`phone_hash` de `UserProfile`), documento cifrado si
  se persiste (`EncryptedCharField`).
- Webhook MP: validar firma `x-signature`, verificar `live_mode`
  (rechazar `False` en prod — copiar `_reject_test_payment`).

### 3.4 Imágenes

Todo upload nuevo (foto de perfil NO aplica — ver 4.1; comprobantes de
pago, imágenes de tarjeta digital si las hubiera) pasa por
`normalize_image` → WebP en R2.

### 3.5 Tests de seguridad por track (OBLIGATORIO antes de cerrar cada subagente)

Ningún track se da por terminado sin escribir y dejar verdes sus tests
de seguridad (`manage.py test <dominio>`). Mínimos por superficie:

| Superficie | Tests obligatorios |
|---|---|
| Todo endpoint nuevo | Auth/permiso correcto (401/403/404 según el caso — IDOR devuelve 404, nunca 403-leak); mass-assignment (campos `status`/`store`/`customer`/precios jamás escribibles por serializer); payloads malformados → 400, nunca 500 |
| Multi-tenant (todo lo de tiendas) | IDOR: dueño A no lee/escribe pedidos/clientes/planes/cobros de tienda B; comprador solo ve SUS pedidos/suscripción/tarjeta; tests con dos tiendas y dos customers |
| Endpoints públicos de compra | Rate limit + captcha (patrón `ProductReview`), qty=0/negativa/gigante, producto de otra tienda en carrito/pedido, precios SIEMPRE recalculados server-side (mandar `total`/`price` en el body NO altera el pedido) |
| Webhook MP (track C) | Firma `x-signature` inválida/ausente → 401/403; `live_mode=False` rechazado; `payment_id` de otra tienda/inexistente; webhook duplicado → un solo `PAID`; monto distinto al pedido → no marca pagado; `external_reference` ajeno |
| Concurrencia (B, C, D) | Dos compradores por la última unidad de stock → uno solo gana (`select_for_update`); doble confirmación de pago / webhook concurrente → una sola transición; retry de creación de pedido con misma idempotency-key → un solo pedido |
| Secretos (A, C, H) | Token MP/Google/R2 jamás en respuesta API, serializer ni log — solo flags `connected`; round-trip vault (encrypt→decrypt) testeado; `enc:v1:` inválido/manipulado → error controlado sin filtrar material |
| PII compradores (A) | Documento/teléfono cifrados en reposo + hash indexable (patrón `UserProfile`); email jamás expuesto en endpoints de terceros |
| Notificaciones/emails (F) | Emails solo al destinatario correcto (comprador/dueño); avisos deduplicados, no spam ante eventos repetidos |
| Soporte (G) | Cliente solo ve SUS hilos; dueño solo los de SU tienda; adjuntos validados (tipo/tamaño; `normalize_image` si aplica) |
| Frontend (I, J) | Sin tokens de refresh en localStorage (patrón cookie-refresh del proyecto); `v-html` solo con contenido sanitizado; rutas nuevas con `meta` de guard correcto |

## 4. ALCANCE FUNCIONAL

> **Decisiones asumidas** (confirmar con el usuario antes de codificar
> cada una; si difieren, ajustar el track correspondiente):
> - Cuentas de comprador **globales** (un registro sirve para comprar
>   en cualquier tienda) con perfil/membresía por tienda.
> - "Suscripciones del administrador" = **planes que cada DUEÑO ofrece
>   a SUS clientes** (gym, barbería, tienda con membresía) — NO los
>   planes de DAVENT para dueños (eso ya existe).
> - "Invoices para cada cliente" = comprobante interno no fiscal por
>   pedido (PDF) + datos fiscales del vendedor + campo para cargar el
>   nº/CAE real. Sin WSFE multi-tenant en esta iteración.
> - "Administradores" de confirmación/ventas = **dueño de cada
>   tienda**; DAVENT admin solo lectura de soporte.
> - Google Auth por tienda: soportar client propio del dueño (BYO,
>   cifrado) **y** client central DAVENT por defecto.
> - Tracking "en vivo": SSE o polling corto sobre `OrderEvent`;
>   websockets solo si la infra ya existe (verificar `INSTALLED_APPS`).

### 4.1 Identidad de compradores (`StoreApp/domains/customers` o similar)

- `Customer`: cuenta global del comprador — email único, password
  (hashead), nombre, apellido, teléfono, avatar = **solo inicial del
  nick** (NO foto de perfil — requisito explícito), doc tipo/número
  opcional cifrado (para facturación del vendedor), dirección(es) de
  envío guardadas, `email_verified`.
- Auth propia (JWT/session — decidir según convención del proyecto y
  documentar): register/login/logout/refresh/me.
- Login social Google por tienda: botón "Ingresar con Google" en el
  checkout/registro de ESA web; el `state`/callback lleva el `store`
  para crear/vincular `StoreMembership`. Credenciales: `store.mp`…
  no — `StoreOAuthConfig.google_client_id/secret` cifrados; si la
  tienda no configuró, usar client central DAVENT.
- `StoreMembership` (customer × store): estado, plan vigente
  (ver 4.5), tags. Un comprador puede ser cliente de N tiendas.
- Endpoints de perfil de comprador: editar datos, direcciones, método
  de pago preferido, suscripciones activas, pedidos.

### 4.2 Carrito (`StoreApp/domains/cart` o dentro de customers)

- `Cart` por customer (+ `store`), `CartItem` (product, qty).
- Un carrito por tienda por cliente (el comprador puede tener carritos
  en varias webs).
- Precios SIEMPRE resueltos server-side al leer (price/offer/discount
  vigente) — el carrito guarda refs, no snapshots.
- Stock: `Product.stock` nullable + `stock_unlimited` implícito cuando
  null (decidir y documentar); reserva NO se hace en carrito — el
  descuento es al confirmar pago (ver 3.1).
- Guest checkout: permitir compra sin registro (email+datos mínimos)
  que luego puede "reclamar" creando cuenta con el mismo email —
  decidir complejidad; mínimo viable: registro obligatorio antes de
  pagar (más simple y cubre facturación).

### 4.3 Pedidos + seguimiento en vivo (`StoreApp/domains/orders`)

Según PLAN_ECOMMERCE.md Fase 1 — modelos `Order`, `OrderItem`,
`OrderEvent`, `PaymentProof`, `StorePaymentConfig`, `StoreFiscalProfile`.

- Estados: `PENDING_PAYMENT → PAID → PACKING → SHIPPED → DELIVERED`
  (+ `EXPIRED`, `CANCELLED`, `REFUNDED`). Transiciones validadas por
  tabla permitida; `PAID` automático por webhook MP o manual por el
  dueño.
- `OrderEvent`: bitácora append-only → fuente del tracking.
- **Seguimiento en vivo**: endpoint público por token
  (`secrets.token_urlsafe`) que devuelve estado + últimos eventos;
  actualización en vivo por SSE
  (`/api/stores/<slug>/orders/<token>/events/`) o polling 5s si SSE no
  es viable — el front muestra línea de tiempo.
- Expiración: `manage.py expire_orders` (cron) → `PENDING_PAYMENT`
  vencidos a `EXPIRED` + libera stock reservado si aplica.
- Notificación de seguimiento: email al comprador en cada cambio de
  estado (reusar mail service) + aviso in-app al dueño.
- Datos del comprador en el pedido: snapshot inmutable de lo necesario
  para entregar y facturar (nombre, email, doc, dirección) — aunque el
  perfil cambie después.

### 4.4 Comprobantes ("invoices para cada cliente")

- Comprobante interno por pedido: vista/PDF "no fiscal" con datos
  fiscales del vendedor, items, totales, leyenda "DOCUMENTO NO FISCAL".
- `Order.invoice_ref`/`invoice_file`: el dueño carga el nº de factura
  real emitida en ARCA (opcional pero incentivado).
- Registro consultable por el comprador en su panel ("mis facturas" =
  sus pedidos + comprobantes).

### 4.5 Suscripciones de clientes + beneficios (por tienda)

- `StorePlan` (lo crea el DUEÑO): nombre, precio, período
  (mensual/anual/custom), `StoreSubscription` (customer × store × plan,
  estado, vigente_hasta, MP preference/payment ref).
- Cobro de la suscripción por el MP del vendedor (mismo OAuth/token —
  reutilizar infra de 4.6) o manual como los pedidos.
- **3 beneficios implementables por plan** (toggles):
  1. `digital_card`: tarjeta digital del miembro (vista pública del
     cliente con QR/nº de socio, nombre del plan, vigencia) — útil
     como "pase" de gimnasio.
  2. `exclusive_discounts_free_shipping`: descuentos exclusivos +
     envíos gratis — flag que el checkout aplica (envío = 0) y cupones/
     descuentos internos del plan.
  3. `exclusive_access`: productos/servicios marcados `is_exclusive`
     visibles/comprables solo para miembros vigentes.
- Enforcement server-side: los beneficios se validan en checkout y en
  endpoints de catálogo (productos exclusivos devuelven 403/404 a no
  miembros en la API pública).
- Renovación: `vigente_hasta` + recordatorio email; mora → pierde
  beneficios automáticamente al leer (sin cron destructivo).

### 4.6 Pagos por tienda (MP del vendedor)

- `StoreMpAccount`: `mp_user_id`, access/refresh token **cifrados
  (vault)**, `live_mode`, `connected_at`. Alta: el dueño pega sus
  credenciales (access token de su app MP o flujo OAuth — implementar
  el más simple que MP permita sin revisión de app propia:
  **MP "credenciales de prueba/producción" pegadas por el dueño** es
  aceptable en MVP; documentar que OAuth Connect requiere app
  aprobada). Si se hace OAuth: callback central + state con slug.
- Checkout MP: crear preference server-side con el token DEL VENDEDOR,
  `external_reference` = token pedido, `notification_url` webhook
  `/api/webhooks/mp/<slug>/`, `back_urls` → página de seguimiento.
- Webhook: validar firma, `GET /v1/payments/<id>` con token del
  vendedor, idempotente, `live_mode` check. Aprobado → `PAID` →
  `PACKING`. Reembolso: endpoint del dueño vía MP con SU token.
- Transferencia/WhatsApp como métodos manuales alternativos en
  `StorePaymentConfig` (instrucciones, alias, `wa.me` link con pedido).
- PROHIBIDO `application_fee`. Comisión futura = facturar como servicio.

### 4.7 Google Auth por tienda

- `StoreOAuthConfig`: `google_client_id`, `google_client_secret`
  (cifrados), `enabled`. Si vacío → client central DAVENT.
- Flujo: `/api/auth/google/<store_slug>/` → callback → crea/vincula
  `Customer` + `StoreMembership`.
- Documentar en el panel del dueño qué client ID/secret crear en
  Google Cloud (guía corta, como la de R2).

### 4.8 R2 propio del dueño (BYO storage)

- `StoreStorageConfig`: `endpoint`, `bucket`, `access_key`,
  `secret_key` (cifrados), `public_base_url`, `enabled`.
- Storage backend por tienda con fallback a R2 de DAVENT si no
  configurado o falla (no romper uploads existentes).
- **Guía en el panel**: pasos para crear bucket R2 gratis + API token
  con permisos object read/write + dominio público/custom — texto
  instructivo, no integración automática.
- Límite: `normalize_image` corre ANTES de subir → el pipeline es el
  mismo; solo cambia el destino.

### 4.9 Notificaciones + soporte

- `Notification` in-app: nuevo `kind` para pedidos/suscripciones del
  dueño; campana existente.
- Emails: pedido nuevo (dueño), cambio de estado (comprador), suscripción
  por vencer (comprador), resumen diario de ventas (dueño, opcional).
- **Panel de soporte**: reusar/extend `AdminApp/domains/chat` — hilo
  comprador↔dueño de tienda (y/o ↔ soporte DAVENT). Decidir modelo:
  `SupportThread(store, customer, order opcional)` con mensajes;
  panel en dashboard del dueño + vista en panel del comprador.
- WhatsApp: links `wa.me` pre-cargados (no API de WhatsApp Business
  en esta iteración).

### 4.10 Panel del dueño — ventas y métricas

- Dashboard "Pedidos": bandeja por estado, confirmar pago, avanzar
  estado, cancelar, detalle con items/comprador/dirección, export CSV.
- Dashboard "Ventas": registro de todas las ventas + **ganancias
  diarias/mensuales/anuales** — agregados en DB (anotaciones/queries
  agregadas, no Python), con filtros por fecha/producto/método de pago.
  Ojo: "ganancias" = total vendido (DAVENT no procesa ni descuenta
  comisiones de MP — aclarar en UI que MP retiene sus fees aparte).
- Panel "Clientes": lista de `StoreMembership`, suscripciones, LTV
  simple (# pedidos, total comprado).
- Panel "Plan/Beneficios": CRUD de `StorePlan` + toggles de beneficios.
- Panel "Cobros": conectar/desconectar MP, Google Auth, R2 + guías.
- Panel "Soporte": bandeja de hilos.

### 4.11 Web pública — activar e-commerce + adaptar diseños

- `StoreCustomization` (o config nueva): `store_mode`/`ecommerce_enabled`
  + `orders_enabled` (requiere `StoreFiscalProfile` completo — Fase 0
  del plan legal).
- En "secciones web" del dashboard: toggle "Activar tienda online"
  que habilita carrito/checkout/seguimiento en la web pública.
- **Componentes compartidos nuevos** (fuera del iframe de patrones):
  `StoreCartDrawer`, `StoreCheckout`, `StoreOrderTracking`,
  `StoreAuthModal` (login/registro Google+email), `StoreMemberCard`
  (tarjeta digital), `StoreLegalPages` (términos/privacidad/
  devoluciones/botón arrepentimiento).
- Adaptación por diseño: cada template/piel suma entrada de carrito en
  header, badge de estados, estilos acordes a su sistema (`store-*.css`,
  tokens `--st-*`); los **patrones HTML** (document sandbox) que
  incluyan catálogo deben enlazar al checkout del shell vía el puente
  existente o simplemente mostrar CTA "Comprar" → ruta del shell.
  Estrategia: primero componentes + rutas del shell funcionando en el
  template default; luego ola de adaptación visual por grupos de
  templates (mismo criterio que tracks G1-G4 del repo).
- Página de seguimiento pública accesible desde email/link — no
  requiere login (token) pero el comprador logueado la ve en "mis
  pedidos".

### 4.12 Páginas legales (Fase 0 del plan)

- Templates de Términos/Privacidad/Devoluciones por tienda con datos
  fiscales del vendedor interpolados; botón de arrepentimiento;
  leyendas de checkout ("la venta es entre comprador y comercio",
  "el pedido se confirma cuando el vendedor acredita el pago",
  precio final visible).
- ToS de DAVENT actualizado (no-parte del contrato, categorías
  prohibidas) — texto para revisión legal del usuario.

## 5. DESCOMPOSICIÓN EN TRACKS (olas de subagentes)

El orquestador lanza subagentes con ownership de archivos DISJUNTO.
Cada track entrega: modelos+migraciones+serializers+views+urls+services
+tests del dominio, o la parte frontend asignada. Nada de dos tracks
editando el mismo archivo (los puntos de integración — `urls.py`
raíz, `INSTALLED_APPS`, router del dashboard — los hace el
orquestador al final de cada ola).

### Ola 0 — Cimientos (orquestador, secuencial)

- Rama `ECCOMMERCE-ADD`, `git pull`/`checkout` correcto.
- Crear estructura de apps: `StoreApp/domains/{customers,cart,orders}`
  (o el naming que se decida) + registrar en `INSTALLED_APPS`/`urls`.
- Modelos base compartidos: `StoreFiscalProfile`, `StorePaymentConfig`,
  `StoreMpAccount`, `StoreOAuthConfig`, `StoreStorageConfig`, flags en
  `StoreCustomization`.
- `AGENTS.md`: agregar sección Ecommerce al final (el orquestador la
  escribe al cerrar, no los tracks).

### Ola 1 — Backend paralelo (4-5 subagentes)

| Track | Scope | Ownership |
|---|---|---|
| A | `customers`: Customer, auth register/login/Google, StoreMembership, perfil, direcciones | `domains/customers/**`, urls customers |
| B | `cart` + `orders` core: modelos, state machine, concurrencia stock/pedidos, idempotencia, expire_orders | `domains/cart/**`, `domains/orders/**`, management command |
| C | Pagos: `StoreMpAccount` + credenciales MP + preference + webhook + métodos manuales | `domains/payments_store/**` o ext. de orders; cuidado: NO tocar `AdminApp/domains/payments` (es de suscripciones DAVENT) — app nueva |
| D | `StorePlan`/`StoreSubscription` + beneficios (digital card, descuentos/envíos gratis, exclusividad) + enforcement en catálogo | `domains/memberships/**` (o dentro de customers) + cambios mínimos en `catalog` serializers/viewset público |
| E | Legal/páginas + contenido: modelos de páginas legales por tienda, textos base, `store_mode` flags | `domains/legal_pages` o ext. `legal` + config |

Dependencias: B y C se tocan en `Order.payment` — definir contrato
(`payment_method`, `payment_ref`, webhook llama servicio de B) en la
descripción del track C para no pisarse. D toca `catalog` público:
solo serializers/viewset de lectura (filtro `is_exclusive` por
membership) — avisar al orquestador para revisar diffs.

### Ola 2 — Backend 2 + notificaciones (2-3 subagentes)

| Track | Scope |
|---|---|
| F | Tracking SSE/polling + `OrderEvent` feed + emails de estado + `Notification` kinds nuevos + `expire_orders` si no quedó en B |
| G | Soporte: `SupportThread`/mensajes comprador↔dueño (extender `chat` o app nueva) + endpoints |
| H | Panel dueño backend: viewsets de pedidos/ventas/métricas/clientes/planes/cobros (agregados SQL, CSV export) |

### Ola 3 — Frontend core (3-4 subagentes)

| Track | Scope |
|---|---|
| I | Público: auth modal/páginas, carrito, checkout, tracking en vivo, mis pedidos, tarjeta digital — componentes compartidos + rutas + template default |
| J | Dashboard dueño: secciones Pedidos/Ventas/Clientes/Planes/Cobros/Soporte + toggle "Activar tienda online" + guard de beneficio si aplica |
| K | Panel comprador dentro del dashboard de DAVENT? — NO: el comprador es usuario final de la web de la tienda, su panel vive en la web pública de la tienda (mis pedidos, suscripción, tarjeta). Definir UX: cuenta de comprador = misma sesión que el registro de DAVENT o separada — decidir en Ola 0 y documentar |

### Ola 4 — Adaptación por diseños (ola de subagentes por grupos)

- Agrupar templates/skins existentes (patrón de los tracks G1-G4) y
  lanzar subagentes que adapten carrito/checkout/tracking/estados al
  lenguaje visual de cada piel (`store-*.css`, tokens `--st-*`).
- Patrones HTML importados: solo CTA/bloques que enlacen al shell —
  no reescribir documentos importados (riesgo CSP).
- QA visual por tienda representativa por grupo.

### Ola 5 — Cierre (orquestador)

- Integración de urls/routers/INSTALLED_APPS, `manage.py check`,
  migraciones consolidadas, suite de tests por dominio tocado,
  `npm run build` frontend.
- Actualizar `AGENTS.md` (sección Ecommerce) + `PLAN_ECOMMERCE.md`
  (checklist de lo implementado vs fases).
- Reporte final: qué quedó, qué falta, decisiones tomadas, riesgos.

### Ola 6 — Auditoría de seguridad final (security-audit)

Antes del reporte final, ejecutar el workflow completo del skill
`.devin/skills/security-audit/SKILL.md` (**full audit mode**) sobre el
diff de la rama `ECCOMMERCE-ADD`:

- **Scope**: dominios nuevos (`customers`, `cart`, `orders`,
  `memberships`, `storepayments`, `legalpages`, `support`/`storeadmin`
  si existen) + lo modificado en `stores`, `catalog`, `notifications`,
  `chat` y el frontend público (componentes/vistas nuevas).
- **Perfil**: `standard` (o `deep` si el diff lo justifica). Output
  directory FUERA del repo (`~/security-audit-skill/<repo>/run-<N>`,
  nunca dentro del target salvo orden expresa).
- **Cierre**: todo `confirmed` critical/high se corrige en la rama y
  se re-verifica antes de reportar; medios/bajos quedan documentados
  en `SECURITY_AUDIT.md` con su veredicto. Los `needs_validation` se
  listan en el reporte final con su plan de validación — no se asumen
  controles ausentes del repo.
- El orquestador verifica los artefactos generados (`run-metadata.json`,
  `findings.json`, `REPORT.md`) antes de cerrar la rama.

## 6. CRITERIOS DE ACEPTACIÓN GLOBAL

- [ ] Un comprador se registra (email o Google), arma carrito en la web
      de una tienda, paga por MP del vendedor o transferencia
      confirmada por el dueño, y sigue su pedido EN VIVO hasta
      `DELIVERED`.
- [ ] El dueño ve su bandeja de pedidos, confirma pagos, avanza
      estados, exporta ventas y ve ganancias diarias/mensuales/anuales.
- [ ] El dueño crea un plan de suscripción con beneficios; un cliente
      que paga ve su tarjeta digital / descuentos+envío gratis /
      acceso a exclusivos, y los pierde al vencer.
- [ ] Cero fugas multi-tenant (tests IDOR por track).
- [ ] Cero N+1 en listados nuevos (verificar con `assertNumQueries`
      o django-debug-toolbar en tests).
- [ ] Idempotencia probada: webhook duplicado, doble confirmación,
      retry de pedido → un solo efecto.
- [ ] Concurrencia: dos compradores por la última unidad de stock →
      uno solo gana; test que lo demuestre.
- [ ] Nada pusheado a `main`, nada sincronizado con Neon/prod.
- [ ] `manage.py check` limpio + tests de cada dominio nuevo verdes +
      build frontend OK.
- [ ] Cada track cerró con sus tests de seguridad de la sección 3.5
      escritos y en verde.
- [ ] `security-audit` (`.devin/skills/security-audit/`, full audit
      mode) ejecutado sobre la rama: cero `confirmed` critical/high
      abiertos; el resto documentado.

## 7. PROTOCOLO DEL ORQUESTADOR

1. Leer `AGENTS.md` + `PLAN_ECOMMERCE.md` + este documento completo.
2. `git checkout main && git pull` → `git checkout -b ECCOMMERCE-ADD`.
   Verificar que NO hay cambios sin commitear del usuario que se
   pisen (avisar si hay).
3. Ola 0 → 5. Por cada track: prompt autocontenido (este documento +
   paths exactos + ownership + contratos entre tracks + criterios de
   aceptación del track). Los subagentes NO ven esta conversación:
   incluirles todo el contexto necesario en su prompt.
4. Tras cada track: revisar diff (`git diff --stat`), correr tests del
   dominio **incluidos los de seguridad de la sección 3.5**, commitear
   en la rama. Si dos tracks chocan en un archivo compartido, resolver
   el orquestador.
5. Ola 6: lanzar la auditoría `security-audit` final; corregir los
   `confirmed` critical/high y documentar el resto antes del reporte.
6. Nunca `git push` ni `git merge` sin orden expresa del usuario.
