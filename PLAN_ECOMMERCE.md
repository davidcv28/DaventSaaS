# PLAN — E-commerce + seguimiento de pedidos en DAVENT

Fecha: 09/11/2026. Estado: **implementado en `ECCOMMERCE-ADD`** (Olas 0-5
completas — backend + frontend + tests; pendiente de revisión legal
humana antes de habilitar ventas reales).

> Esto es un roadmap técnico-legal, **no asesoría legal**. Los textos de
> Términos/Privacidad y la config fiscal deben revisarlos un abogado y un
> contador argentino antes de publicar tiendas con ventas reales.

## Principio rector (protección legal de DAVENT)

DAVENT es **infraestructura**: no vende, no cobra, no factura, no es parte
del contrato de compraventa. El contrato es **comprador ↔ dueño de tienda**.
La plata del comprador va **directo al vendedor** (transferencia/depósito/
WhatsApp coordinado, o la cuenta MP del propio vendedor vía OAuth Connect —
nunca la cuenta de DAVENT ni con `application_fee`). El comprobante fiscal lo emite el **vendedor** desde
ARCA con su propio CUIT — DAVENT nunca emite CAE de terceros (el CAE exige
certificado del propio emisor).

Lo que DAVENT SÍ hace: generar el pedido, mostrar las instrucciones de
pago de la tienda, notificar cambios de estado, guardar los datos del
comprador y del vendedor, y emitir un **comprobante interno no fiscal**.

---

## FASE 0 — Bases legales (antes de habilitar ventas)

Sin esto no se publica "modo ventas" en ninguna tienda.

- [x] **ToS de DAVENT** (página legal propia `/terminos`): declara que
      DAVENT no es parte de las operaciones de compraventa, no procesa
      pagos ni emite comprobantes fiscales de las ventas de comercios,
      y no responde por datos fiscales del vendedor ni reclamos
      comprador↔comercio. Categorías prohibidas cubiertas en §5.
- [x] **Páginas legales por tienda** (generadas desde template, editables
      por el dueño): Términos y condiciones, Política de privacidad,
      Política de cambios y devoluciones (derecho de arrepentimiento 10
      días en compras online — Ley 24.240), datos de contacto del
      comercio. `/tienda/<slug>/legal/<kind>` público + panel del dueño.
- [x] **Botón/enlace de arrepentimiento** en la web pública de la tienda
      (obligatorio en e-commerce argentino) → `legal/returns` con
      formulario captcha+honeypot+throttle; las solicitudes llegan al
      dueño en el panel (Legal → Devoluciones) y por notificación.
- [x] **Leyenda en checkout**: "La venta se realiza entre vos y el
      comercio…" + aceptación de términos linkeada + precio final
      visible en el resumen + método de envío con su plazo declarado.
- [x] **Datos fiscales del vendedor** obligatorios para activar ventas:
      razón social/nombre, CUIT (dígito verificador), condición frente
      a IVA (Monotributo / RI / Exento), domicilio fiscal y punto de
      venta. Se muestran en el pie de la tienda y en el comprobante
      interno no fiscal. (Monotributo también tiene CUIT → no excluye
      a nadie.)

## FASE 1 — Dominio `orders` (MVP funcional)

App nueva `StoreApp/domains/orders` (app_label `orders`), mismo patrón
que `catalog`: models / serializers / views / urls / services / tests.

### Modelos

- `Order` — store FK, número interno secuencial por tienda (`store`
  + `number` unique), estado, snapshot del comprador (nombre, apellido,
  email, tipo/número de doc — solo si el vendedor lo pide, dirección de
  envío), totales (subtotal, descuentos aplicados, total), método de
  pago usado, referencia de pago (nº de pedido visible), vencimiento de
  pago, timestamps.
- `OrderItem` — order FK, product FK (SET_NULL para no perder historial
  si borran el producto), nombre/precio/offer snapshot **inmutables**
  (mismo criterio que `Invoice`: un cambio posterior del producto no
  reescribe pedidos emitidos), qty, imagen key opcional.
- `OrderEvent` — bitácora append-only de cambios de estado
  (quién/qué/cuándo) → base del "seguimiento" del comprador.
- `PaymentProof` (opcional fase 1) — comprobante subido por el comprador
  (imagen → `normalize_image` → WebP en R2, regla AGENTS.md §5).

### Estados

```
PENDING_PAYMENT → PAID → PACKING → SHIPPED → DELIVERED
      ↓             ↓
  EXPIRED/CANCELLED   REFUNDED
```

`PAID` lo marca **el vendedor a mano** ("recibí el pago"). Al confirmar:
- decrementa stock si `Product.stock` existe (descontar AL PAGAR, no al
  crear el pedido — no bloquear mercadería por pedidos impagos).
- pasa automático a `PACKING`.

### Config por tienda

`StorePaymentConfig` (OneToOne a Store): métodos habilitados
(`transfer`, `whatsapp`, `cash`), alias/CVU/CBU + titular, instrucciones
texto libre, número de WhatsApp, `require_payment_proof` (bool),
`payment_deadline_hours` (default 48), datos fiscales del vendedor
(Fase 0). Vive en el panel del dueño junto a "Qué mostrar".

### Endpoints

- Público (sin auth, rate-limit + captcha como reviews):
  `POST /api/stores/<slug>/orders/` (crear pedido),
  `GET  /api/stores/<slug>/orders/<token>/` (seguimiento por token
  no adivinable — no por id secuencial, anti-IDOR),
  `POST .../proof/` (subir comprobante si `require_payment_proof`).
- Dashboard (dueño): CRUD de pedidos, `POST /orders/<id>/confirm-payment/`,
  `POST /orders/<id>/advance/` (packing→shipped→delivered),
  `POST /orders/<id>/cancel/`, listado con filtros por estado.
- `GET /api/orders/` admin DAVENT: solo lectura para soporte.

### Frontend

- Web pública de la tienda: carrito (store-localStorage), página/flujo
  checkout (datos comprador + método de pago → instrucciones + botón
  WhatsApp `wa.me` con pedido precargado), pantalla "pedido creado"
  con link de seguimiento y datos para pagar.
- Página pública de seguimiento (estado + historial de eventos).
- Dashboard dueño: nueva sección/pestaña "Pedidos" — bandeja con badge
  "pendiente de pago", detalle con items/datos comprador, acciones
  confirmar pago / avanzar estado / cancelar, export CSV.
- Bloque de checkout en los diseños: la mayoría de templates pueden
  reusar la página catálogo existente + ruta nueva; los pattern docs
  (iframe sandbox) necesitan su propio puente si el checkout vive
  dentro del documento del diseño — evaluar si el checkout es página
  del shell (recomendado: sí, fuera del iframe para no duplicar CSP).

### Notificaciones

- `Notification` in-app al dueño por pedido nuevo (kind nuevo
  `KIND_ORDER`) y al comprador no aplica (no tiene cuenta).
- Email al comprador en cada cambio de estado (reusar el servicio de
  mail de `suscriptions`/`invoices`: `send_mail` ya existe).
- Email al dueño por pedido nuevo y por pedido por vencer.

### Cron

`manage.py expire_orders` (diario o cada hora): pedidos
`PENDING_PAYMENT` vencidos → `EXPIRED` + libera reserva de stock.
Mismo patrón que `subscription_notices`/`prune_visits`.

### Seguridad

- Token de seguimiento: `secrets.token_urlsafe(24)` único por pedido.
- Rate limit en creación de pedidos (anti-spam de pedidos falsos).
- Precios SIEMPRE del servidor (nunca del cliente) — re-calcular
  totales contra `Product.price`/`offer_price`/`Discount` vigentes.
- Snapshot inmutable de items (anti manipulación posterior).
- Datos del comprador: email/phone con hash si se indexa (patrón
  `document_hash`/`phone_hash` de UserProfile), cifrado de doc si se
  guarda (EncryptedCharField).

## FASE 2 — Mercado Pago por tienda (OAuth Connect)

La plata cae **directo en la cuenta MP del vendedor** → MP le deposita
a su banco. DAVENT nunca toca los fondos: mismo esquema fiscal que la
transferencia. **Prohibido `application_fee`/split**: retener comisión
por venta convertiría a DAVENT en intermediario de fondos (obligaciones
fiscales propias). Si más adelante se quiere comisión por venta, se
factura como servicio aparte (el dominio `invoices` ya existe).

- [x] **Credenciales MP del vendedor (BYO, no OAuth)**: el vendedor pega
      su propio access token de MP en `mp/connect/` (vault + AAD por
      tienda) junto al `webhook_secret` de SU app. Desviación
      deliberada del OAuth Connect original: cero dependencia de una
      app MP registrada por DAVENT, mismos efectos (pagos directos al
      vendedor, Checkout Pro/Bricks → cero PCI).
- [x] `StoreMpAccount` + `StoreMpWebhookConfig`: `mp_user_id`,
      access token **cifrado con `vault.py`** (purpose por tienda),
      `live_mode`, `connected_at`, webhook secret cifrado igual.
      Desvincular = revocar/borrar tokens.
- [x] Conexión: `POST /api/store-payments/mp/connect/` (solo el dueño)
      valida el token contra `/users/me` de MP antes de guardar.
- [x] Checkout: `POST /api/stores/public/<slug>/orders/<token>/pay/`
      crea la preferencia **con el token del vendedor**
      (`external_reference` = pedido, `notification_url` = webhook,
      `back_urls` = seguimiento) → frontend redirige a `init_point`.
- [x] Webhook `POST /api/webhooks/store-mp/<slug>/`: firma `x-signature`
      HMAC con el secret del vendedor + ventana anti-replay, `data.id`
      solo del query firmado, `GET /v1/payments/<id>` con el token del
      vendedor, idempotente por `mp_payment_id` unique +
      `select_for_update`, monto aprobado debe igualar `order.total`
      (fail-closed), rechaza `live_mode=False` en producción.
      Aprobado → `PAID` → `PACKING`. Reembolso: endpoint del dueño que
      llama a MP con SU token bajo lock de la fila del pedido.
- [x] `StorePaymentConfig`: `mp_enabled` convive con métodos manuales —
      el comprador elige "Mercado Pago" o "Transferencia".
- [x] Requisito: el vendedor necesita cuenta MP propia (que ya exige
      CUIT/monotributo — encaja con el perfil fiscal obligatorio).
- [x] Tests: webhook firma inválida, pago duplicado, monto
      mismatch, `live_mode=False` en prod, pedido de otra tienda,
      refund MP y manual.

## FASE 3 — Fiscal del vendedor (sin integración ARCA)

- [x] `StoreFiscalProfile`: CUIT validado (dígito verificador),
      condición IVA, domicilio fiscal, punto de venta.
- [x] Comprobante interno **no fiscal**: `build_receipt_payload`
      devuelve datos del emisor (fiscales del vendedor), items con
      snapshot, totales y leyenda "DOCUMENTO NO FISCAL"; el front lo
      renderiza imprimible en la página de seguimiento (decisión: sin
      PDF en backend — el comprobante fiscal real lo emite el
      comercio desde ARCA).
- [x] Campo en el pedido: `invoice_ref` — el vendedor carga nº de
      factura/CAE emitida desde ARCA (`POST store-orders/<id>/invoice-ref/`)
      → queda en el pedido y visible en seguimiento.
- [x] Footer de la tienda muestra datos fiscales del vendedor.
- [x] Validación: no se puede activar `orders_enabled` sin perfil
      fiscal completo.

## FASE 4 — Integraciones (opcional, post-MVP)

- **Facturación automática**: solo si aparece demanda — WSFE
  multi-tenant (`afip.py` refactor a emisor-por-tienda + cert del
  vendedor) o API de terceros. Requiere contrato que cubra a DAVENT
  como prestador del servicio. **No habilitar sin revisión legal.**
- **Devoluciones**: flujo formal post-entrega (solicitud → aprobación
  vendedor → reembolso coordinado por fuera → `REFUNDED`). Con MP
  conectado el reembolso puede ejecutarse por API con el token del
  vendedor.
- **Envíos**: cotización por zona, tracking number, integración
  Andreani/CorreoArgentino (fase posterior).
- **IIBB / percepciones**: revisar con contador si alguna provincia
  designa plataformas como agentes — hoy no aplica porque DAVENT no
  toca la plata.

## Estado de implementación (rama `ECCOMMERCE-ADD`)

- **FASE 0 (legal)**: implementada — `legalpages` (páginas por tienda con
  datos fiscales interpolados, defaults sin persistir, botón de
  arrepentimiento con captcha+honeypot+throttle), leyenda de venta en
  checkout, `ecommerce_enabled` como toggle del dueño. Pendiente solo la
  revisión de un abogado/contador de los textos antes de producción.
- **FASE 1 (orders)**: implementada — `orders` + `cart` + `customers`
  (JWT propio, PII cifrada, Google login BYO), state machine con
  `select_for_update` + idempotencia, stock al pagar, tracking público
  por token de alta entropía, comprobante interno no fiscal, avisos
  Celery por kind.
- **FASE 2 (MP por tienda)**: implementada — OAuth Connect del vendedor,
  webhook HMAC por secreto propio, preference con credenciales del
  dueño, refunds por API del vendedor + `mark_refunded`, métodos manuales
  (transferencia/WhatsApp/efectivo) con instrucciones por tienda.
- **FASE 3 (fiscal)**: implementada — `StoreFiscalProfile` (CUIT con
  dígito verificador, condición IVA, domicilio), gate de ventas sin
  perfil completo, `invoice_ref`/`invoice_file` en el pedido, footer con
  datos fiscales.
- **FASE 4 (integraciones)**: parcial — devoluciones con reembolso MP
  por API del vendedor implementadas (`refunds.py`); envíos con
  cotización/tracknumber y facturación automática quedan post-MVP.
- **Extras entregados**: `memberships` (planes del dueño, beneficios,
  enforcement de `is_exclusive`), `support` (hilos comprador↔dueño),
  `storeadmin` (panel dueño: pedidos, métricas, clientes/LTV), storage
  BYO R2 por tienda, CTAs de compra dentro de los documentos de patrón,
  paneles del dashboard (pedidos, ventas, clientes, soporte, cobros,
  legal, suscripciones).
- **Security audit (skill Cloudflare, run-1)**: perfil `standard`,
  scope `main...ECCOMMERCE-ADD`, 18 unidades de cobertura, 15 records
  finales — 9 confirmados (todos corregidos en `7d53e880`/`5c249b52`),
  5 rejected post-fix (claims reales en el ref auditado cuyo sink ya
  estaba remediado cuando el verificador revisó el árbol: captcha,
  mails a email no verificado, huella-PII unique, receipt PII y
  amount-None del webhook), 1 needs_validation (dedup de refunds
  duplicados del lado de MP tras outcome ambiguo — plan de validación
  en `NEEDS-VALIDATION.md` del run). Artefactos del run en
  `C:\Users\David\security-audit-skill\DaventSaaS\run-1` (fuera del
  repo); reportes commiteados en `docs/security-audit-run1/`.

## Checklist "libre de problemas fiscales hoy"

- [x] DAVENT no cobra ni retiene fondos de ventas.
- [x] DAVENT no emite comprobantes fiscales de terceros.
- [x] ToS explícitos de no-parte + categorías prohibidas.
- [x] Política de privacidad cubre datos de compradores (encargado del
      tratamiento por cuenta del vendedor).
- [x] Datos fiscales del vendedor obligatorios para vender.
- [x] Comprobante interno marcado "no fiscal".
- [x] Páginas legales por tienda + botón de arrepentimiento.
- [x] El vendedor asume en ToS de la tienda su responsabilidad fiscal
      (monotributo/RI al día, facturación de cada venta).

---

## FASE 6 — Pulido visual ecommerce (Ola 2, `ECCOMMERCE-ADD`)

Fecha: ola de subagentes paralelos con ownership disjunto, integrada y
pusheada en la misma rama.

- **Auth del comprador**: página completa `/ingresar` (`StoreAuthView` +
  `StoreAuthForm` compartido con el modal global), modos login/register/
  forgot por `?mode=`, destino post-auth `?next=` sanitizado
  (`authRoute`/`authNextPath` en `cart.store`, anti open-redirect).
  Alias `/tienda/<slug>/{ingresar,carrito,pedido/:token/comprobante}`.
- **Panel de cuenta**: `StoreAccountView` rediseñado — sidebar con
  avatar/nav/logout en desktop, tabs con scroll en mobile; pedidos con
  pills semánticos, suscripciones con tarjeta digital, direcciones y
  perfil autocontenidos (`components/ecommerce/account/*`). Gate de auth
  propio; `store-auth`/`store-plans` excluidos del iframe de patrón
  (`ECOMMERCE_ROUTES` en `StorePublicLayout`).
- **Flujo de compra**: carrito, checkout, tracking, comprobante imprimible,
  planes y soporte pulidos (skeletons, steppers, empty states); sticky buy
  bar; `store-plans` ya no queda tapado por el patrón.
- **Patrones**: los 23 `sources/*.html` con secciones ecommerce propias
  (CTAs de compra integrados a la identidad de cada diseño, cuenta +
  carrito en headers, contraste AA, responsive). `moderntec.html`
  reescrito como patrón ecommerce funcional (catálogo + filtros + PDP).
  `fotos.html` quedó huérfano del seed (preexistente — pendiente decidir
  publicarlo o borrarlo).
- **Bridge**: píldoras cuenta/carrito inyectadas en documentos, badge con
  `itemCount` vía `postMessage` (`davent:ds-cart-state`), `ds-cart` →
  `/carrito` de la tienda; CSS base `.dsx-*` elevado.
- **Templates Vue**: las 7 pieles + Raíz con ecommerce nativo (gimnasio
  placas lima + mono, moderntec panel instrumento, movimiento fichas,
  mercado/sastrería/indumentaria/impacto pulidos). Tarjetas consumen los
  tokens `--tpc-name-*` que las pieles ya declaraban (bug: nunca se
  aplicaban). `.sp-form` neutralizado por piel (orbe/rotación de Raíz no
  se filtra a las demás).
- **Verificación**: `seed_design_catalog` re-corrido (127 estilos, 25
  patrones), `npm run build` + tests (65) verdes, QA visual de subagentes
  (~500 páginas combinaciones patrón/estilo/viewport en verde) + smoke
  browser de `/ingresar`, `/cuenta`, `/carrito`, `/checkout`, landing con
  iframe de patrón — 0 errores de consola ni requests fallidos.
