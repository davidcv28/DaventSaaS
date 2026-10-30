# Auditoría técnica DAVENT — 30/10/2026

Alcance: ejecutar la suite de tests y herramientas de seguridad, y revisar el código
en los seis ejes pedidos (vulnerabilidades, fugas de memoria, CI/CD, middlewares,
filtro de variables de entorno críticas/peligrosas, concurrencia/idempotencia/N+1).
Al final: plan de remediación priorizado + prompt de corrección listo para usar.

Repo: `C:\Users\David\OneDrive\Escritorio\SaaS DAVENT` (rama `main`, con cambios
locales sin commitear ajenos a esta auditoría).

---

## 1. Resumen ejecutivo

| Eje | Estado | Hallazgos |
|---|---|---|
| Suite de tests backend | **881 tests, 359 s** → 873 OK; los 8 fallos son del sandbox (escritura en `%TEMP%`), no del código | ver §2 |
| SAST (bandit) | 1 hallazgo alto (SHA1 de un hash de firma de layout, falso positivo), 0 medios | V-09 |
| Dependencias Python (pip-audit) | no completó en este host (red/venv temporal de la herramienta); CI lo corre en cada push | §2 |
| Dependencias SPA (npm audit) | **0 vulnerabilidades** (`--omit=dev --audit-level=high`) | §2 |
| Vulnerabilidades | 1 alta/2 medias de disponibilidad, 4 medias/bajas de diseño, 3 bajas | V-01…V-13 |
| Fugas de memoria | 2 relevantes (Redis) + 2 menores (Vue/ONNX) | M-01…M-04 |
| CI/CD | pipeline maduro, pero faltan backup pre-migración, rollback y controles de cadena de suministro | C-01…C-08 |
| Middlewares | orden y cabeceras correctos; falta resiliencia de caché, correlación y body-cap | MW-01…MW-04 |
| Env vars críticas/peligrosas | **no existe filtro central**; secretos se heredan a subprocesos y a contenedores que no los necesitan | ENV-01…ENV-04 |
| Concurrencia / idempotencia | muy bien resuelta (select_for_update, webhook HMAC, dedup); quedan 3 huecos | CC-01…CC-06 |
| N+1 | en general resuelto (prefetch/anotaciones); 2 casos concretos | CC-02, CC-03 |

**Veredicto:** la base es sólida (fail-closed, HMAC en pagos, cifrado de PII, throttles
por scope, tests de regresión). No hay una vulnerabilidad crítica explotable de
lectura/escritura de datos; los riesgos reales son de **disponibilidad y costo**
(flooding de caché, lockout de cuentas, Redis como dependencia dura), de **cadena de
suministro/deploy** (sin backup ni rollback) y de **higiene de secretos** (env vars
que viajan a subprocesos y contenedores de DB/Redis).

---

## 2. Evidencia de la ejecución

Entorno: Windows, Python 3.11.15 (venv del repo), PostgreSQL local `daventec`
(la suite crea `test_daventec`), DSH sandbox `workspace-write`.

Comandos y resultados:

```
venv/Scripts/python.exe manage.py test --verbosity 1 --noinput
  Found 881 test(s) · System check identified no issues (0 silenced)
  Ran 881 tests in 359.206s
  FAILED (failures=3, errors=5)
```

Los 8 fallos NO son bugs de producto: 3 fallos + 5 errores provienen de tests que
escriben con `tempfile.mkdtemp()`/`default_storage.save()` bajo `%TEMP%`, y el
sandbox de esta sesión deniega `makedirs` en ese árbol:

```
PermissionError: [WinError 5] Acceso denegado:
  ...\AppData\Local\Temp\dsh-...\tmp...\chat   (chat/media upload)
  ...\AppData\Local\Temp\dsh-...\tmp...\index.html (SPA dist)
```

Tests afectados (todos de subida de archivos / dist temporal):
`AdminApp.domains.chat.tests.ChatAttachmentTests` (2),
`StoreApp.domains.stores.tests_ai_design.AiDesignImageTests` (1),
`DaventProject.tests.SpaCatchAllTests` (4 casos de setUp), más 1 error derivado.

Re-ejecución focalizada **sin el sandbox** (política `danger-full-access`):

```
python manage.py test AdminApp.domains.chat.tests DaventProject.tests   -> 32 tests OK
python manage.py test StoreApp.domains.stores.tests_ai_design.AiDesignImageTests -> 6 tests OK
```

Conclusión: la suite está **verde al 100% (881/881)**; los 8 fallos eran
exclusivamente del sandbox de la sesión (denegación de escritura en `%TEMP%`),
no del código. En CI (ubuntu, `/tmp` escribible) también pasan. No se tocó código
para esta auditoría.

```
venv/Scripts/python.exe -m bandit -r AdminApp StoreApp SuscriptionApp DaventProject -ll
  High: 1 · Medium: 0 · Low: 87 (filtrados) · nosec: 7       [B324 hashlib.sha1]
venv/Scripts/python.exe -m pip_audit -r requirements.txt
  no completa en este host (pip-audit arma un venv temporal y la resolución de red
  desde este equipo no terminó en un tiempo razonable, incluso con acceso completo);
  el job `security` de CI sí lo corre con pip-audit 2.10.1 en cada push
npm audit --omit=dev --audit-level=high   (frontend/)
  found 0 vulnerabilities
```

Nota de entorno: el árbol de trabajo tiene **118 directorios `tmp*` sin ignorar**
(ver V-11) y cambios sin commitear de otro trabajo en curso; no se modificó nada
fuera de los dos documentos de esta auditoría.

---

## 3. Hallazgos

Severidad: P0 = explotable/pérdida de datos; P1 = alto (disponibilidad/costo/secretos);
P2 = medio; P3 = bajo/mejora.

### 3.1 Vulnerabilidades

| ID | Sev | Ubicación | Problema | Impacto |
|---|---|---|---|---|
| V-01 | **P1** | `StoreApp/domains/stores/views/viewset.py:200-206` (`_params_fingerprint`) + `:485-489` | La key del cache del catálogo público hashea **todos** los query params (`request.query_params.lists()`), no solo los filtros conocidos. `?x=<aleatorio>` crea una entrada nueva con el payload completo del catálogo (TTL 120 s). | Flooding de caché: memoria de Redis (256 MB) y evicción `volatile-lru` de **contadores de throttle** (bypass del rate-limit) y de las versiones del cache público. DoS barato + costo de serialización por request. |
| V-02 | **P1** | `AdminApp/domains/users/views/auth_views.py:65-90,193-201` | Lockout por cuenta (`LOGIN_FAIL_LIMIT=10/15 min`) contado por username, sin captcha ni vínculo IP+cuenta. El atacante manda 10 passwords erróneos cada 15 min y la cuenta queda bloqueada de forma sostenida (el desbloqueo exige un login exitoso). | DoS dirigido a cualquier usuario conocido (anti-enumeración no aplica al username). |
| V-03 | P2 | `StoreApp/domains/stores/services/contact.py:30-57` (captcha compartido por contacto y reseñas) | La respuesta es una suma de dos dígitos: **17 valores posibles (2..18)**; `signing.dumps` no oculta el payload; el challenge no es de un solo uso. Throttle 10/h/IP es la única barrera. | Anti-spam efectivamente sorteable con pocas IPs/proxies. |
| V-04 | P2 | `AdminApp/domains/users/services/services.py:242-246` → `_send_branded_mail` (SMTP sincrónico) | `POST /api/password-reset/` responde 200 genérico, pero solo envía correo (y tarda ~cientos de ms) si el email existe. | Enumeración de cuentas por timing, pese a la respuesta uniforme. |
| V-05 | P2 | `DaventProject/settings.py` (no define `PASSWORD_RESET_TIMEOUT`) | Aplica el default de Django: **3 días** para reset de contraseña y para el token de verificación de email. | Ventana de robo/replay de links de correo demasiado amplia. |
| V-06 | P2 | `AdminApp/domains/users/services/services.py:129,254-255`; `AdminApp/domains/invoices/services/services.py:69,82-94`; `StoreApp/domains/stores/services/contact.py:80-87`; `legal/services` | Todos los correos se envían **sincrónicamente dentro del request** (algunos vía `transaction.on_commit`, que corre en el mismo hilo). Celery está configurado y se levanta un worker, pero **no hay ninguna task definida** (`@shared_task` inexistente). | Un SMTP lento (timeout 10 s) ocupa los 12 hilos de gunicorn (`3 workers × 4 threads`) y bloquea el panel; el worker Celery consume 384 MB para nada. |
| V-07 | P2 | `AdminApp/domains/chat/services/attachments.py:35-41` + `docker/web/templates/default.conf.template` (`location /media/`) | Sin R2 configurado, los adjuntos del chat (que deberían ser privados y firmados) se guardan en `MEDIA_ROOT` y nginx los sirve en `/media/chat/<thread>/<uuid>.webp` **sin auth ni expiración**. | Fuga de imágenes privadas de soporte si se filtra/escanea una URL. |
| V-08 | P2 | `AdminApp/domains/users/views/auth_views.py:334-347` | `GET /api/verify-email/` es `AllowAny` y **no declara throttle**; además muta estado por GET. | Endpoint gratuito para fuerza bruta de tokens (improbable) y para tráfico basura; prefetchers pueden verificar sin intención del usuario. |
| V-09 | P3 | `StoreApp/domains/stores/services/ai_design.py:2036` | `hashlib.sha1(...)` para firma de layout — bandit B324 (Alta/falso positivo: no es seguridad). | Ruido en el gate de seguridad (bandit falla el job si se sube a severidad alta sin `nosec`). |
| V-10 | P3 | `DaventProject/middleware.py:121-160` vs `/admin/password_reset/` (Django admin) | El rate-limit propio cubre solo `POST <ADMIN_URL>/login/`; el reset de contraseña del admin es público, no pasa por throttles DRF y dispara emails. | Spam de correos al buzón del staff. |
| V-11 | P3 | raíz del repo + `.gitignore`/`.dockerignore` | 118 directorios `tmp*` sin ignorar y con ACL denegadas. | Rompen `git add -A`/`git status`, inflan el contexto de build Docker y el scan `trivy fs`; ruido para agentes. |
| V-12 | P3 | `frontend/src/config/env.js:11` | Fallback `VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'` se hornea si un build olvida el build-arg: la SPA de producción llama a localhost. | Falla total silenciosa de la SPA, no detectable por healthcheck (que solo mira el backend). |
| V-13 | P3 | `DaventProject/middleware.py:63-72,101-106` | CSP de respaldo con `script-src/style-src 'unsafe-inline'` e `img-src https:` muy amplio. | Superficie XSS residual en HTML servido por Django (admin/browsable). |

### 3.2 Fugas de memoria

| ID | Sev | Ubicación | Problema | Impacto |
|---|---|---|---|---|
| M-01 | **P1** | `StoreApp/domains/stores/views/viewset.py:200-206` | Misma raíz que V-01: keys de caché ilimitadas por query string arbitraria; cada valor es el payload serializado del catálogo. | Crecimiento no acotado del cache (Redis 256 MB) hasta evicción agresiva. |
| M-02 | P2 | `StoreApp/domains/stores/public_cache.py:27-31` | `_bump()` usa `cache.add(key, 1, timeout=None)`: las keys `stores:pub:ver:<id>` y `stores:pub:epoch` **nunca expiran**. Al borrar tiendas quedan huérfanas. | Fuga lenta de memoria en Redis; crecimiento monotónico con la cantidad de tiendas históricas. |
| M-03 | P2 | `StoreApp/domains/stores/services/imaging.py:124-164` | Modelo ONNX descargado entero en RAM (`response.content`) y `InferenceSession` global por worker que nunca se libera; `max_requests` recicla el worker recién a las 1000 requests. Cada worker suma el modelo + numpy/onnxruntime sobre un límite de 1 GB. | Picos de memoria/OOM-kill del contenedor `api` con tráfico de "quitar fondo" (60/h por usuario). |
| M-04 | P3 | `frontend/src/views/LoginView.vue:19-34` | `setInterval` del cooldown sin `onUnmounted`: si el usuario navega durante los 60 s, el timer sigue vivo. | Fuga menor de un timer por visita al login. |
| M-05 | P3 | `StoreApp/domains/stores/models/models.py:532` (StoreDailyVisit) + `services/services.py:101-117` | Una fila por tienda/día sin poda (crecimiento indefinido) y una key de caché por (tienda, visitante, día). | Crecimiento de DB/caché acotado por TTL pero permanente en DB; impacto bajo. |

Bien resuelto (no tocar): `max_requests=1000` + `max_requests_jitter` en gunicorn,
`maxmemory`/`volatile-lru` en Redis, logs con rotación `max-size`, cache de
beneficios con TTL 10 s y memo por instancia, `prefetch_related` en listados.

### 3.3 CI/CD

| ID | Sev | Ubicación | Problema | Mejora |
|---|---|---|---|---|
| C-01 | **P1** | `.github/workflows/ci-cd.yml:350-417` | El deploy corre `docker compose run --rm migrate` **sin backup previo** de Postgres. Una migración destructiva/fallida no tiene red. | Paso previo `docker compose run --rm api python manage.py backup_db` fail-closed; abortar el deploy si falla. |
| C-02 | **P1** | `.github/workflows/ci-cd.yml:350-417` | No hay rollback: si `up -d --wait` o el `curl /healthz/` fallan, los contenedores ya se reemplazaron y el job termina en rojo con el sitio caído/versión nueva rota. | Capturar los tags `sha` previos (`docker compose images`/`docker inspect`) y re-desplegar la versión anterior si healthcheck falla; documentar el runbook. |
| C-03 | P2 | `.github/workflows/ci-cd.yml:326-348` | `davent-secrets.env` queda en el workspace del runner tras el `scp` (no se borra). | `rm -f davent-secrets.env` inmediatamente después del upload + `::add-mask::` no aplica a archivos; mejor `scp` desde `stdin` o borrar en el mismo step. |
| C-04 | P2 | `.github/workflows/security-schedule.yml` | El scan semanal solo audita dependencias: no corre bandit ni gitleaks (secretos). | Sumar `bandit -ll` y `gitleaks` (o reusar el job `security` con `workflow_call`). |
| C-05 | P2 | `.github/workflows/ci-cd.yml:212-220,288-306` | Trivy escanea `fs` e `image` solo vulnerabilidades; no escanea **misconfig** de Dockerfile/compose, no genera SBOM y no firma imágenes. | `scan-type: config` (severity HIGH/CRITICAL), `sbom: true` en build-push y firma con cosign/attestation. |
| C-06 | P2 | `docker/api/Dockerfile:6,54`, `docker/web/Dockerfile:29`, `docker-compose.yml:37,57,265` | Imágenes base por tag (`python:3.11-slim-bookworm`, `postgres:16-alpine`, `redis:7.4-alpine`) sin digest; acciones de terceros por tag (`checkout@v7`, `setup-python@v7`, `setup-buildx@v4`, `metadata-action@v6`, `build-push-action@v7`) aunque gitleaks/trivy ya van por SHA. | Pinnear digests + acciones por SHA (dependabot/renovate los actualiza). |
| C-07 | P2 | `pyproject.toml:14`, `frontend/package.json:11` | Calidad débil: ruff solo `["E9","F"]`; `npm run lint` es un `echo` sin ESLint; no hay cobertura ni tests de frontend, y el job `frontend` solo corre `verify:studio` + build. | `ruff select = ["E","F","W","I","B","UP","S"]` + `ruff format --check`; ESLint flat config + Vitest para `env.js`/`catalog.api.js`/`flyer.js`; `coverage --fail-under` en backend; `--parallel` para bajar los 6 min. |
| C-08 | P3 | `.github/workflows/ci-cd.yml:195-202`; raíz | `pip-audit`/`npm audit` sin política de excepciones (un CVE sin fix rompe main indefinidamente, como ya pasó con `ignore-unfixed` de Trivy); `git pull --ff-only` en el VPS sin validar árbol limpio; `keepalive.yml` pingeando Render (borrar al pasar al VPS). | Archivo `audit-ignore.txt` versionado; `git status --porcelain` antes del pull; limpiar keepalive al cutover. |

### 3.4 Middlewares

| ID | Sev | Ubicación | Problema | Mejora |
|---|---|---|---|---|
| MW-01 | **P1** | `DaventProject/middleware.py:141-159`; throttles DRF (settings 61-126); `public_cache`; webhook dedup | Redis es dependencia **dura sin degradación**: si se cae, `cache.add/incr` propaga excepción → 500 en login de admin y en todos los endpoints con throttle; si Redis alcanza `maxmemory`, la evicción `volatile-lru` borra contadores (rate-limit multiplicado) y versiones de cache público. | Envolver acceso a cache en helper con timeout corto y política explícita (fail-open con log para throttles/dedup, fail-closed solo para login); alerta/healthcheck que detecte `REDIS_URL` vacío en prod (ver ENV-03). |
| MW-02 | P2 | `DaventProject/middleware.py` (orden actual) | No hay `X-Request-ID`/correlación ni logging de latencia; los 429 de DRF salen sin `Retry-After`; `X-Robots-Tag: noindex` solo cubre `<ADMIN_URL>/` (la API JSON es indexable); el límite de body (10 MB) vive solo en nginx — sin nginx (Render/serverless) DRF lee el body completo. | Middleware de request-id (aceptar/propagar `X-Request-ID`, loguearlo), `Retry-After` en Throttled, `X-Robots-Tag` para `/api/`, cap de `Content-Length` y `DATA_UPLOAD_MAX_MEMORY_SIZE` explícito. |
| MW-03 | P2 | `DaventProject/middleware.py:30-46` vs `StoreApp/domains/stores/services/services.py:111` | Dos implementaciones de IP de cliente: `client_ip()` (NUM_PROXIES, ignora XFF sin proxies) y el contador de visitas (toma el **último** XFF siempre). Con `NUM_PROXIES=0` o exposición directa, el contador de visitas es spoofeable. | Unificar en `client_ip()` (importar el helper, nunca duplicar parseo de XFF). |
| MW-04 | P3 | `DaventProject/middleware.py:49-84` | CSP de respaldo sin reporting (`report-to`/`report-uri`) y `unsafe-inline` inevitable para el admin; sin `Cross-Origin-Resource-Policy`. | `Content-Security-Policy-Report-Only` en una fase, CORP `same-origin` en API. |

Bien resuelto (no tocar): orden `Cors → Security → rate-limit admin → CSP →
SecurityHeaders → WhiteNoise`; CSP del SPA en `urls.py:117-162` y nginx;
`Permissions-Policy`; HSTS/secure cookies atados a `DEBUG` (default seguro) y
`check --deploy` fail-closed (`DaventProject/checks.py`).

### 3.5 Filtro de variables de entorno críticas y peligrosas

Hoy **no existe** un guard central: los controles están dispersos (checks de deploy
por dominio, preflight del deploy en CI y `entrypoint.sh`). Faltan los siguientes
puntos, que son los que convierten una variable en incidente:

| ID | Sev | Ubicación | Problema | Mejora |
|---|---|---|---|---|
| ENV-01 | **P1** | `AdminApp/domains/users/management/commands/backup_db.py:44` | `env = os.environ.copy()` y se pasa al subproceso `pg_dump`: el hijo hereda `SECRET_KEY`, `SECRETS_MASTER_KEYS`, `SECRET_MP_KEY`, `MP_WEBHOOK_SECRET`, claves SMTP/R2. Cualquier `--verbose` o volcado de entorno del proceso lo expone. | Construir un env mínimo (`PATH`, `PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE`, `PGSSLMODE`) y no heredar el resto (`env={...}`, `start_new_session=True`). |
| ENV-02 | **P1** | `docker-compose.yml:39,59,129,150,182` | `env_file: .env` inyecta **todas** las variables en db, redis, migrate, api y celery: la DB y Redis ven `SECRET_KEY`, tokens de MP, SMTP y el keyring de PII. | Reemplazar `env_file` por `environment:` explícito por servicio (db: solo `POSTGRES_*`; redis: `REDIS_PASSWORD`; api/celery: allowlist de la app) o `env_file` + `environment: {}` para no heredar lo que no se usa. |
| ENV-03 | P2 | `DaventProject/checks.py` (solo transporte) | Faltan checks de valores peligrosos: `ALLOWED_HOSTS=*`, `CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` con `*`, `SECRET_KEY` placeholder/débil (el W009 solo mira longitud ≥50), `REDIS_URL` vacío en prod (rompe throttles/multi-worker), `EMAIL_BACKEND` de consola en prod (traga mails), `MP_PAYER_EMAIL` seteado en prod, `AUTO_SEED`/`DJANGO_SUPERUSER_PASSWORD` en prod, `SECRETS_HASH_KEY` igual a una master key, `DATABASE_URL` remota sin `sslmode`. | Módulo `DaventProject/envguard.py` con denylist de **nombres** y de **valores**, expuesto como `check --deploy` (`project.E006…`) y como comando `manage.py check_env` (tabla enmascarada, exit≠0). Ver prompt §5. |
| ENV-04 | P2 | `docker/api/entrypoint.sh:9-18` | El `check --deploy` del arranque es **no estricto por defecto**: solo aborta con `DEPLOY_CHECK_STRICT=1`, y esa variable no está en `x-api-env` ni en `.env.example`. En Render el deploy arranca con configuración incompleta. | Setear `DEPLOY_CHECK_STRICT: "1"` en compose (VPS) y documentarlo en `.env.example`; en Render dejarlo en `0` explícito y compensar con el guard de ENV-03. |
| ENV-05 | P3 | build del SPA (`docker/*/Dockerfile`, `frontend/src/config/env.js`) | Nada impide que un secreto se prefije `VITE_` y quede horneado en el bundle; el fallback de `apiBaseUrl` a localhost (V-12) tampoco se detecta. | Step de CI que falle si aparece `VITE_.*(SECRET|TOKEN|KEY|PASSWORD)` en el build-arg/env y que grepee el `dist/` por patrones de secretos (`sk-`, `AKIA`, `MP_`, JWT). |

Referencia: el proyecto **ya** tiene el resto muy cubierto (`logscrub` redacta
PEM/tokens/CUIT/paths de todos los logs, `checks.py` de users/payments/invoices,
preflight del deploy en CI, `.dockerignore` excluyendo `.env`/certbot/PEM).

### 3.6 Concurrencia, idempotencia y N+1

Bien resuelto (no tocar): `select_for_update` en alta/baja de preapproval, canje de
cupón, cupos de storage, numeración de facturas (con reintento + constraint único);
webhook MP con HMAC (`compare_digest`), ventana de frescura, dedup por
`x-request-id` y `data.id` firmado; `cache.add` para dedup de visitas y sweeps;
`F()` en contadores; idempotencia de `ApplyPendingPlanQuery(renew=...)`.

| ID | Sev | Ubicación | Problema | Impacto |
|---|---|---|---|---|
| CC-01 | **P1** | `StoreApp/domains/stores/services/imaging.py:132-149` | Dos workers pueden descargar el modelo a la vez al **mismo** `path + '.tmp'` y hacer `os.replace` concurrente, sin lock entre procesos (el lock es un `threading.Lock`, solo intra-proceso); la descarga no tiene tope de tamaño ni `stream`. | Archivo de modelo corrupto (hash ya no se revalida post-replace) → fallas intermitentes o OOM del worker. |
| CC-02 | P2 | `StoreApp/domains/catalog/serializers/serializers.py:254-255` | `DiscountSerializerList.get_products_count` hace `discount.products.count()` **por descuento** en el listado. | N+1 clásico en `GET /api/discounts/` (N descuentos = N COUNT). |
| CC-03 | P2 | `AdminApp/domains/users/services/services.py:52-56,252-256` | El reset/cambio de contraseña itera `OutstandingToken` con `BlacklistedToken.objects.get_or_create` (1 SELECT + 1 INSERT por token). | N+1 de escritura; con muchas sesiones el request se estira (y bloquea el reset). Usar `bulk_create(..., ignore_conflicts=True)`. |
| CC-04 | P2 | `StoreApp/domains/stores/views/viewset.py:298-316` | El claim del slug valida disponibilidad y luego crea; una carrera de dos claims del mismo slug termina en `IntegrityError` → 500 (el registro sí maneja esa carrera; el store no). | 500 en vez de 400 "slug en uso" en una condición real (doble click/2 pestañas). |
| CC-05 | P3 | `AdminApp/domains/users/views/auth_views.py:334-347` + `services/services.py:287-299` | GET que muta y sin idempotencia explícita (aunque el token se autoinvalida por `email_verified` en el hash); ver V-08. | Riesgo menor; se resuelve con throttle + POST/redirect. |
| CC-06 | P3 | `StoreApp/domains/stores/services/services.py:101-117` | `get_or_create` + `update(F())` son 2 queries (+race de dedupe por cache). Se puede hacer `update_or_create`/`get_or_create` y un solo UPDATE, pero el impacto es bajo (ya es atómico y la dedupe es `cache.add`). | Mejora de eficiencia, no bug. |

---

## 4. Plan de remediación priorizado

**Sprint 1 — P1 (disponibilidad y secretos), sin cambiar features**
1. V-01/M-01: fingerprint del catálogo público **solo con params whitelisteados** y
   tope de longitud para `q`; key = hash de la lista canónica de filtros conocidos.
2. V-02: desactivar lockout puro por username → contador por `IP+username` con
   backoff progresivo (o lockout con CAPTCHA), y no bloquear el endpoint de
   password-reset.
3. ENV-01/ENV-02/ENV-04: env mínimo en `backup_db`; `environment:` allowlist en
   compose; `DEPLOY_CHECK_STRICT=1` en VPS/compose.
4. C-01/C-02: backup `pg_dump`→R2 antes de migrar + rollback a los tags previos si
   `up -d --wait`/`healthz` falla.
5. MW-01: helper de cache resiliente (timeout corto, fail-open con log) para
   throttles/dedup/visitas; fail-closed solo para el rate-limit del login.
6. CC-01/M-03: descarga del modelo a archivo temporal único + `os.replace` atómico,
   lock entre procesos (`fcntl`/`msvcrt`) y tope de bytes; evaluar precargar el
   modelo fuera del worker HTTP o aislarlo en un proceso/tarea.

**Sprint 2 — P2**
7. ENV-03: `envguard.py` + checks `project.E006+` + `manage.py check_env` (ver §5).
8. V-06: mover correos (verificación, reset, factura, contacto, denuncia) y
   `FinalizeInvoiceQuery` a `@shared_task` Celery con `retry_backoff`; el request
   solo encola. Si no se adopta Celery: eliminar el servicio `celery` del compose y
   documentar el envío sincrónico con timeout.
9. V-04/V-05: `PASSWORD_RESET_TIMEOUT = 3600` (y TTL de verificación 24 h con
   generator propio); encolar el mail elimina el canal de timing.
10. V-07: fallback de adjuntos del chat fuera de `MEDIA_ROOT` público o fuera de
    `/media/` (directorio privado servido solo por la API autenticada), o exigir R2
    en producción.
11. V-03: captcha con nonce de un solo uso (contador de intentos por challenge en
    cache), respuesta con más entropía y `CAPTCHA_MIN_SECONDS` efectivo.
12. C-03/C-04/C-05/C-06/C-07: limpiar el archivo de secretos del runner; bandit +
    gitleaks semanal; Trivy `config` + SBOM + firma; digests/SHA pinning; ruff y
    ESLint/Vitest/coverage.
13. MW-02/MW-03: request-id + latencia, `Retry-After` en 429, `X-Robots-Tag` en
    `/api/`, body cap; unificar `client_ip()`.
14. CC-02/CC-03/CC-04: `Count` annotation en descuentos; `bulk_create` de
    blacklist; `try/except IntegrityError` en el claim de slug.
15. M-02: TTL (p. ej. 7 días) en las keys de versión del cache público y borrado en
    `post_delete` de `Store`.

**Sprint 3 — P3**
16. V-09 (sha256 o `usedforsecurity=False`), V-10 (throttle del reset de admin),
    V-11 (`tmp*/` en `.gitignore`/`.dockerignore` + limpieza), V-12 (fallback
    `/api`), V-13 (CSP reporting), M-04, M-05, C-08.

**Criterios de aceptación globales**
- `manage.py test` 881/881 en CI (y local con `%TEMP%` escribible).
- `manage.py check --deploy` con env de producción **sin** `project.E00x` nuevos.
- `manage.py check_env` en verde con el `.env` de prod y en rojo con cada variable
  peligrosa de la denylist (test dedicado).
- `bandit -ll` 0 hallazgos (o `nosec` justificado en el único falso positivo).
- `npm audit --omit=dev --audit-level=high` 0; `npm run lint` real.
- Deploy de prueba: backup antes de migrar y rollback verificado forzando un
  healthcheck fallido.
- CI con `--parallel` y cobertura mínima acordada.

---

## 5. Prompt de corrección (listo para pegar en un agente implementador)

> **Contexto.** Repo DAVENT (Django+DRF en la raíz, SPA Vue en `frontend/`). Reglas
> de `AGENTS.md` vigentes: ir directo al código, cambios quirúrgicos, commits
> convencionales al terminar cada fix, nunca commitear `.env`/`venv`/`node_modules`.
> Esta auditoría (30/10/2026) dejó el detalle en
> `docs/AUDITORIA_TECNICA_2026-10-30.md`: leelo completo antes de tocar nada.
>
> **Objetivo.** Resolver TODOS los hallazgos del reporte en este orden, un commit
> por bloque, sin cambiar comportamiento funcional salvo lo indicado:
>
> **Bloque 1 — Disponibilidad y secretos (P1).**
> a) `StoreApp/domains/stores/views/viewset.py`: reemplazar `_params_fingerprint`
> por una huella basada **solo** en los filtros soportados (`category`, `brand`,
> `q` recortado a 80 chars, `features` normalizado, `offer`, `new`, `min_price`,
> `max_price`, `sort`), ignorando cualquier otro query param. Tests:
> `?x=1` y `?x=2` comparten entrada; los filtros válidos no colisionan.
> b) `public_cache.py`: TTL para `stores:pub:ver:*`/`epoch` (7 días) y `post_delete`
> de `Store` que borre su key y su versión.
> c) `auth_views.py`: lockout por `hash(username)+IP` con backoff (5→429 inmediato,
> 10→429 15 min) usando un solo contador; no bloquear `password-reset`; agregar
> test de que un atacante con IP rotativa no bloquea una cuenta víctima 15 min con
> tráfico distribuido (simular 10 IPs, 1 intento cada una → no lockout global).
> d) `backup_db.py`: `subprocess.run(..., env=env_minimo)` sin heredar; test unitario
> que verifique que el env del hijo no contiene `SECRET_KEY`/`MP_*`.
> e) `docker-compose.yml`: allowlist `environment:` por servicio (db/redis/api/
> celery/migrate), sin `env_file: .env` para db/redis; agregar
> `DEPLOY_CHECK_STRICT: "1"` a `x-api-env` y documentarlo en `.env.example`.
> f) `ci-cd.yml` deploy: antes de `docker compose run --rm migrate` ejecutar
> `docker compose run --rm api python manage.py backup_db` (fail-closed); guardar
> los tags previos y, si `up -d --wait` o el healthz final fallan, volver a
> levantar los tags anteriores y fallar el job con un mensaje que diga el sha.
> g) Helper `DaventProject/cache_utils.py` con `cache_get/cache_add/cache_incr`
> tolerantes a excepción (log + fail-open) y migrar middleware, throttles de
> dedup/visitas y `public_cache`; el rate-limit del login mantiene fail-closed.
> h) `imaging.py`: descarga a `tempfile.mkstemp` + `os.replace` atómico, lock de
> archivo entre procesos y `Content-Length`/stream con tope (p. ej. 200 MB);
> test de dos `_ensure_model` concurrentes (threads) que no corrompan el archivo.
>
> **Bloque 2 — Env guard central (P2).**
> Crear `DaventProject/envguard.py` con:
> `DANGEROUS_NAMES = {'PYTHONPATH','PYTHONSTARTUP','LD_PRELOAD','LD_LIBRARY_PATH',
> 'DJANGO_SETTINGS_MODULE','AUTO_SEED','DJANGO_SUPERUSER_PASSWORD',
> 'MP_WEBHOOK_ALLOW_UNSIGNED','DEPLOY_CHECK_STRICT'}` (estas dos últimas solo si el
> valor es peligroso) y `DANGEROUS_VALUES` con validadores: `ALLOWED_HOSTS` sin `*`,
> `CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` sin `*` y https, `SECRET_KEY` no
> vacía/no placeholder (`change-me`, `ci-only`, `django-insecure`) y ≥50 chars,
> `REDIS_URL` obligatoria con `DEBUG=False`, `EMAIL_BACKEND` no console en prod,
> `MP_PAYER_EMAIL` vacía en prod, `SECRETS_HASH_KEY` distinta de cada master key,
> `DATABASE_URL` remota con `sslmode` (excepto `localhost`), `DEBUG` booleano.
> Exponer `@register(Tags.security, deploy=True)` con ids `project.E006…` y un
> comando `manage.py check_env` (tabla nombre→estado con valores enmascarados,
> exit 1 si hay errores). Añadir tests: cada regla positiva/negativa con
> `override_settings`/`patch.dict`. Actualizar `SECURITY_AUDIT.md` y `.env.example`.
>
> **Bloque 3 — Correos y Celery (P2).**
> Definir `AdminApp/domains/users/tasks.py` (`send_verification_email`,
> `send_password_reset_email`, `send_invoice_email`, `send_contact_email`,
> `send_legal_report_email`) con `@shared_task(autoretry_for=(Exception,),
> retry_backoff=True, max_retries=3)`; los services dejan de enviar en línea y
> encolan post-commit (`.delay`). Tests: `mail.outbox` no crece en el request y
> crece al ejecutar la task (usar `CELERY_TASK_ALWAYS_EAGER=True` en tests).
> Si el proyecto decide no usar Celery: eliminar el servicio `celery` del compose y
> `DaventProject/celery.py`, y dejar el envío con `EMAIL_TIMEOUT` reducido —
> justificar en el commit.
>
> **Bloque 4 — Resto P2.** Captcha de un solo uso con nonce y contador de intentos;
> `PASSWORD_RESET_TIMEOUT=3600` + TTL de verificación; adjuntos del chat fuera de
> `/media/` público; N+1 de descuentos con `Count`; `bulk_create` en blacklist de
> tokens; `try/except IntegrityError` en claim de slug; CI: limpiar
> `davent-secrets.env`, bandit+gitleaks semanales, Trivy `config`+SBOM+firma,
> digests/SHA pinning, ruff `["E","F","W","I","B","UP","S"]`+format, ESLint+Vitest,
> cobertura y `--parallel`; middlewares: request-id, `Retry-After`, `X-Robots-Tag`
> en `/api/`, body cap, unificar `client_ip`.
>
> **Bloque 5 — P3.** SHA1 (`usedforsecurity=False` o sha256), throttle del reset de
> admin, `tmp*/` en `.gitignore`/`.dockerignore` + limpieza, fallback de
> `apiBaseUrl` a `/api`, CSP reporting, `onUnmounted` en `LoginView`, poda de
> `StoreDailyVisit`.
>
> **Reglas de ejecución.** Un commit por bloque (`fix:`, `chore:`, `ci:`, `docs:`).
> Correr antes de cada commit: `python manage.py test` (todo verde), `python
> manage.py check --deploy` (sin errores nuevos), `ruff check`, `npm run build`.
> No tocar `.env`, no commitear artefactos, actualizar `AGENTS.md`/`SECURITY_AUDIT.md`
> cuando cambie una regla operativa. Al terminar, entregar un resumen con:
> hallazgo → archivos tocados → test que lo cubre → resultado.
