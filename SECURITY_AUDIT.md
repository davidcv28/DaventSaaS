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

### Hallazgos nuevos — estado: **todos remediados** (mismo commit)

| # | Severidad | Hallazgo | Fix aplicado |
|---|-----------|----------|--------------|
| A | **Media** | `AnonRateThrottle` global `anon: 100/day` aplicaba a las rutas públicas (`stores/public/*`, catálogo, locations). Bajo CGNAT de carriers móviles miles de usuarios comparten IP → 429 a visitantes legítimos. | ✅ Nuevo scope `public_read: 1000/hour` (`DaventProject/throttling.py::PublicReadThrottle`) aplicado a `public`/`public_catalog`/`contact_captcha`, `GET /api/plans/`, `GET /api/suscription-plans/` y los 3 viewsets de locations. El scope `anon` sigue como red de seguridad para futuros endpoints anónimos. |
| B | **Media-baja** | CSP divergente entre deploys: la de `urls.py::spa` habilita Firebase pero la de `docker/web/templates/default.conf.template` no → verificación por SMS rota en Docker/nginx. | ✅ `script-src` suma gstatic/google/apis.google; `connect-src` suma identitytoolkit + securetoken + googleapis; `frame-src` suma recaptcha.google.com. Misma whitelist que la CSP del SPA. |
| C | **Baja** | `DEFAULT_PERMISSION_CLASSES = DjangoModelPermissionsOrAnonReadOnly`: fail-open — cualquier view futuro sin `permissions` permitía lectura anónima. | ✅ Default → `IsAuthenticated` (fail-closed). Verificado: todo endpoint público declara `AllowAny`/`IsAnonimous` explícito o `permission_classes = ()` (simplejwt); OPTIONS preflight lo resuelve el middleware CORS antes del view. |
| D | **Baja** | `redeem_coupon` nulleaba `preapproval_id` local sin cancelar en MP: un débito autorizado podía seguir cobrando tras el canje. | ✅ `CancelPreapprovalQuery` se llama antes del atomic si había `preapproval_id` (best-effort fuera de la transacción: un fallo de MP se loguea, no bloquea el canje ni alarga el lock del cupón). |
| E | **Baja** | `BG_MODEL_URL` (onnx de rembg) se descargaba sin chequeo de integridad (supply-chain). | ✅ SHA256 del artefacto oficial pinneado (`BG_MODEL_SHA256` en imaging.py, sobreescribible por env). El archivo cacheado y la descarga se verifican; un mismatch borra el cache y una descarga que no matchea falla cerrado (no se escribe). |
| F | **Baja** | `PATCH` devolvía 405 en suscriptions/plans/coupons/payments; además `partial_update` del mixin en `/api/profile/me/` caía al config `retrieve` y update() pedía `['message']` → 500. | ✅ `partial_update` delegando a `update` en los bases de suscriptions/payments/users + mapeo `partial_update → config 'update'` (sin el mapeo PATCH habría usado el serializer de lectura y permitido escribir `plan_suscription` directo — escalación evitada). |
| F2 | **Baja** | PATCH parcial real rompía en users: `UpdateUserQuery` exigía `email` en el payload (KeyError→500) y `UpdateProfileQuery` reseteaba `phone_verified` si `phone` no viajaba en el PATCH; `UserProfileValidatorsMixins.validate` explotaba (`len(None)`, `None.cities`) con payload parcial. | ✅ `UpdateUserQuery` conserva el email actual si no viaja; `phone_verified` solo se resetea si `phone` está en `validated_data`; el validate() usa los valores de la instancia como fallback. Verificado por smoke test: PATCH parcial 200, flag intacto, PATCH de phone resetea el flag. |
| G | **Nota** | `SECURE_*`/cookies `Secure` dependen 100% de .env (defaults False). | ➖ Pendiente por diseño: endurecer los defaults rompería el runserver local (`localhost` sin TLS). Mitigación real = checklist de .env por entorno (ver abajo). |

### Verificación del `.env` local (2026-10-25)

Auditoría del `.env` del proyecto (sin volcar secretos: solo presencia, longitud
y entropía):

- `SECRET_KEY`: 66 chars, ~340 bits — fuerte, **pero con prefijo
  `django-insecure-`** (es la key generada por startproject). Para dev es
  aceptable (la parte aleatoria tiene entropía suficiente); **si esa misma
  key estuviera seteada en producción, rotarla** (el prefijo solo indica que
  vino del template, no que sea débil — la del deploy de Render es la que
  cuenta y no es verificable desde acá).
- `DEBUG=True`, `ALLOWED_HOSTS=127.0.0.1,localhost`, `CORS` a localhost:5173 —
  correctos para dev; en prod vienen de Render/dashboard.
- `MP_WEBHOOK_SECRET` **ausente** en dev (by design: con DEBUG=True el webhook
  procesa sin firma y loguea warning). **Confirmar que esté seteado en el
  panel de Render y en el `.env` del VPS** — es la variable que más daño hace
  si falta en prod.
- `BACKEND_URL` vacío en dev (sin `notification_url` en los checkouts — el
  webhook no puede alcanzar localhost; necesario en prod).
- Credenciales SMTP (Brevo), R2 y MP presentes con entropía alta; `REDIS_URL`
  ausente → locmem cache en dev (throttles per-process, correcto en local).
- `CLOUD_CL_NAME`/`SECRET_CL_KEY`/`API_CL_KEY`/`ACCOUNT`: credenciales de
  Cloudinary huérfanas (Cloudinary ya no se usa — la app migró a R2) —
  candidatas a limpieza del `.env`.
- `ISSUER_*` (datos fiscales de AFIP) vacíos — necesarios cuando se habilite
  facturación real.

## 6. Segunda auditoría externa (IA independiente) — cotejo y remediación

Una segunda IA auditó el repo en solo lectura (seguridad, ACID, concurrencia,
SOLID, API). Cotejo de sus hallazgos contra el código real:

### Confirmados → remediados

| ID | Hallazgo de la otra IA | Veredicto / fix |
|----|------------------------|-----------------|
| S-02 | `X-Forwarded-For` spoofeable evade throttles | **Válido, pero el diagnóstico era otro sitio**: `_client_ip` ya toma el ÚLTIMO XFF (corregido en la pasada anterior). El hueco real es `SimpleRateThrottle.get_ident` de DRF: sin `NUM_PROXIES` usa el PRIMER XFF → spoofeable. ✅ `REST_FRAMEWORK['NUM_PROXIES'] = NUM_TRUSTED_PROXIES` (default 1 = nginx/Render; 2 si Cloudflare delante). |
| S-04 | `/admin/` sin rate-limit propio | **Válido.** ✅ `AdminLoginRateLimitMiddleware`: 10 POST/5min por IP a `<ADMIN_URL>/login/` (cache Redis en prod). |
| S-06 | logout y verify-resend sin throttle dedicado | **Mitad falso positivo**: `verify-email/resend` ya tenía `email_verification` 5/h. `TokenLogoutView` (AllowAny, blacklistea refresh) no tenía → ✅ scope `logout` 30/h. |
| A-01/A-02 | race en extensión de plan / rollups | **Válido y real**: dos webhooks `approved` concurrentes leían `old_status=PENDING` ambos → rollups duplicados + posible doble factura. ✅ `PaymentWebhookQuery` re-lee el Payment con `select_for_update(of='self')` dentro de la tx y re-evalúa `old_status` bajo lock; `ApplyPendingPlanQuery` bloquea la fila de Suscription. (Nota: `of='self'` es obligatorio — `FOR UPDATE` no aplica al lado nulable de un outer join en Postgres.) |
| A-03 | `UpdateUserQuery` sin `transaction.atomic` | **Válido** (user.email + profile.email_verified en dos saves). ✅ envuelto en `atomic`. |
| C-01 | cancel de débito MP fuera de la tx del canje | **Válido, peor de lo descrito**: el fix anterior cancelaba ANTES de validar → un canje rechazado (cupón inválido/vencido/usado → rollback) dejaba al usuario SIN débito y SIN plan. ✅ `RedeemCouponQuery` (nuevo `suscriptions/services/`, también resuelve D-01) registra `transaction.on_commit(CancelPreapprovalByIdQuery(pid))`: el débito en MP solo se cancela si el canje commitea; fallo de MP queda logueado para `/sync/`. |
| C-02 | llamadas a MP fuera de tx → huérfanos | **Válido parcialmente.** ✅ `CreatePreapprovalQuery` ahora compensa: si el save local falla, cancela el preapproval remoto (saga mínima). Los demás paths ya son idempotentes por `external_reference` + `/sync/`; una saga completa queda como deuda documentada. |

### Falsos positivos / sin acción

| ID | Hallazgo | Por qué no aplica |
|----|----------|-------------------|
| S-03 | "no se observó django-cors-headers" | **Falso**: `corsheaders` está en INSTALLED_APPS + middleware + `CORS_ALLOWED_ORIGINS` por env (settings.py:128,148,249). |
| S-01 | webhook sin firma = crítico | **Sobreestimado**: el bypass sin firma solo existe con `DEBUG=True` (dev local, testeado explícitamente); en prod ya se rechaza con 401+error. Endurecido igualmente: ✅ `payments/checks.py` registra errores `payments.E001/E002` en `check --deploy` si falta `MP_WEBHOOK_SECRET`/`SECRET_MP_KEY` con DEBUG=False. |
| S-05 | API key Firebase en query string | Inevitable: Identity Toolkit REST la exige así; es una key pública por diseño (protección real = Authorized Domains + cuota). |
| A-04 | UpdateProfileQuery sin tx | Una sola fila — `save()` ya es atómico. |
| A-05 | `Payment.approve()` sin tx explícita | Único caller lo invoca dentro de `atomic` (viewset.approve). |
| C-03 | phone verify sin lock | Idempotente (mismo resultado); doble escritura sin efecto. |
| C-04 | retry ciego de IntegrityError en facturas | El retry re-lee la existente y topea en 3; solo puede colisionar la UNIQUE (type,pos,number) que es justo lo que recalcula. |
| D-05 | regex de password duplica validate_password | **No es duplicación**: el regex añade complejidad (mayús+dígito+especial) ENCIMA de AUTH_PASSWORD_VALIDATORS; quitarlo debilitaría la política. |
| API-03 | webhook AllowAny depende solo de HMAC | Además de la firma: `external_reference`→suscripción propia + monto=precio del plan + ventana anti-replay. MP no publica rangos IP estables para allowlist. |
| API-01/02 | sin /api/v1/, respuestas no uniformes | **Válido como deuda de diseño**, fuera de scope: cambiar paths/envelope rompe el frontend; queda en roadmap. |
| D-02/D-04 | SDK a nivel módulo, view_config dicts | Deuda de diseño aceptada; refactor grande sin riesgo de seguridad. |
| API-04/05 | sin Location/ETag | Roadmap. |

### Límites de esta auditoría (honestidad técnica)

- El .env de producción, el nginx en ejecución, ACL real del bucket R2,
  secretos de MP/Firebase y dominios autorizados **no son verificables desde
  el repo** — se audita la intención, no el despliegue.
- Una suite propia cubre lo que el autor previó; el estándar de industria
  complementa con: pentest externo o segundo revisor humano, DAST (OWASP
  ZAP/Burp) contra staging, y `pip-audit`/`npm audit` en CI.
- Estado tras esta pasada: 219 tests OK; ambas auditorías coinciden en que no
  hay hallazgos críticos abiertos en el código — el residual es de despliegue
  (env vars en prod) y de validación humana externa pendiente.

## 7. Cierre — segunda pasada de la IA externa sobre `5c07a52`

La IA externa re-auditó el HEAD con todos los fixes y concluyó igual que esta
auditoría: **sin hallazgos críticos abiertos en el código**; confirmó además
los controles agregados (throttle `logout`, saga de compensación en
preapproval, `RedeemCouponQuery` + `on_commit`, fail-closed, SHA256 del
modelo ONNX, CSP alineada nginx/SPA) y la sincronía docs↔código.

### Falso positivo verificado

- **§4.2 "admin sin rate-limit"**: incorrecto — `AdminLoginRateLimitMiddleware`
  (`DaventProject/middleware.py`, registrado en `MIDDLEWARE`) ya corta el
  brute-force del login del admin a 10 POST/5min por IP sobre
  `<ADMIN_URL>/login/`, desde el propio commit auditado. (`django-axes`
  NO está instalado; sería una capa adicional opcional, no una dependencia
  del control actual.)

### Notas operativas / deuda técnica (no son bugs)

- **§4.5 throttling sin Redis en multi-instancia**: con `locmem` cada proceso
  cuenta sus propios límites — documentado en settings; en prod `REDIS_URL`
  está seteado. Nota de escalado, no defecto.
- **§4.7 OneToOne + UniqueConstraint redundantes en `Suscription`**:
  redundancia de esquema inofensiva; se deja como está.
- **§4.8 sin ESLint en CI**: real, pero se **difere** deliberadamente — el
  frontend puede acumular warnings que romperían el pipeline; se evalúa
  cuando el código frontend pase lint limpio.
- **Checklist de despliegue** (residual de ambas auditorías): `.env` de prod
  completo (SECRET_KEY, SECRET_MP_KEY, **MP_WEBHOOK_SECRET**, R2_*, ISSUER_*
  fiscales, AFIP_*, EMAIL_HOST_PASSWORD), `ADMIN_URL` no obvio,
  `CSRF_TRUSTED_ORIGINS` con el dominio real, `R2_PUBLIC_URL`, Authorized
  domains en Firebase, ACL del bucket R2, `NUM_TRUSTED_PROXIES=2` si hay
  Cloudflare delante. Los deploy checks `payments.E001/E002` hacen falible
  el deploy sin credenciales MP.

**Cierre de la auditoría estática**: dos revisiones independientes sobre dos
estados del repo arrojan resultados consistentes. Lo que queda fuera del
alcance de cualquier lectura de código es la validación del despliegue real y
un pentest/revisor humano externo — el siguiente paso recomendado es DAST
(OWASP ZAP/Burp) contra staging.

## 8. Simulación de ataque al sistema de pagos — 2026-10-25 (cotejo + remediación)

Una simulación adversarial de 5 vectores sobre el flujo de Mercado Pago fue
cotejada contra el código real. Resultado corregido: **2 falsos positivos,
1 edge de consistencia (remediado), 1 brecha condicional (remediada) y
1 defensa confirmada**.

| # | Vector | Veredicto cotejado | Acción |
|---|--------|--------------------|--------|
| V-1 | Replay de webhook con firma válida dentro de la ventana de 10 min | **Falso positivo**: la idempotencia no falta — vive a nivel `Payment` (`external_reference` unique + `select_for_update(of='self')` + relectura de `old_status` → segundo `approved` sin `renew`, sin rollup ni factura). `IssueInvoiceQuery` devuelve la existente. | ✅ Endurecido igual: dedup de entregas por `x-request-id` en cache (`WEBHOOK_DEDUP_SECONDS=600`, fail-open, marca solo tras procesar OK) — el replay ya ni siquiera pega a la API de MP. |
| V-2 | Race en cupón `max_uses=1` multiusuario | **Falso positivo**: `Coupon.objects.select_for_update()` dentro de `atomic()` retiene el lock de fila hasta el commit — el `redemptions.count()` del segundo ya ve la redención del primero (READ COMMITTED por statement). Serialización total en la fila del cupón. | Sin cambio (el lock existente es la mitigación correcta). |
| V-3 | Canje de cupón con débito MP vivo (`PENDING_PAYMENT` + `preapproval_id`) | **Válido como edge de consistencia (bajo)**: un cobro en vuelo de MP podía entrar con el plan ya pisado por el cupón — si el monto no coincidía con el nuevo plan quedaba huérfano sin acreditar (sin ganancia para el atacante: los días del cupón se pisan, no se acumulan). | ✅ `RedeemCouponQuery` rechaza el canje con `preapproval_id` sin `cancelled_at` — hay que dar de baja el débito primero. El `on_commit(CancelPreapprovalByIdQuery)` quedó obsoleto y se eliminó (baja confirmada ⇒ nada que cancelar). |
| V-4 | Webhook sin firma con `DEBUG=True` en producción | **Válido condicional a misconfig** (era el único bypass: `DEBUG=True` + secret vacío procesaba sin verificar; además `checks.py` retornaba temprano con DEBUG → `check --deploy` no lo flagueaba). | ✅ El bypass ahora exige opt-in explícito `MP_WEBHOOK_ALLOW_UNSIGNED=True` **además** de `DEBUG=True`; nuevo check `payments.E003` marca el flag en `check --deploy`. `DEBUG=True` solo ya nunca abre el endpoint. |
| V-5 | IDOR con `payment_id` ajeno | **Defensa confirmada**: ownership por `external_reference` + rechazo de pago existente de otra suscripción (regresión del hallazgo #4, §1). | Sin cambio. |

Tests nuevos/actualizados: `payments/tests.py` (unsigned solo con flag+DEBUG,
rechazo sin flag en DEBUG, flag inerte fuera de DEBUG, dedup por request-id,
request-ids distintos sí procesan) y `suscriptions/tests.py` (canje rechazado
con débito vivo conservando suscripción intacta, canje permitido con baja
confirmada `cancelled_at`).

## 9. Segunda ronda de simulación — 2026-10-25 (cotejo + remediación)

Segunda simulación adversarial de 5 vectores sobre el mismo flujo, cotejada
contra el código: **3 falsos positivos, 1 race real pero inofensiva
(endurecida igual), 1 edge de consistencia real (remediado)**.

| # | Vector | Veredicto cotejado | Acción |
|---|--------|--------------------|--------|
| W-1 | Race `cache.get`+`set` en el dedup por `x-request-id` | **Race real, impacto nulo**: dos entregas concurrentes podían procesar a la vez, pero la idempotencia real (`external_reference` unique → IntegrityError → existente; `select_for_update` + `old_status` → sin doble rollup/factura/`renew`) lo absorbía. Además el vector descrito era incorrecto: la firma cubre `id:<data.id>` en el manifest — un replay no puede cambiar el `payment_id`. | ✅ Endurecido: `cache.add` atómico para clamar la entrega + `cache.delete` si el procesamiento falla (el retry de MP con el mismo request-id reintenta). Dedup ahora también correcto entre workers. |
| W-2 | `pending_plan` con débito activo → plan sin cobro del nuevo monto | **El vector narrado es falso** (MP no cobra "el monto viejo y se aplica el nuevo": `subscription` ya llama `UpdatePreapprovalPlanQuery` y `CreatePaymentQuery` exige monto = precio del plan). **Pero el cotejo encontró el hueco real**: `checkout` seteaba `pending_plan` con `preapproval_id` vivo sin realinear el monto en MP → el próximo débito cobraba el precio viejo y el webhook lo rechazaba → cobro huérfano. | ✅ `checkout` ahora llama `UpdatePreapprovalPlanQuery` cuando hay débito vivo (`preapproval_id` sin `cancelled_at`) y cambió el plan objetivo (pending_plan o suscripción impaga). Débito cancelado queda fuera (MP rechazaría el update). |
| W-3 | Cancelación de débito ajeno vía `cancel-renewal` | **Falso positivo**: el action es `detail=False` y resuelve `Suscription.objects.filter(user__user=request.user)` — no acepta ningún id del request. | Sin cambio + test de regresión (`CancelRenewalOwnershipTests`). |
| W-4 | Pago con monto alterado inferior al plan | **Falso positivo**: `CreatePaymentQuery` exige `transaction_amount == plan_price` (services.py:75-80) — más estricto que el `>=` propuesto. La simulación no leyó esa sección. | Sin cambio (ya cubierto por `test_amount_mismatch_rejected`). |
| W-5 | Webhook `authorized_payment` tardío tras canje de cupón | **Ya mitigado por el fix de la ronda 1**: el canje exige `cancelled_at` (baja confirmada en MP) antes de pisar la suscripción — la ventana quedó reducida a cobros ya ejecutados por MP antes de la baja. Residuo honesto: si ese cobro existe y su monto ≠ precio del plan nuevo, el `Payment` no se registra → reconciliación manual vía panel MP (el dinero sí se cobró — no hay ganancia para el atacante ni cargo sin rastro en MP). | Documentado como residual aceptado; registrar/alertar cobros huérfanos queda como mejora futura (no trivial: distinguir débito stale de pago manual legítimo sin romper la acreditación). |

Tests nuevos: `payments/tests.py` (`test_failed_processing_releases_dedup_key`,
alineación de preapproval en checkout con débito vivo / skip sin débito /
skip con débito cancelado, `CancelRenewalOwnershipTests`).
