# Auditoría de seguridad DAVENT — backend

**Fecha:** 2026-10-24 · **Alcance:** `AdminApp/`, `StoreApp/`, `SuscriptionApp/`, `DaventProject/`
**Suite:** 269 tests — `manage.py test` → OK (sección 12: valoraciones/comentarios)

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

## 10. Tercera ronda de simulación — 2026-10-25 (cotejo: 5 falsos positivos)

Tercera y última simulación de 5 vectores; todos refutados contra el código.
La ronda asumió comportamientos sin leer las secciones relevantes — mismo
patrón que las anteriores (ronda 1: 2/5 falsos, ronda 2: 3/5, ronda 3: 5/5).

| # | Vector | Veredicto cotejado |
|---|--------|--------------------|
| Y-1 | `back_url` manipulada en la preferencia / robo de `payment_id` | **Falso positivo**: la preferencia se arma 100% server-side — `back_urls` de `FRONTEND_URL` (env), `unit_price = plan.price`, `external_reference = suscription.id` (services.py:254-266). El request de `checkout`/`subscription` solo acepta ids de suscripción/plan. Y un `payment_id` robado solo puede acreditar la suscripción del propio pagador (`external_reference == suscription.id` por `request.user`) — ganancia del atacante: cero. |
| Y-2 | IDOR en `/sync/` con `preapproval_id` ajeno | **Falso positivo**: `sync` resuelve `filter(user__user=request.user)` y no lee `preapproval_id`/`suscription_id` del request (viewset.py:296). El único parámetro (`payment_id`) se contrasta contra el `external_reference` real de MP — ajeno → `[]`. |
| Y-3 | `pending_plan` activado sin pago aprobado | **Falso positivo**: `ApplyPendingPlanQuery` solo se invoca tras verificar el cobro en la API real de MP (`CreatePaymentQuery`, `PaymentWebhookQuery`) o desde `approve` (`IsAdminUser`, sobre un `Payment` ya creado vía verificación MP). Setear `pending_plan` no otorga acceso: `grants_access` exige ACTIVE + vigencia, y aplicarlo exige cobro approved del monto del plan pendiente. |
| Y-4 | Replay de webhook `subscription_preapproval` para alterar débito ajeno | **Falso positivo**: el manifest HMAC cubre `id:<resource_id>` — el `preapproval_id` no es cambiable sin invalidar la firma. Además `PreapprovalWebhookQuery` hace GET a MP y espeja el estado remoto: el body del webhook ni se lee, un replay solo re-sincroniza la verdad de MP. El dedup atómico absorbe replays del mismo `x-request-id`. |
| Y-5 | Doble pago `approved` extiende el acceso (60 días por 1) | **Falso positivo**: `ApplyPendingPlanQuery` hace `end_date = now + 30d` — reinicia, nunca acumula (services.py:188-191). El segundo pago además debe ser real en MP con monto = precio del plan: quien lo intenta paga dos veces por los mismos 30 días (perjuicio propio → reembolso, no ganancia). |

Sin correcciones — la regla de los 5 intentos no aplica al no haber brecha
abierta. Balance de las 3 rondas: 15 vectores simulados → **3 issues reales
remediados** (bypass de firma unsigned, canje de cupón con débito vivo,
preapproval desalineada en checkout) + **1 hardening defensivo** (dedup
atómico de webhooks) + 10 falsos positivos documentados.

## 11. Auditoría del feature: descuentos programados del catálogo — 2026-10-25

Revisión de seguridad del nuevo modelo `Discount` (mig. catalog.0005) y su
superficie: CRUD `/api/discounts/` + aplicación en `public_catalog`.
La automatización se implementó por **evaluación al leer**
(`running_discounts_of`/`effective_offer_of` en `catalog/services`) —
el estado vigente se resuelve en cada request con `timezone.now()`, nunca se
materializa en `offer_price` ni depende de Celery Beat: no hay ventana de
precios stale ni un job que un atacante pueda interferir.

### Controles aplicados (diseño)

| Control | Dónde |
|---------|-------|
| **Aislado por dueño**: queryset scoping `store=my_store()` en list/retrieve/update/destroy — un id ajeno devuelve 404, nunca 403 con fuga de existencia | `DiscountViewSet` / `viewset_config` |
| **Gate de suscripción**: mismo `catalog_enabled()` que el resto del catálogo (exige `has_public_link` vigente) → 403 sin plan | `viewset_config` |
| **Objetivos del alcance validados server-side**: `scope=category|brand` exige el FK **y que pertenezca a la tienda del owner**; `scope=products` exige ≥1 producto propio (queryset filtrado por `store` — ids ajenos se cuentan como faltantes → 400) | `DiscountMixinValidator` |
| **Porcentaje acotado en dos capas**: `percent` 1–99 con `MinValue/MaxValueValidator` **y** `CHECK` en DB (`ck_discount_percent_range`) — ni 0% inútil ni 100%+ que regale el producto | `models.py`, `config_fields.DiscountFields` |
| **Ventana coherente**: `ends_at > starts_at` obligatorio; `ends_at` null = sin fin explícito (no ambigüedad con "vencido") | `DiscountMixinValidator` |
| **Tope defensivo de selección**: `scope=products` limita a `DiscountLimits.products_max` (500) — evita payloads gigantes en el M2M | `DiscountMixinValidator` |
| **Limpieza de restos**: cambiar de `scope` nulifica los campos del alcance anterior — un descuento no puede heredar productos de una configuración previa | serializer `update`/`create` |
| **Precio efectivo seguro**: `effective_offer_of` toma el **mínimo** entre oferta manual y descuentos solapados, clamp a ≥0 con `quantize` — un % extremo nunca produce precio negativo | `services.py` |
| **Sin inyección en filtros públicos**: los descuentos no agregan parámetros nuevos al endpoint público; `?min_price/max_price` siguen pasando por `_price_bound` y el sort por whitelist `CATALOG_SORTS` (el orden por precio se hace en Python sobre el queryset acotado, jamás `order_by` crudo) | `stores/views/viewset.py` |
| **Vista pública fail-closed**: los descuentos solo enriquecen `offer_price` del payload existente — no exponen endpoints nuevos AllowAny | `public_catalog` |

### Tests agregados (`catalog/tests.py`, suite 42 → OK)

- `DiscountTests` (aislamiento: list/update/delete ajenos → 404; percent fuera
  de rango → 400; `ends_at ≤ starts_at` → 400; scope inválido o sin objetivo →
  400; categoría/producto ajenos → 400; create+toggle; cambio de scope limpia
  restos).
- `DiscountPublicTests` (descuento vigente baja el `offer_price` público;
  programado/vencido/pausado no aplican; oferta manual gana si es menor;
  scope por categoría solo cubre esa categoría; `?min_price` filtra con el
  precio ya descontado; el list del owner expone `discount_offer`/`discount_names`).

### Residuales honestos (documentados, no bugs)

- **Carga del listado público**: `running_discounts_of` trae los descuentos
  vigentes de la tienda y `discount_price_of` itera el M2M por producto —
  O(productos × descuentos) en memoria. Acotado por `max_products` del plan y
  por el propio catálogo del dueño; sin índice extra necesario a este volumen.
- **Sin auditoría de cambios**: crear/editar/borrar descuentos no queda en un
  log de auditoría propio (igual que el resto del catálogo — cubierto por el
  logging de requests de la sección 3).
- **Zona horaria**: las ventanas se guardan/comparan en UTC (`USE_TZ`); el
  frontend convierte `datetime-local` ↔ ISO (`localInputToIso`/`isoToLocalInput`).
  Un desfasaje del reloj del cliente solo afecta lo que el dueño ve, no la
  vigencia server-side.

### Addendum 2026-10-25 — metadata de descuentos en el catálogo público

`public_catalog` ahora expone `promotions[]` (nombre, %, alcance y
vencimiento de los descuentos vigentes) y `product.discount`
(`{name, percent, ends_at}` del descuento que firma la oferta).
Superficie revisada: solo datos de marketing que el dueño escribió para
publicar; los `category`/`brand` ids ya viajaban en las mismas respuestas
(`categories`/`brands` del payload). `is_active`, `products` M2M, ids de
descuento y `store` **no** se exponen. La regla "el descuento firma solo
cuando gana" (`effective_pricing_of`) evita mostrar una promo que no
corresponde al precio mostrado — consistencia, no solo seguridad.

**Verificación ejecutada**: `manage.py check` 0 issues · `manage.py test`
250 tests OK · `npm run build` (Vite) OK.

### Addendum 2026-10-26 — exclusividad de productos entre grupos de ofertas

`DiscountMixinValidator` ahora rechaza (400) que un producto quede en dos
descuentos con `scope=products` cuya ventana siga viva: el solape se evalúa
contra descuentos con `ends_at` null o futuro — el terminado libera y el
pausado también bloquea (reactivarlo recrearía el conflicto). Se excluye el
propio registro en update y el mensaje nombra el descuento ocupante. El
picker del dashboard los muestra deshabilitados con el nombre del grupo
(`discountTakenBy`) — UX adelantada, no sustituto del gate server-side.
Cubierto por `test_product_lives_in_one_products_discount_only`.

## 12. Auditoría del feature: valoraciones y comentarios de productos — 2026-10-26

Revisión del nuevo modelo `ProductReview` (mig. catalog.0006 — **revisado
2026-10-26**: el voto pasó de `rating` 1-5 a `is_positive` like/dislike
nullable; la mig. catalog.0007 convierte los datos existentes (rating ≥3 →
positivo) antes de borrar el campo), los flags
`StoreCustomization.show_reviews`/`show_comments` (mig. stores.0031) y su
superficie: `GET .../reviews/captcha/`, `GET/POST
.../products/<id>/reviews/` públicos y `GET/DELETE /api/reviews/` del dueño.

### Controles aplicados (diseño)

| Control | Dónde |
|---------|-------|
| **Antispam en capas** (idéntico al contacto auditado): captcha aritmético firmado con `TimestampSigner` (la respuesta viaja como hash SHA-256, nunca en claro), edad máxima 10 min, **mínimo 3s** entre emisión y envío (anti-bot), honeypot `website` con 201 genérico sin persistir, throttle `store_review` 10/h por IP | `services/contact.py`, `stores/views/viewset.py`, settings |
| **Fricción exigida por diseño del producto**: nombre + apellido + email obligatorios en todo envío — aunque solo deje su voto | `ReviewCreateSerializer` |
| **Privacidad del autor**: el email y el apellido completo jamás salen en la API pública — `ReviewPublicSerializer` expone `surname` como inicial; solo el dueño autenticado los ve en moderación | serializers |
| **Feature gates server-side en cascada**: la tienda debe estar publicada, sin bloqueo, con suscripción vigente, `has_public_link`, catálogo encendido y producto activo — mismos 404/403 que el catálogo; además `is_positive` exige `show_reviews` y `text` exige `show_comments` **más** el flag `has_product_comments` del plan (premium/trial; `PATCH customization` lo descarta sin el flag) | `_review_store`/`_review_product` |
| **Contenido mínimo garantizado en DB**: `ck_review_vote_or_text` (voto like/dislike o texto — algo tiene que traer) — segunda capa tras el serializer | models |
| **Moderación aislada por dueño**: `/api/reviews/` scoping `store=my_store()` — borrar una opinión ajena da 404; create/update/retrieve bloqueados con 405 (`http_method_names`) — el alta solo nace en la web pública | `ReviewViewSet` |
| **Sin XSS**: el texto es `CharField` plano renderizado como `{{ r.text }}` en Vue (escapado nativo); sin `v-html` | `ProductReviews.vue` |
| **Aggregates acotados**: `rating_avg`/`rating_count` se anotan solo si `show_reviews` (sin el flag viajan null — la web no muestra la fila de valoración) | `public_catalog` |
| **Sin enumeración de existencia**: producto ajeno a la tienda o inactivo → 404, igual que catálogo inexistente | `_review_product` |

### Tests agregados (`catalog/tests.py`, suite 270 → OK)

- `ProductReviewPublicTests`: GET lista (sin email, apellido como inicial);
  POST feliz con voto+texto; captcha inválido/vencido/muy rápido → 400;
  voto sin `show_reviews` → 400; texto sin `show_comments` → 400;
  comentarios sin `has_product_comments` → 400; producto inactivo → 404;
  honeypot → 201 sin persistir.
- `ReviewOwnerTests`: list scoping (no ve ajenas), delete propio OK / ajeno
  404, POST/PATCH/PUT → 405, sin suscripción → 403.
- `ReviewCustomizationTests`: PATCH `show_comments` sin flag → queda False;
  serializer público devuelve `show_comments=False` sin el beneficio.

### Residuales honestos (documentados, no bugs)

- **Sin pre-aprobación**: las opiniones se publican directo y el dueño modera
  borrando (decisión de producto: fricción de captcha+datos ya filtra; la
  moderación posterior queda en su pestaña Opiniones).
- **Emails de visitantes en DB**: se guardan para contacto del comercio ante
  abuso — mínimo necesario, nunca expuestos públicamente; un futuro purgado
  por antigüedad es mejora posible.
- **Cache 30s del catálogo público**: un borrado de opinión tarda ≤30s en
  reflejarse en el `rating_avg` de la grilla (la lista de opiniones es endpoint
  aparte, sin cache) — staleness acotada y consistente con el resto.
- **Sin dedupe de reseñas**: el mismo visitante puede opinar varias veces
  (pasa captcha cada vez, 10/h por IP) — spam real exige resolver captchas
  manualmente, costo razonable vs. exigir cuenta.

**Verificación ejecutada**: `manage.py check` 0 issues · `manage.py test`
270 tests OK · `npm run build` (Vite) OK.

## 13. Auditoría general — delta post-§12 (2026-10-26)

Pasada sobre todo lo incorporado desde la §12: login social con Google,
gate `billing_required` del checkout, headers del SPA (COOP/CSP para GIS),
retirada de Firebase Phone Auth y de la feature WhatsApp (add+revert).
Verificación ejecutable del HEAD actual.

**Ejecutado:** `manage.py check --deploy` → solo warnings `drf_spectacular.W001`
de type hints (sin issues de seguridad) · `pip-audit -r requirements.txt` →
**0 CVEs** · `npm audit --omit=dev` → **0 vulnerabilities** · `manage.py test`
→ suite OK.

### Verificado como correcto

| Área | Veredicto |
|------|-----------|
| **Login Google — verificación server-side** | `VerifyGoogleCredentialQuery` consulta `tokeninfo` de Google (firma+issuer los valida Google), exige `aud == GOOGLE_CLIENT_ID` (un ID token de otra app no sirve) y `email_verified=true`. El email/nombre salen del token, nunca del body del cliente. Token trucho/ajeno → 400 genérico sin revelar causa. |
| **Login Google — find-or-create** | `SocialLoginQuery`: alta nueva con `set_unusable_password` (sin clave local: el reset la crea si quiere), `email_verified` sellado (Google ya lo verificó → no se manda mail redundante), TyC en `TERMS_VERSION` vigente y plan trial — mismas garantías que `RegisterUserQuery`. `IntegrityError` en alta concurrente → login de la cuenta ya creada (no duplica). Merge por email: si existe cuenta con ese correo verificado por Google, entra directo (auto-link estándar — Google garantiza titularidad). |
| **Login Google — sesión y límites** | `_social_session_response` emite exactamente la misma sesión que el login con clave: access en memoria + refresh httpOnly scopeado `/api/token/` + CSRF doble-submit + `remember` respetado. Throttle `social_auth` 20/h por IP (cada exchange pega a Google). Kill switch: `GOOGLE_CLIENT_ID` seteado vacío → 503 y botón oculto. `_social_error` no filtra si la cuenta existe. |
| **Alta social sin celular** | Google no provee phone → `profile.phone=None` y la respuesta trae `requires_phone=true` → el frontend lleva a `/completar-celular`. El claim de la web sigue exigiendo phone — el ancla anti-abuso se conserva sin bloquear el ingreso al panel. |
| **GOOGLE_CLIENT_ID embebido en código** | El default hardcodeado es un **identificador público** (viaja en la URL del iframe de Google que todo visitante recibe — no puede ser secreto por diseño). No es una credencial: el Client Secret **no** está en el repo ni se usa (el flujo del botón verifica el ID token directo). Env var lo sobreescribe; seteada vacía apaga la feature. |
| **Headers del SPA para GIS** | CSP suma `accounts.google.com` (script/frame/connect) y `ssl.gstatic.com` (style) — whitelist exacta de la guía de Google Identity Services. `Cross-Origin-Opener-Policy: same-origin-allow-popups` (en vez del `same-origin` default de Django): mantiene aislamiento pero permite que el popup de Google haga `postMessage` de vuelta — sin esto el popup queda en blanco tras elegir la cuenta. Solo se aplica a la respuesta del SPA; la misma CSP/COOP quedó espejada en el template nginx (`docker/web`). |
| **Gate `billing_required`** | `_resolve_suscription` (compartido por `checkout` y `subscription`) llama `BillingMissingFieldsQuery` **antes** de cualquier llamada a MP → 400 con la lista de campos faltantes. La suscripción impaga se crea igual (válido: nace `PENDIENTE_PAGO`, no otorga nada). Fail-closed server-side — el form del dashboard es solo UX, saltearlo con un POST a mano no inicia cobro. |
| **Retirada Firebase Phone Auth** | Vistas, URLs, service, throttle scope, exports, config `firebase` del frontend, dep `firebase` (package.json), dominios Firebase/reCAPTCHA fuera de **ambas** CSP (SPA + nginx template), vars `VITE_FIREBASE_*`/`FIREBASE_API_KEY` fuera de ejemplos/Dockerfiles/render.yaml. `phone` sigue `required`+`unique` (ancla anti-abuso debilitada pero presente); `phone_verified`/`_at` quedan en el modelo como histórico y `UpdateProfileQuery` los resetea al cambiar el número. |
| **Retirada WhatsApp digest** | Revertida completa: service/tasks/comando/celery-beat/cron/`WHATSAPP_*`/flag `has_whatsapp_digest`/checkbox/tests — la mig. `0009` elimina las columnas ya desplegadas por la `0008`. El campo `whatsapp` del storefront (contacto del comercio) se conservó — no es la automatización. |

### Residuales honestos (documentados)

- **Auto-link por email verificado**: una cuenta local con el mismo correo que
  una cuenta Google absorbe el login social (no se pide la clave local).
  Estándar de la industria (Google atestigua la titularidad del correo); el
  riesgo residual — que alguien pre-registre el email de otro — es el mismo
  vector de siempre del alta por email, mitigado porque el trial exige
  verificación y el claim exige celular único.
- **`GOOGLE_CLIENT_ID` público por diseño**: quien copie el ID puede
  renderizar el botón de Google en otro origen — pero los Authorized
  JavaScript Origins de la consola lo rechazan (ese es el control real, no
  el secreto del ID).
- **COOP relajado a `same-origin-allow-popups`**: el popup queda con
  referencia al opener — requisito de GIS; alternativa (redirect flow)
  exigiría redirect URIs y un backend callback. Riesgo: un popup propio
  malicioso podría leer `window.opener` — solo abrimos popups de Google.
- **Celular sin verificar**: tras la retirada de Firebase, `phone` es
  único pero no probado — ancla anti-abuso más débil (un atacante puede
  inventar números únicos). Compensación: el trial tiene 1 día y el claim
  exige email verificado; si el abuso crece, reintroducir verificación con
  un proveedor de cuota mayor es la mitigación documentada.

## 14. Auditoría del feature: chat de soporte cliente ↔ staff — 2026-10-26

Revisión del nuevo dominio `AdminApp/domains/chat` (mig. chat.0001):
`ChatThread` (un hilo por cliente, OneToOne→User), `ChatMessage`
(`from_staff`, `body` ≤2000, `read_at` para no-leídos) y `ChatPresence`
(heartbeat con ventana de 120s). Superficie: `GET /api/chat/` (role-aware),
`GET /api/chat/messages/` (incremental), `POST /api/chat/send/`,
`POST /api/chat/heartbeat/`. Transporte: **polling + heartbeat** — el deploy
corre gunicorn sync (sin Channels/Daphne): websockets quedaron descartados
por incompatibilidad de infraestructura, no por capricho.

### Controles aplicados (diseño)

| Control | Dónde |
|---------|-------|
| **Gate premium fail-closed**: todo action exige `IsAuthenticated` + `chat_enabled` — el cliente necesita el flag `has_support_chat` vigente (Premium + prueba) → **403**; staff siempre habilitado (es el lado que responde). Frontend oculta la sección pero el gate real es server-side | `viewset._gate` / `services.chat_enabled` |
| **Aislado por dueño**: el cliente lee y escribe solo SU hilo (`OneToOne` resuelto por `request.user`); el parámetro `?thread=` del endpoint messages **se ignora para clientes** — pedir un id ajeno devuelve el propio hilo, nunca datos de otro. Staff resuelve `?thread=<id>` libre | `viewset._resolve_thread` / `send` |
| **`from_staff` jamás del request**: lo fija `send_message` desde `sender.is_staff` — un cliente no puede simular mensajes del staff | `services.send_message` |
| **Presencia con vencimiento**: "conectado" = heartbeat dentro de `ONLINE_SECONDS` (120s); sin latido fresco el usuario aparece offline — no existe un booleano eterno. La lista `online` del staff excluye empleados (`user__is_staff=False`) | `ChatPresence`, `services` |
| **Privacidad del staff hacia el cliente**: los mensajes del staff exponen `sender_name='Soporte'` — nunca nombre, email ni id del empleado | `ChatMessageSerializer.get_sender_name` |
| **Throttles dedicados**: scopes `chat` (1500/h, polling+heartbeat — el `user` default de 1000/día mataría el polling en ~40 min) y `chat_send` (120/h por usuario, spam) aplicado solo al action `send` vía `get_throttles()` | `viewset`, settings |
| **Validación**: body trim obligatorio 1–2000 chars → 400; `thread` inexistente → 404; `after` no numérico → 0 (sin 500) | `ChatSendSerializer`, `viewset` |
| **Lectura marca leídos solo de la contraparte**: `mark_counterpart_read` toca `read_at` de mensajes ajenos al lector — los propios no cuentan | `services.messages_payload` |
| **Índices**: (thread, created_at) para el historial incremental y (thread, from_staff, read_at) para los contadores de no-leídos; bandeja del staff con `unread_count` anotado (sin N+1) | `models.Meta`, `staff_threads_queryset` |
| **Sin XSS**: `body` es texto plano renderizado `{{ m.body }}` en Vue | templates |

### Tests agregados (`chat/tests.py`, 21 → suite 306 OK)

- `ChatGateTests`: anónimo 401 en los 4 endpoints; sin beneficio → 403;
  sin suscripción → 403; premium OK; staff sin beneficio OK.
- `ChatMessagingTests`: primer envío crea el hilo; staff responde con
  `from_staff`/`sender_name='Soporte'`; staff sin hilo o hilo inexistente
  → 404; `?thread=` ajeno ignorado por clientes (cae en el propio);
  incremental `?after=` devuelve solo nuevos; cliente sin hilo → 404;
  staff lee cualquier hilo; body vacío/blank/2001 → 400; leer marca
  contraparte y limpia el badge; bandeja expone identidad del cliente.
- `ChatPresenceTests`: heartbeat marca online; `staff_online` visible para
  el cliente; presencia expira con `last_seen` viejo; la lista `online`
  del staff excluye empleados; el payload del cliente nunca filtra
  identidad del staff.

### Residuales honestos (documentados, no bugs)

- **Polling, no push**: la latencia percibida es ~5s (intervalo del
  frontend). Si la plataforma migra a ASGI/Redis, `ChatMessage`/`ChatPresence`
  ya sirven de modelo para un consumer de Channels.
- **`last_message` por hilo**: la bandeja hace una query por conversación
  (N+1 acotado por cantidad de clientes con chat — volumen bajo; el unread
  sí va anotado).
- **Sin adjuntos**: solo texto — una decisión deliberada (adjuntos abrirían
  vector de uploads, AV scan y cuota R2). Si se agregan, reutilizar el
  pipeline de imágenes auditado en §1/#6.
- **Presencia compartida por pestañas**: dos tabs del mismo usuario hacen
  heartbeat con la misma fila — correcto (misma identidad).
- **Historial ilimitado**: los mensajes no expiran ni se purgan — política
  de retención queda como mejora futura (la bandeja crece con el tiempo;
  paginación por `after` ya la soporta).

**Verificación ejecutada**: `manage.py check` 0 issues · `manage.py test`
306 tests OK · `npm run build` OK · migración `chat.0001` aplicada ·
`seed_benefits` actualiza el flag en cada entorno.

---

## 15. Auditoría de infraestructura: contenedores, Redis y pipeline — 2026-10-27

**Alcance:** `docker/api/Dockerfile`, `docker/web/Dockerfile`, `docker-compose.yml`,
`docker/api/entrypoint.sh`, `.dockerignore`, `docker/web/templates/default.conf.template`
(plantilla de vhost) y `.github/workflows/ci-cd.yml`.
**Commit de remediación:** `e78f2b1` (`fix: harden container/CI stack`).

### 15.1 Hallazgos remediados

| Sev. | Hallazgo | Remediación |
|------|----------|-------------|
| **P0** | El job `test` no definía `MP_WEBHOOK_SECRET` → `payments.E001` (check `deploy=True`) devolvía **exit 1**. Con `test` rojo, `build` (`needs: [lint, test]`) y `deploy` nunca corrían: **ningún push a `main` llegaba al VPS** | Dummy `MP_WEBHOOK_SECRET` de CI (no es un secreto real) + `SECRET_KEY` de 50+ chars |
| **P0** | Redis sin `maxmemory` (default `0`) ni política: con cgroup de 256M el kernel lo mataba por OOM (Redis no lee cgroup limits). Al caer, `RedisCache` lanzaba en cada `INCR` del throttle → **500 en toda la API**; y las tareas en vuelo de Celery se perdían | `--maxmemory 256mb` + `--maxmemory-policy volatile-lru` (evicta solo claves con TTL: contadores de throttle y caché; las listas del broker no tienen TTL y nunca se tocan) + cgroup 384M |
| **P0** | La imagen `web` corría **nginx como root** (sin `USER`), con `NET_BIND_SERVICE` regalado para el puerto 80 | `nginxinc/nginx-unprivileged` (uid 101, 8080/8443); sin `NET_BIND_SERVICE` |
| **P1** | `cancel-in-progress: true` en el `concurrency` del workflow **abortaba deploys a mitad de camino** (entre `compose pull` y `up -d`) | `concurrency: deploy-production` con `cancel-in-progress: false` a nivel de job |
| **P1** | `.dockerignore` no excluía `docker/certbot/` ni `*.pem`/`*.key`: el token de Cloudflare del ACME DNS-01 podía hornearse con `COPY . .` y publicarse en GHCR | Patrones agregados al `.dockerignore` |
| **P1** | El deploy no verificaba la host key SSH (MITM sobre el canal que mueve secretos) y `up -d` reportaba verde con contenedores en crash-loop | `fingerprint` pineada + `up -d --wait --wait-timeout 180` + `curl /healthz/` |
| **P1** | `build` no dependía de `security`: la imagen se publicaba en GHCR antes del SAST | `needs: [lint, test, security]` |
| **P2** | El SPA se compilaba **3 veces** por pipeline (lint + 2 Dockerfiles); `migrate` duplicaba el trabajo de `manage.py test`; `load: true` exportaba 800MB-1.5GB al daemon en cada PR | Lint sin build del SPA; `makemigrations --check`; sin `load` en PR |
| **P2** | Cada restart de `api` repetía `collectstatic` + `migrate` (~4-6s) y dos réplicas podían migrar en paralelo | El job `migrate` hace ambos una vez; `api`/`celery` con `RUN_*=0` |
| **P2** | `docker image prune -f` solo borraba *dangling*: los tags `sha-<commit>` llenaban el disco del VPS | `prune --filter until=168h` |

### 15.2 Checklist de secretos — OBLIGATORIO antes del próximo deploy

> **Regla:** los valores **nunca** se commitean, ni en `.env.example`, ni en
> `render.yaml`, ni en este documento. Acá va solo el nombre y el propósito.
> El deploy **falla a propósito** (preflight fail-closed) si faltan.

#### A. GitHub → Settings → **Environments → `production`** (no en repo-level)

El job `deploy` usa `environment: production`: cargarlos ahí permite exigir
aprobación manual y que no estén disponibles para cualquier workflow del repo.

- [ ] `SSH_HOST_FINGERPRINT` — host key del VPS pineada. Sin esto `appleboy/ssh-action`
      no verifica contra quién habla (MITM sobre el canal del deploy).
      Obtener con: `ssh-keyscan -p <SSH_PORT> <SSH_HOST> | ssh-keygen -lf -`
- [ ] `MP_WEBHOOK_SECRET` — clave secreta del panel de Mercado Pago
      (*Webhooks → Clave secreta*). Firma HMAC-SHA256 de los webhooks.
      **Vacío = todos los pagos entrantes se rechazan con 401** (fail-closed) y
      `payments.E001` rompe `check --deploy`. El preflight exige ≥32 chars.
- [ ] `SECRET_MP_KEY` — access token de producción de Mercado Pago.
      Sin él, `checkout`/`subscription` no pueden crear la preferencia.
      El preflight exige ≥16 chars.

Ya existentes (no cambian): `SSH_HOST`, `SSH_PORT`, `SSH_USERNAME`,
`SSH_PRIVATE_KEY` · Variable: `PLATFORM_DOMAIN`.

#### B. Render → Dashboard → *Environment* (Blueprint `render.yaml`, `sync: false`)

Render no recibe secretos por el pipeline: se cargan una vez en el dashboard
y el Blueprint **no** los pisa (`sync: false`).

- [ ] `MP_WEBHOOK_SECRET`
- [ ] `SECRET_MP_KEY`
- [ ] `SECRETS_MASTER_KEYS` y `SECRETS_HASH_KEY` (misma advertencia que §C: sin
      keyring, la PII se cifra con la llave derivada y queda ilegible al definirlo)
- [ ] (ya existentes, para referencia) `SECRET_KEY`, `DATABASE_URL` de Neon,
      `EMAIL_HOST_PASSWORD`, claves R2, `GOOGLE_CLIENT_ID`

#### C. VPS `/opt/davent/.env`

El deploy escribe `MP_WEBHOOK_SECRET` y `SECRET_MP_KEY` con un **merge atómico**
(`mktemp` + `mv`, `umask 077`, `chmod 600`) y borra el archivo temporal con
`shred`. El resto del `.env` se respeta byte a byte — no lo sobrescribe.

- [ ] **`SECRETS_MASTER_KEYS`** — keyring AES-256-GCM de la PII (`kid:b64url32`).
      **OBLIGATORIO antes del primer deploy con `users/migrations/0010`.** Sin
      él el contenedor arranca cifrando `document`/`phone`/nombres/domicilio con
      la llave derivada del `SECRET_KEY` (`kid "self"`); al definir el keyring
      real, `_keyring()` deja de exponer `self` y **esas filas quedan ilegibles**
      (`VaultError` en cada lectura). No es "acoplado al SECRET_KEY": es pérdida
      de datos. Generar: `manage.py encrypt_secret --gen-master-key k1`.
- [ ] **`SECRETS_HASH_KEY`** — llave HMAC de `document_hash`/`phone_hash`.
      Distinta de la keyring. **No rotarla en caliente**: las huellas ya
      emitidas dependen de ella (se rompe la unicidad/búsqueda).
- [ ] El preflight del deploy (`.github/workflows/ci-cd.yml`, paso 2) corta si
      cualquiera de las dos falta o es demasiado corta.
- [ ] Verificar que `.env` exista y sea `600`: `ls -l /opt/davent/.env`
- [ ] `SECRET_KEY` ≥32 chars (ideal 50+, si no Django marca `security.W009`)

#### D. Verificación post-carga (antes de mergear el próximo deploy)

```bash
# 1. Preflight local contra el .env del VPS
grep -c '^MP_WEBHOOK_SECRET=.\{32,\}' /opt/davent/.env   # -> 1
grep -c '^SECRET_MP_KEY=.\{16,\}'     /opt/davent/.env   # -> 1

# 2. El check de Django en el contenedor (debe salir 0)
docker compose exec api python manage.py check --deploy

# 3. Webhook firmado de punta a punta (sandbox de MP) -> 200 en el log
docker compose logs -f api | grep -i 'webhook'
```

**Rotación:** cambiar el valor en GitHub/Render → el próximo deploy lo escribe
en el `.env` del VPS. No hace falta tocar el servidor a mano.

### 15.3 Blindaje del contenedor `web` (nginx sin privilegios)

`read_only: true` + `tmpfs` es **obligatorio** para `nginx-unprivileged`: el
rootfs es inmutable y nginx solo escribe en los tmpfs declarados.

```yaml
  web:
    ports:
      - "80:8080"      # host 80 -> nginx 8080 (uid 101, sin root)
      - "443:8443"
    security_opt: ["no-new-privileges:true"]
    cap_drop: [ALL]    # ya no hay cap_add: NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp                  # pid file (nginx.conf de la imagen: /tmp/nginx.pid)
      - /var/cache/nginx      # client_body_temp / proxy_temp
      - /etc/nginx/conf.d     # envsubst escribe el vhost renderizado al arrancar
```

`docker compose up -d --wait --wait-timeout 180` (paso 4 del deploy) es el
preflight: si nginx no puede escribir en algún tmpfs, el healthcheck nunca
pasa y **el job falla** en vez de dejar el sitio caído con un deploy verde.

### 15.4 Patrón: aislamiento de cache en tests (falso positivo de SQLite)

`plan_benefits_of` cachea por PK (`planben:<pk>`) y el throttle de DRF keyea
por `scope + user.pk`. SQLite **reutiliza PKs** después del rollback de cada
`TestCase`, así que el cache del test anterior se filtra al siguiente:

- gate de plan → `201` en vez de `403` (el plan cacheado de otro test);
- `coupon_redeem` 10/h → `429` a mitad de la clase (contador acumulado);
- dedupe de visitas `hash(IP+UA+fecha)` → la segunda visita se descarta.

**Regla:** toda clase de test que dependa de beneficios, throttles o del
dedupe de visitas debe empezar con `cache.clear()` en `setUp()`. Postgres no
lo necesita (las secuencias no retroceden), pero el aislamiento no debe
depender del motor: el test tiene que pasar igual en SQLite.

**Verificación ejecutada:** `manage.py test` → **369 tests OK, 0 fallos**
(antes: 10 fallos + 1 error, idénticos en `HEAD`), `manage.py check --deploy`
exit 0, `ruff check` limpio, `docker compose config -q` OK.

## 16. Pasada de parches + auditoría de pipeline — 2026-10-28

Pasada de mantenimiento: traer las dependencias al último parche con
advisories públicas, verificar que la cadena `lint -> test -> security ->
build -> deploy` esté realmente verde (no solo escrita) y re-ejecutar la
auditoría con las herramientas que corren en CI.

**Ejecutado:** `manage.py test` → **498 tests OK** · `manage.py check --deploy`
→ 0 issues (solo warnings env-driven del `.env` de dev) · `ruff 0.17.3` →
limpio · `bandit 1.9.4 -ll` → **0 hallazgos** · `pip-audit 2.10.1 -r
requirements.txt` → **0 CVEs** · `npm audit --omit=dev` → **0 vulnerabilities**.

### 16.1 Parches de dependencias aplicados

| Paquete | Antes | Ahora | Motivo |
|---------|-------|-------|--------|
| **Django** | 5.2.17 | **5.2.18** | Release de seguridad 2026-10-06: **CVE-2026-84429** (DoS cuadrático en `parse_header_parameters`, alcanzable sin autenticar vía `Accept`/`Content-Type` — **aplica**: DRF negocia contenido en cada request), **CVE-2026-87975** (abuso de privilegios en formsets con PK editable — **no aplica**: todo el schema usa `BigAutoField` y no hay inlines de admin), **CVE-2026-87890** (SSRF en spatial lookups — **no aplica**: sin GIS), **CVE-2026-77050** (DoS en `get_supported_language_variant`, severidad baja) + fix de la mitigación insuficiente de 5.2.17 (CVE-2026-15830, bypass del límite de profundidad de geometrías) |
| **djangorestframework** | 3.18.2 | **3.18.3** | Revert de un cambio de API introducido por error en 3.18.2. Los fixes de seguridad (GHSA-33wh-fxxf-88vv content negotiation, GHSA-3547-9m27-7rxg charsets no-text, GHSA-xw6w-gcfp-cf8m `TokenProxy`) ya estaban en 3.18.2 |
| **PyJWT** | 2.15.0 | **2.15.1** | Patch del validador de claims (lo usa simplejwt en cada request autenticado) |
| **psycopg2-binary** | 2.9.12 | **2.9.13** | Patch del driver |

**Diferidos a propósito** (publicados hace <7 días, sin advisory: no se adopta
un release sin ventana de maduración): `boto3` 1.43.120 (2026-10-27),
`onnxruntime` 1.31.1 (2026-10-26). Django **5.2.19** figura en la doc como
release del 2026-11-03 pero **no está publicado en PyPI** todavía: 5.2.18 es
el último parche instalable hoy.

### 16.2 Superficie de dependencias reducida

`cloudinary`, `coreapi`, `openapi-codec`, `coreschema` e `itypes` estaban
pinneados en `requirements.txt` sin ningún import en el código (Cloudinary se
abandonó por R2; el schema lo genera `drf-spectacular`). Se eliminaron: menos
paquetes que auditar en cada build y ninguna credencial huérfana que alguien
pueda reactivar por error. `inflection`/`uritemplate` se conservan (los exige
`drf-spectacular`).

### 16.3 Pipeline — estaba en rojo, no solo "mal configurada"

| Sev. | Hallazgo | Evidencia | Remediación |
|------|----------|-----------|-------------|
| **P0** | `gitleaks/gitleaks-action@v2` corre sobre **Node 20**, retirado de los runners de GitHub el **2026-09-16**: el paso no arranca, el job `security` falla y con él `build` (`needs: [lint, test, security]`) y `deploy` → **ningún push llega al VPS** | `action.yml` de v2: `using: node20`; release v3 documenta el corte de Node 20 | `@v3` (mismos inputs/salidas, runtime node24) |
| **P0** | `bandit -ll` **fallaba** con el pin actual (1.8.3): 8 hallazgos ≥ media (1 HIGH B324 + 7 MEDIUM B608). Mismo resultado con 1.9.4 | `bandit -r ... -ll` → `High: 1, Medium: 7` | Ver 16.4: `usedforsecurity=False` en el MD5 de cache + `# nosec B608` justificado en los 7 SQL de `_meta` (valores parametrizados). Ahora `High: 0, Medium: 0` |
| **P1** | `concurrency` del workflow con `cancel-in-progress: true` **cancela el run entero** — incluido el job `deploy` a mitad de camino. El `concurrency` a nivel de job (fix de §15) serializa deploys pero no protege de la cancelación del workflow padre | `gh` run cancelado entre `compose pull` y `up -d` = migraciones nuevas con contenedores viejos | `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`: los PRs siguen cancelando, `main` nunca |
| **P2** | Herramientas de CI pinneadas viejas (`ruff 0.8.6`, `bandit 1.8.3`, `pip-audit 2.9.0`) — el SAST corría con reglas de hace ~1 año | — | `ruff 0.17.3`, `bandit 1.9.4`, `pip-audit 2.10.1` (verificados localmente antes de subir el pin) |
| **P2** | `appleboy/scp-action@v0.1.7` (acción **docker**, sin mantenimiento) y `ssh-action@v1.2.0` | — | `scp-action@v1.0.0` (composite; mismos inputs `host/port/username/key/fingerprint/source/target/overwrite`) y `ssh-action@v1.2.5` |
| **P2** | `ruff 0.17.3` destapó 6 errores que el pin viejo dejaba pasar: `F841` en `stores/tests.py` y `F401` en 4 scripts `qa_*.py` | `ruff check` → 6 errors | Imports muertos eliminados; `ruff check` limpio |

### 16.4 Fixes de código

- **B324 (HIGH) — `hashlib.md5` sin `usedforsecurity=False`**
  (`StoreApp/domains/stores/views/viewset.py:200`). El MD5 no es
  criptográfico: firma la querystring canónica como key del cache del catálogo
  público. Se declara la intención explícita (Python ≥3.9) en vez de bajar la
  severidad en CI: si mañana alguien usa MD5 para algo de seguridad, bandit
  vuelve a marcarlo.
- **B608 (MEDIUM ×7) — SQL con f-string** en
  `users/management/commands/rotate_encrypted_fields.py`,
  `users/migrations/0010_encrypt_pii_fields.py` y un helper de `users/tests.py`.
  Falso positivo estructural: la tabla y las columnas salen de
  `UserProfile._meta` (constantes del modelo) y **todos los valores** viajan
  como parámetros (`%s`). Se anotó `# nosec B608` con el motivo en cada sitio
  en vez de silenciar la regla para todo el repo (un `-s B608` global taparía
  una inyección real futura).

### 16.5 Verificado como correcto (sin cambio)

- Cadena de gates: `build` exige `lint + test + security`; `deploy` exige
  `build + security`, corre en `environment: production`, serializado, con
  host key pineada, preflight fail-closed de secretos, `up -d --wait` y
  `curl /healthz/` externo. El `test` lleva los dummies de CI
  (`MP_WEBHOOK_SECRET`, `SECRETS_MASTER_KEYS`, `SECRETS_HASH_KEY`, `ADMIN_URL`)
  que evitan que `payments.E001`/`users.E002-E003` tumben el job.
- Endurecimiento de contenedores de §15 sigue en pie: nginx-unprivileged
  (uid 101, 8080/8443) con `read_only` + tmpfs, `cap_drop: [ALL]`,
  `no-new-privileges`, Redis con `maxmemory 256mb`/`volatile-lru` bajo cgroup
  384M, `.dockerignore` excluyendo `docker/certbot/`, `*.pem`, `*.key`.
- `keepalive.yml` (ping a Render) sin secretos ni permisos elevados.

### 16.6 Residuales honestos

- **El pipeline verde no se puede confirmar desde el repo**: los jobs se
  verificaron ejecutando localmente cada herramienta con el pin nuevo, pero la
  prueba real es el primer push a `main` (Actions → CI/CD).
- **Secretos de despliegue** (checklist §15.2) siguen siendo el riesgo #1
  residual: no son verificables desde el código.
- `SECURITY_SIMULATION_REPORT.md` (§5, recomendación 3) todavía describe la
  verificación por SMS de Firebase, retirada en §13: documento histórico, no
  se reescribe.

### 16.7 Dependencias diferidas — cuándo se pueden adoptar

Regla de adopción: **7 días** desde la fecha de publicación en el índice
(pip/npm) y sin advisory nuevo en ese lapso. No es una fecha de calendario
rígida: si aparece un CVE que aplique, se adelanta.

| Paquete | Publicado | Adoptable desde | Estado hoy (2026-10-28) |
|---------|-----------|-----------------|--------------------------|
| `boto3` 1.43.120 | 2026-10-27 | **2026-11-03** | Pin actual `1.43.116`; sin CVE que lo fuerce |
| `onnxruntime` 1.31.1 | 2026-10-26 | **2026-11-02** | Pin actual `1.31.0`; solo lo usa `remove_background` |
| Django **5.2.19** | doc dice 2026-11-03; **no está en PyPI** | **2026-11-10** (publicación + 7d) | `5.2.18` es el último instalable; `pip-audit` no marca nada |

Cómo verificar antes de subir el pin (mismo comando que CI):

```bash
venv/Scripts/python.exe -m pip index versions Django        # ¿existe 5.2.19?
venv/Scripts/python.exe -m pip install "Django==5.2.19" && venv/Scripts/python.exe manage.py test
venv/Scripts/python.exe -m pip_audit -r requirements.txt
```

`boto3`/`onnxruntime` no los actualiza Dependabot a ciegas: el cooldown de
`.github/dependabot.yml` (7 días) respeta la misma ventana.


---

## §17 Cierre de riesgos residuales (ronda 2026-10-28)

Alcance: los ítems que §16 dejó abiertos (P0 de despliegue, P1 de código y de
cadena de suministro, validación externa). Cada fila trae el comando que la
prueba; lo que no se pudo ejecutar desde el repo se marca como tal.

### 17.1 Hallazgos cerrados

| # | Hallazgo | Sev. | Fix aplicado | Verificación ejecutada |
|---|----------|------|--------------|------------------------|
| 1 | Cabeceras de transporte dependían de que el `.env` no las apagara: `SECURE_SSL_REDIRECT=False` pasaba `check --deploy` sin ruido | **P0** | `DaventProject/checks.py`: `project.E001-E005` fallan `check --deploy` con `DEBUG=False` si `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS>0` o `SECURE_PROXY_SSL_HEADER` quedaron apagados. Registrado desde `UsersAppConfig.ready()` | `manage.py test AdminApp.domains.users.tests.ProductionTransportChecksTests` (6 tests, OK) · `manage.py check --deploy` en dev: sin errores nuevos |
| 2 | Adjunto del chat podía salir por la **URL pública** del bucket (si `R2_PUBLIC_URL` está configurada) — link permanente para cualquiera que lo tenga | **P1** | `storage.object_url(key, private=True, expires=...)` ignora la base pública; `chat_image_url` firma con TTL de **1 h** (`CHAT_IMAGE_TTL_SECONDS`). El archivo sigue validado por el pipeline auditado de stores (firma real de bytes, 4 MB antes de leer, `MAX_IMAGE_PIXELS=40M` → `DecompressionBombError`, recodificación a WebP sin EXIF) | `manage.py test StoreApp.domains.stores.tests.ObjectUrlPrivacyTests` · `AdminApp.domains.chat` (suite completa) |
| 3 | Cobros `approved` de MP sin fila local (residual W-5) invisibles | **P1** | `manage.py audit_orphan_payments [--days N] [--include-test] [--json]`: pagina `payment.search(status=approved)`, cruza `Payment.external_reference` (id de pago MP) y `external_reference` (id de suscripción), lista monto/moneda/fecha/motivo y **loguea** — no crea `Payment` ni acredita nada | `manage.py test AdminApp.domains.payments.tests.AuditOrphanPaymentsTests` (2 tests: no escribe, filtra sandbox) |
| 4 | `review.email` y chat viejo se conservaban indefinidamente (Ley 25.326) | **P1** | `manage.py purge_personal_data --days N [--dry-run]`: anonimiza `ProductReview.email` y borra `ChatMessage` + adjunto (R2/MEDIA) anteriores al corte. No toca `Payment`/`Suscription`/`Invoice` por diseño | `manage.py test AdminApp.domains.users.test_retention` (dry-run, purga real con borrado de adjunto, idempotencia) |
| 5 | CVEs nuevas solo se veían cuando alguien pusheaba | **P1** | `.github/workflows/security-schedule.yml` (lunes 06:00 UTC + `workflow_dispatch`): pip-audit, npm audit `--omit=dev`, trivy fs con los mismos pins que CI | YAML revisado; se valida en el primer run programado (Actions → Security schedule) |
| 6 | Actualizaciones de dependencias sin ventana de maduración | **P2** | `.github/dependabot.yml`: pip/npm/github-actions/docker, `cooldown.default-days: 7`, parches agrupados. El cooldown **no** aplica a security updates | Config revisada contra el esquema de Dependabot (Insights → Dependency graph) |
| 7 | Fechas de adopción de los pins diferidos no estaban fijadas | **P2** | §16.7: `boto3` 1.43.120 → 2026-11-03, `onnxruntime` 1.31.1 → 2026-11-02, Django 5.2.19 → 2026-11-10 (publicación + 7 d) | Comandos de verificación listados en §16.7 |
| 8 | DAST y rotación de secretos sin procedimiento escrito | **P2** | `SECURITY_RUNBOOK.md`: ZAP baseline contra staging, tokens de prueba por área, rotación keyring → `SECRET_KEY` → MP con el orden que evita perder PII | Documento operativo (no ejecutable desde el repo) |

### 17.2 Checklist de secretos — comando por secreto

Marcado **verificable desde el repo** (V) o **solo en el panel** (P).

| Secreto | Dónde | Comando / cómo verificar | Quién |
|---------|-------|--------------------------|-------|
| `MP_WEBHOOK_SECRET` (≥32) | GitHub Env `production`, Render, VPS | `grep -c '^MP_WEBHOOK_SECRET=.\{32,\}' /opt/davent/.env` → `1`; en Render: Dashboard → Environment (valor enmascarado, solo se ve si se edita) | P |
| `SECRET_MP_KEY` (≥16) | ídem | `grep -c '^SECRET_MP_KEY=.\{16,\}' /opt/davent/.env` → `1`; prueba real: `manage.py audit_orphan_payments --days 1` responde 200 (si el token es inválido, MP devuelve 401 y el comando lo reporta) | P |
| `SECRETS_MASTER_KEYS` | VPS `/opt/davent/.env`, Render | `docker compose exec api python manage.py check --deploy` → 0 errores (`users.E002/E003`); `docker compose exec api python manage.py shell -c "from AdminApp.domains.invoices.services import vault; print(vault.active_kid())"` | P |
| `SECRETS_HASH_KEY` | ídem | mismo `check --deploy`; no tiene verificación de valor (es HMAC de unicidad) — se valida indirectamente con el alta de un perfil duplicado | P |
| `SSH_HOST_FINGERPRINT` | GitHub Env `production` | `ssh-keyscan -p $SSH_PORT $SSH_HOST \| ssh-keygen -lf -` y comparar con el secret | P |
| `SECRET_KEY` (≥50) | VPS, Render | `docker compose exec api python -c "from django.conf import settings; print(len(settings.SECRET_KEY))"` → `>=50`; Django lo marca como `security.W009` si no | P (V solo el largo, no el valor) |
| Preflight completo | GitHub | `gh run view --log --job deploy \| grep -i preflight` (o Actions → CI/CD → job `deploy` → paso *Preflight*) | P |

### 17.3 Estado del primer run de CI del commit `1a78b03`

**No verificable desde este entorno**: no hay `gh` instalado ni credenciales de
Actions. Qué mirar (Actions → *CI/CD* → run de `1a78b03`):

1. `lint` — `ruff check` limpio.
2. `test` — `check --deploy`, `makemigrations --check`, `manage.py test` (los
   dummies de CI cubren `MP_WEBHOOK_SECRET`/`SECRETS_*`).
3. `security` — bandit, pip-audit, npm audit, gitleaks, trivy fs.
4. `build` — dos imágenes a GHCR + trivy image.
5. `deploy` — preflight de secretos, scp, ssh, `up -d --wait`, `curl /healthz/`.

Si algo falla, pegar acá la salida del paso rojo:
`Actions → run → job → paso → "Download log"` (o `gh run view <id> --log-failed`).

> Nota: los commits de esta ronda (`7d607f4`, `7cfc491`, `a478ea6`) disparan
> runs nuevos; el criterio es que el **último** run de `main` quede verde.

### 17.4 Residuales honestos (lo que sigue abierto)

| Residual | Por qué queda abierto | Mitigación actual |
|----------|----------------------|-------------------|
| Sin antivirus/escaneo de adjuntos | El pipeline solo garantiza que es una imagen decodificable (Pillow), no que sea benigna. Un polyglot/esteganografía pasa | Recodificación a WebP (destruye el archivo original y cualquier payload embebido en el contenedor), tamaño ≤4 MB, 40 MP, servido con `Content-Type: image/webp`, URL firmada de 1 h. No se ejecuta ni se sirve como HTML |
| URL firmada es bearer | Quien la tenga la usa durante 1 h | TTL corto + key UUID no adivinable + solo se emite a los dos participantes del hilo. Firma por usuario requeriría proxy de media propio (fuera de alcance) |
| Media local en VPS sin R2 | Si `R2_*` no está configurado, nginx sirve `/media/chat/...` como público (key UUID) | Documentado; en producción el bucket está configurado. Si se corre sin R2, tratar `/media/` como no público |
| `audit_orphan_payments` es solo lectura | Acreditar automáticamente un huérfano puede duplicar un cobro legítimo | Lista + log para reconciliación manual en el panel de MP (decisión de producto, no técnica) |
| Retención por defecto 365 d | No hay cron que lo ejecute | Comando idempotente listo; falta agendarlo (cron del VPS o Celery beat) — acción de despliegue |
| `SECRETS_HASH_KEY` sin rotación | Rotarla rompe `document_hash`/`phone_hash` ya emitidos | Documentado como no rotable en caliente (runbook §3.3) |
| DAST no ejecutado | Requiere staging accesible y ventana | Runbook listo (§1-§2); ejecución pendiente del operador |
| Primer run de CI | Sin acceso a Actions desde el entorno del agente | §17.3 |

### 17.5 Ejecución completa de verificación (2026-10-28, local)

| Comando | Resultado |
|---------|-----------|
| `manage.py test` (suite completa) | **509 tests, OK** (238 s) |
| `manage.py test AdminApp.domains.users.test_headers` | 3 OK — CSP + `nosniff` + `X-Frame-Options` + `Referrer-Policy` en HTML de Django; JSON sin CSP; CSP previa no se pisa |
| `manage.py test AdminApp.domains.chat.tests.ChatAttachmentTests` | 7 OK — incluye >4 MB, `content_type` mentiroso y PNG truncado con firma válida |
| `ruff check .` | limpio |
| `bandit -r ... -ll` | 0 HIGH / 0 MEDIUM (38 low) |
| `pip-audit -r requirements.txt` | 0 vulnerabilidades |
| `npm audit --omit=dev --audit-level=high` | 0 vulnerabilidades |
| `DEBUG=False manage.py check --deploy` | 0 errores de código. Solo `payments.E001` y `users.E002` por secretos ausentes en el `.env` **local** (en producción los exige el preflight) + `security.W009` (SECRET_KEY de dev) y `security.W021` (HSTS preload, decisión de dominio) |

No ejecutables en este entorno: `trivy` (binario ausente y daemon de Docker
apagado) y `gitleaks` (no instalado) — ambos corren en CI y en
`security-schedule.yml`. El DAST sigue pendiente de staging (§17.4).
