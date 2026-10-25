# Auditoría de seguridad DAVENT — backend

**Fecha:** 2026-10-24 · **Alcance:** `AdminApp/`, `StoreApp/`, `SuscriptionApp/`, `DaventProject/`
**Suite:** 194 tests (61 preexistentes + 133 nuevos) — `manage.py test` → OK

Auditoría ofensiva/defensiva del backend completo: autenticación, sesiones,
suscripciones, pagos (Mercado Pago), facturación, tiendas/catálogo,
uploads a R2, formularios públicos y endpoints de administración.

---

## 1. Brechas de seguridad encontradas y remediadas

| # | Severidad | Brecha | Fix aplicado |
|---|-----------|--------|--------------|
| 1 | **Alta** | `remember='false'` (string form-encoded) era evaluado como truthy → convertía sesiones efímeras en persistentes de 30 días | `_remember_requested()` con parseo estricto en `auth_views.py` |
| 2 | **Alta** | Unicidad de email/username **case-sensitive**: `NUEVO@GMAIL.COM` abría una segunda cuenta con el mismo correo (multi-cuenta / farming de trial) | `__iexact` en `users/serializers/mixins.py` |
| 3 | **Alta** | Webhook de Mercado Pago: una firma válida capturada podía **rejugarse** indefinidamente (sin ventana de frescura) | Ventana anti-replay de 10 min (acepta ts en seg. y ms) + HMAC `compare_digest` en `payments/views/viewset.py` |
| 4 | **Alta** | `CreatePaymentQuery` no verificaba `external_reference` de MP: un `payment_id` ajeno cuyo monto coincidiera con el plan podía registrarse en la suscripción propia (**IDOR de cobros**) | Ownership del cobro validado + pago existente de otra suscripción ya no se devuelve |
| 5 | **Media** | Token de verificación de email incluía `last_login`: **el primer login invalidaba el link** del correo de alta | Eliminado `last_login` del hash en `EmailVerificationTokenGenerator` |
| 6 | **Media** | Cuota de imágenes (storage R2): carrera **check→put→consume** permitía a dos uploads concurrentes superar el límite de MB/imágenes del plan | `select_for_update` + rechequeo de cupos bajo lock en `storage.py`; el objeto huérfano se borra de R2 |
| 7 | **Media** | `max_products` se chequeaba antes de insertar sin lock → mismo TOCTOU en creates concurrentes | Rechequeo bajo `select_for_update` en `catalog/views/viewset.py` |
| 8 | **Media** | Contador de visitas confiaba en el **primer** `X-Forwarded-For` (spoofeable): el visitante inflaba el dedupe a su favor | Se toma el último segmento (IP real appendeada por el proxy) |
| 9 | **Media** | `POST /api/content-reports/` (AllowAny) enviaba un correo a `LEGAL_REPORTS_EMAIL` por cada denuncia sin throttle propio → **vector de email-bombing** | Throttle `content_report` dedicado en viewset + settings |
| 10 | **Baja** | `min_price`/`max_price` del catálogo público: `Decimal('1e999')` desbordaba `numeric(12,2)` → 500 | Parseo defensivo + clamp al máximo del campo en `_price_bound` |
| 11 | **Baja** | Reorden de carrusel/galería con ids duplicados o incompletos dejaba **posiciones pisadas** | `_apply_order()`: dedupe de ids + posiciones consecutivas para los omitidos |
| 12 | **Baja** | `assign` de planes (admin) con ids no numéricos → `ValueError` al ORM → 500 | Parseo `int()` defensivo → 400 |
| 13 | **Baja** | Regex invertido en `validate_name` de planes: `^[a-zA-Z...]` rechazaba **todo** nombre que empezara con letra | `re.search(r'[^a-zA-ZñÑáéíóúÁÉÍÓÚ\s]', ...)` |
| 14 | **Baja** | `IntegrityError` en altas concurrentes (registro, suscripción, claim de slug) salía como **500** en vez de 400 | `try/except IntegrityError` → `ValidationError` en services/serializers |
| 15 | **Baja** | `PATCH /api/content-reports/<id>/` (gestión staff) devolvía **405**: solo existía `update` (PUT) | `partial_update` agregado al base viewset de legal |
| 16 | **Baja** | Captcha del formulario de contacto: comparación de hash con `==` (timing) | `hmac.compare_digest` |
| 17 | **Baja** | CSP del SPA bloqueaba Firebase Phone Auth / reCAPTCHA en el deploy empaquetado | Dominios de Firebase/Google agregados a la CSP en `settings.py` |

### Verificado como correcto (sin cambio necesario)

- **Aislado por dueño**: catálogo (`my_store()` en querysets y `context['store']`),
  tienda, suscripciones, pagos y facturas solo devuelven objetos propios; staff ve todo.
- **Web pública fail-closed**: `public`, `public_catalog` y `contact` exigen
  `is_published` + `!is_blocked` + `has_public_link` con `grants_access()` vigente → 404.
- **Suscripción nace impaga**: `POST /api/suscriptions/` crea `Pendiente de pago`;
  el plan se aplica solo al acreditar el cobro (`ApplyPendingPlanQuery`).
- **Trial anti-farming**: `is_trial` excluido del queryset del campo, del
  `_resolve_suscription` de payments, del `assign` admin y del catálogo público.
- **Password reset**: respuesta 200 genérica (anti-enumeración), token firmado,
  invalida todos los `OutstandingToken` al confirmar (cierra sesiones).
- **Cambio de clave**: misma invalidación de refresh que el reset.
- **Store claim**: exige `email_verified` (excepto staff).
- **Refresh en cookie httpOnly** scopeada a `/api/token/` + CSRF doble-submit en
  refresh/logout por cookie; rotación con blacklist (un refresh robado muere al
  primer uso legítimo).
- **Serializers públicos sanitizados**: `contact_email` no viaja en el payload
  público; `location_address` solo con `has_location_map` + `show_location`;
  `chatbot` solo con el flag y habilitado.
- **Plan pendiente ≠ plan vigente**: `PUT` de cambio de plan no otorga nada sin cobro.
- **Invoice numbering**: correlativo por (tipo, pos) bajo `select_for_update` +
  retry de colisión + OneToOne por pago (idempotente); email post-commit.

## 2. Optimización de consultas, concurrencia e idempotencia

### Concurrencia — resuelto

- **Cuota de imágenes**: todos los upload/delete (logo, cover, carrusel,
  galería, producto) bloquean la fila de `Store` y rechequean
  `max_images`/`max_gallery_images`/`max_storage_mb` antes de consumir cuota.
- **`can_add_product`**: rechequeo bajo lock en el `create` de `ProductViewSet`.
- **Rollups de revenue**: `UpdateRevenueRollupsQuery` usa `F()` atómico +
  `Greatest(..., 0)` (antes un read-modify-write perdía pagos concurrentes y
  un refund podía dejar el contador negativo).
- **Visitas**: `get_or_create` por (store, día) con `UniqueConstraint` +
  `F('count') + 1` — no pierde hits concurrentes.
- **Registro/suscripción/store**: `IntegrityError` de la carrera final → 400.

### Idempotencia — verificada/robustecida

- `CreatePaymentQuery`: por `external_reference` (unique) + IntegrityError →
  devuelve el existente; rechaza el ajeno.
- `PaymentWebhookQuery`: `renew` solo cuando el pago **entra** a approved;
  reentregas del webhook no re-extienden el período ni duplican rollups.
- `IssueInvoiceQuery`: existente por pago → devuelve; colisión de número →
  recalcula con retry (máx. 3).
- `logout` sin cookie → 200 idempotente.
- `verify_captcha`/`captcha firmado`: `TimestampSigner` con edad máxima.

### Índices / consultas — estado

Ya cubiertos: `idx_payment_status_paidat`, `idx_payment_user`,
`idx_payment_suscription`, `idx_suscription_plan`, `idx_suscription_pending_plan`,
`idx_product_store_active`, `idx_category_store`, `idx_brand_store`,
`idx_carousel_store`, `idx_gallery_store`, `idx_planbenefit_benefit`,
`idx_report_status_kind`, `idx_invoice_user_created`, unique (store, date) en
visitas, unique `external_reference` en pagos, unique (type,pos,number) en facturas.

`select_related` aplicado en listados calientes (stores list con
`customization`/`suscription`/`plan`, payments con `suscription.plan`, invoices
con cadena `payment.suscription.plan`).

**Oportunidad pendiente (no aplicada)**: `profile_has_benefit` se invoca varias
veces por request (public + serializer). Un cache por request de
`plan_benefits_of(profile)` ahorraría ~3-5 queries por hit público. Bajo impacto
(cache de plan de 60s posible en `plan_benefits_of`, ojo con invalidación en
baja de plan).

## 3. Logging y auditoría

### Estado previo

No existía sección `LOGGING` en settings → los `logger.warning/exception` del
proyecto se perdían en producción.

### Aplicado

- **`LOGGING`** en `settings.py`: console handler, loggers de `django.request`
  y del proyecto con nivel por env (`LOG_LEVEL`, default INFO).
- **Auditoría de login**: `logger.warning` por intento rechazado (status, user,
  IP — **nunca** la contraseña).
- **Moderación**: `block`/`unblock` loguean slug + admin + motivo.
- **Admin**: `assign` de plan y aprobación manual de pago loguean admin + target.
- **Webhooks**: firma inválida (warning), secret ausente en prod (error).
- **Fallos de email**: contacto/factura/denuncia → `logger.exception` sin
  romper el flujo principal.

### Recomendaciones pendientes

- Reintentos de `UpdateRevenueRollupsQuery`/`IssueInvoiceQuery` en colisión:
  hoy el retry es silencioso; un `logger.warning` en el retry ayuda a detectar
  hot-spots de concurrencia.
- `record_store_visit` falla silencioso si el cache cae — considerar `try/except`
  + warning (un Redis caído no debe tirar la web pública).
- Centralizar un handler de `security` (django.security) si se quiere SIEM.

## 4. Cobertura de tests (133 nuevos)

| Dominio | Archivo | Tests nuevos (aprox.) | Cubre |
|---------|---------|----------------------|-------|
| users | `users/tests.py` | ~18 | cookies httpOnly/CSRF, remember estricto, blacklist en logout, registro anónimo, iexact email/username, token verificación vs primer login, trial de 1 día |
| stores | `stores/tests.py` | ~40 | slug reservado/formato/unicidad/renombre, gating público (blocked/unpublished/plan/flag), contact_email oculto, mapa sin beneficio, captcha (firma, edad, anti-bot, slug-bound, timing), honeypot/mail contacto, dedupe visitas + XFF, stats gated, orden sin duplicados, cuotas bajo lock + huérfano R2, decompression bomb, chatbot gating/saneo, block/unblock staff, campos premium descartados |
| catalog | `catalog/tests.py` (nuevo) | ~22 | 401 anónimo, aislamiento owner (404/405), unicidad iexact por tienda, schema acotado, cupo `max_products`, category/brand ajenos, oferta < precio, features acotadas, remove-background gated |
| suscriptions | `suscriptions/tests.py` (nuevo) | ~18 | alta impaga, trial no seleccionable/asignable, una sola suscripción, update → plan pendiente, scoped list, assign staff/ids defensivos, catálogo sin trial, regex nombre, `grants_access` + gracia |
| payments | `payments/tests.py` | ~16 | replay de firma (ts viejo/ms), checkout ids/ownership/trial/pendiente, external_reference IDOR, monto, idempotencia, cross-suscripción, pending plan, rejected, rollups ±/clamp, listado/approve/admin-summary |
| invoices | `invoices/tests.py` (nuevo) | ~7 | solo approved, idempotente, correlativo, tipo por emisor, listado propio, ajeno 404 |
| legal | `legal/tests.py` (nuevo) | ~10 | denuncia válida + mail, original_work por kind, buena fe, URL/nombre/desc, list/update solo staff |

Nota: los throttles comparten el cache locmem entre tests — las clases que
pegan a endpoints con rate limpio `cache.clear()` en `setUp` para que el
conteo por IP no se herede entre casos.

---

## 5. Re-auditoría independiente — 2026-10-25

Segunda pasada completa (misma base de código, foco adversarial: leer el
sistema como si lo hubiera escrito un tercero) + verificación ejecutable.

**Ejecutado:** `manage.py test` → **219 tests OK** · `manage.py check --deploy`
(solo warnings esperados de flags env-driven + spectacular) · `pip-audit -r
requirements.txt` → **0 CVEs** · `npm audit --omit=dev` → **0 CVEs** (2 en dev:
vite/esbuild, solo afectan `vite dev`) · grep de secretos en el repo → limpio
(`.env` nunca commiteado; la Firebase Web API key es pública por diseño).

### Hallazgos nuevos

| # | Severidad | Hallazgo | Acción sugerida |
|---|-----------|----------|-----------------|
| A | **Media** | `AnonRateThrottle` global `anon: 100/day` aplica a las rutas públicas (`stores/public/*`, catálogo, locations). Bajo CGNAT de carriers móviles miles de usuarios comparten IP → 429 a visitantes legítimos de las webs de clientes. | Scope propio más holgado para GETs públicos de tienda (ej. `store_public: 600/hour`) y/o eximir lecturas GET de la cuota anon. |
| B | **Media-baja** | CSP divergente entre deploys: la de `urls.py::spa` habilita Firebase (gstatic, googleapis, recaptcha) pero la de `docker/web/templates/default.conf.template` no (`script-src 'self'`, `connect-src 'self'`) → verificación por SMS rota en el deploy Docker/nginx. | Sumar los dominios de Firebase/reCAPTCHA a la CSP del vhost. |
| C | **Baja** | `DEFAULT_PERMISSION_CLASSES = DjangoModelPermissionsOrAnonReadOnly`: fail-open — cualquier view futuro sin `permissions` permite lectura anónima. Hoy no expone nada (todos los viewsets definen permisos propios). | Cambiar el default a `IsAuthenticated` (AllowAny se declara explícito igual que ahora). |
| D | **Baja** | `redeem_coupon` nullea `preapproval_id` local sin cancelar en MP: si el usuario tenía débito autorizado y su plan quedó sin acceso (edge: cancelado en MP pero `auto_renew` stale), MP seguiría debitando un preapproval que el sistema ya no conoce. | Si hay `preapproval_id` al canjear, llamar `CancelPreapprovalQuery` antes de limpiar. |
| E | **Baja** | `BG_MODEL_URL` (onnx de rembg) se descarga sin chequeo de integridad. | Pinnar SHA256 del modelo en settings/env. |
| F | **Baja** | `PATCH` devuelve 405 en suscriptions/plans/coupons/payments (los bases definen `update` pero no `partial_update`; `update` ya es partial=True). El frontend usa PUT — funciona, pero la API es inconsistente. | Agregar `partial_update` en los bases afectados. |
| G | **Nota** | `SECURE_*`/cookies `Secure` dependen 100% de .env (defaults False). Si una variable falta en un deploy nuevo, las cookies viajan sin `Secure`. | Verificar el .env de cada entorno al deployar (o endurecer defaults cuando `DEBUG=False`). |

### Límites de esta auditoría (honestidad técnica)

- El .env de producción, el nginx en ejecución, ACL real del bucket R2,
  secretos de MP/Firebase y dominios autorizados **no son verificables desde
  el repo** — se audita la intención, no el despliegue.
- Una suite propia cubre lo que el autor previó; el estándar de industria
  complementa con: pentest externo o segundo revisor, DAST (OWASP ZAP/Burp)
  contra staging, y `pip-audit`/`npm audit` en CI.
