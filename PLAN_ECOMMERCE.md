# PLAN — E-commerce + seguimiento de pedidos en DAVENT

Fecha: 09/11/2026. Estado: propuesta.

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

- [ ] **ToS de DAVENT** (página legal propia): declarar que DAVENT no es
      parte de las operaciones de compraventa, no procesa pagos ni emite
      comprobantes fiscales, no responde por veracidad de datos fiscales
      del vendedor ni por reclamos entre comprador y vendedor.
      Categorías prohibidas (armas, productos regulados, servicios
      ilícitos, etc.).
- [ ] **Páginas legales por tienda** (generadas desde template, editables
      por el dueño): Términos y condiciones, Política de privacidad,
      Política de cambios y devoluciones (derecho de arrepentimiento 10
      días en compras online — Ley 24.240), datos de contacto del
      comercio.
- [ ] **Botón/enlace de arrepentimiento** en la web pública de la tienda
      (obligatorio en e-commerce argentino) → flujo de solicitud de
      devolución que le llega al vendedor como pedido especial.
- [ ] **Leyenda en checkout**: "La venta se realiza entre el comprador y
      el comercio. El pedido se confirma cuando el vendedor acredita el
      pago." + precio final visible + plazos de entrega declarados.
- [ ] **Datos fiscales del vendedor** obligatorios para activar ventas:
      razón social/nombre, CUIT, condición frente a IVA (Monotributo /
      RI / Exento), domicilio fiscal. Se muestran en el pie de la tienda.
      (Monotributo también tiene CUIT → no excluye a nadie.)

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

- [ ] **App de MP**: alta en developers.mercadopago.com + credenciales
      `MP_CLIENT_ID`/`MP_CLIENT_SECRET`/`FRONTEND_URL` callback.
      Checkout Pro/Bricks → cero PCI (tarjeta nunca toca DAVENT).
- [ ] `StoreMpAccount` (OneToOne a Store): `mp_user_id`, access/refresh
      token **cifrados con `vault.py`** (mismo mecanismo que AFIP_KEY),
      `live_mode`, scopes, `connected_at`. Desvincular = revocar.
- [ ] OAuth: `GET /api/stores/<slug>/mp/connect/` → redirect a MP →
      `GET /api/mp/callback/` guarda tokens. Solo el dueño de la tienda.
- [ ] Checkout: `POST /api/stores/<slug>/orders/<token>/pay/` crea la
      preferencia **con el token del vendedor** (`external_reference` =
      token del pedido, `notification_url` = webhook, `back_urls` =
      página de seguimiento) → frontend redirige a `init_point`.
- [ ] Webhook `POST /api/webhooks/mp/<slug>/`: validar firma
      `x-signature`, `GET /v1/payments/<id>` con el token del vendedor,
      idempotente por `payment_id` (mismo patrón que
      `CreatePaymentQuery`/`external_reference` de suscripciones),
      rechazar `live_mode=False` en producción. Aprobado → `PAID` →
      `PACKING` automático. Reembolsos: endpoint del dueño que llama a
      MP con SU token.
- [ ] `StorePaymentConfig`: `mp_enabled` convive con métodos manuales —
      el comprador elige "Mercado Pago" o "Transferencia".
- [ ] Requisito: el vendedor necesita cuenta MP propia (que ya exige
      CUIT/monotributo — encaja con el perfil fiscal obligatorio).
- [ ] Tests: webhook firma inválida, pago duplicado, `live_mode=False`
      en prod, pedido de otra tienda, token revocado.

## FASE 3 — Fiscal del vendedor (sin integración ARCA)

- [ ] `StoreFiscalProfile` (o campos en `StorePaymentConfig`): CUIT
      validado (dígito verificador), condición IVA, domicilio fiscal,
      punto de venta (opcional).
- [ ] Comprobante interno **no fiscal**: PDF por pedido con datos del
      emisor (fiscales del vendedor), items, totales, leyenda
      "DOCUMENTO NO FISCAL — el comprobante fiscal autorizado lo emite
      el comercio". Descargable por vendedor y comprador.
- [ ] Campo en el pedido: `invoice_ref` + `invoice_file` — el vendedor
      carga nº de factura/CAE emitida desde ARCA → queda en el pedido
      y en el seguimiento.
- [ ] Footer de la tienda muestra datos fiscales del vendedor.
- [ ] Validación: no se puede activar `orders_enabled` sin perfil
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

## Checklist "libre de problemas fiscales hoy"

- [x] DAVENT no cobra ni retiene fondos de ventas.
- [x] DAVENT no emite comprobantes fiscales de terceros.
- [ ] ToS explícitos de no-parte + categorías prohibidas.
- [ ] Política de privacidad cubre datos de compradores (encargado del
      tratamiento por cuenta del vendedor).
- [ ] Datos fiscales del vendedor obligatorios para vender.
- [ ] Comprobante interno marcado "no fiscal".
- [ ] Páginas legales por tienda + botón de arrepentimiento.
- [ ] El vendedor asume en ToS de la tienda su responsabilidad fiscal
      (monotributo/RI al día, facturación de cada venta).
