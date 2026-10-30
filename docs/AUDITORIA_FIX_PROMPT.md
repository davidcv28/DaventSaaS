# Prompt de corrección — hallazgos auditoría 30/10/2026

Pegar tal cual en un agente implementador (Claude/Codex/DeepSeek) con acceso al repo.
Reporte completo: `docs/AUDITORIA_TECNICA_2026-10-30.md`.

---

Eres el agente implementador de DAVENT (Django + DRF en la raíz, SPA Vue en
`frontend/`). Leé primero `AGENTS.md` y `docs/AUDITORIA_TECNICA_2026-10-30.md`.
Vas a resolver **todos** los hallazgos del reporte, en el orden de los bloques.
Reglas: cambios quirúrgicos, un commit convencional por bloque, nunca commitear
`.env`/`venv`/`node_modules`, correr los tests del área antes de cada commit.

## Bloque 1 — P1: disponibilidad, secretos y deploy

1. **Cache flooding / N+1 de keys** (`StoreApp/domains/stores/views/viewset.py`,
   `_params_fingerprint` y `public_catalog`): la huella del cache debe usar SOLO los
   filtros soportados (`category`, `brand`, `q` recortado a 80 chars, `features`
   normalizado, `offer`, `new`, `min_price`, `max_price`, `sort`) e ignorar
   cualquier otro query param. Tests nuevos: `?x=1` y `?x=2` comparten entrada;
   `?category=1` y `?category=2` no; `?q=` enorme no crece la key.
2. **TTL del versionado** (`StoreApp/domains/stores/public_cache.py`): las keys
   `stores:pub:ver:<id>` y `stores:pub:epoch` no pueden ser eternas (TTL 7 días) y
   `post_delete` de `Store` debe borrar su key. Test: `timeout` no `None` (mock de
   `cache.set/add`) y borrado en `post_delete`.
3. **Lockout de login** (`AdminApp/domains/users/views/auth_views.py`): el lockout
   por username permite DoS dirigido. Cambiar a contador por `sha256(username)+IP`
   con backoff progresivo y ventana corta; si se quiere lockout por cuenta, exigir
   CAPTCHA en vez de bloquear. Tests: 10 IPs × 1 fallo no bloquean la cuenta; una
   sola IP con 10 fallos recibe 429; un login exitoso limpia el contador.
4. **Secretos en subprocesos** (`AdminApp/domains/users/management/commands/backup_db.py`):
   dejar de pasar `os.environ.copy()` a `pg_dump`; construir env mínimo (`PATH`,
   `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE`, `HOME`).
   Test: el env del hijo no contiene `SECRET_KEY`, `MP_WEBHOOK_SECRET`,
   `SECRET_MP_KEY`, `SECRETS_MASTER_KEYS`.
5. **Compose sin sobre-exposición** (`docker-compose.yml`): reemplazar
   `env_file: .env` por allowlist `environment:` por servicio (db: `POSTGRES_*`;
   redis: `REDIS_PASSWORD`; api/celery/migrate: solo las variables que la app usa).
   Agregar `DEPLOY_CHECK_STRICT: "1"` a `x-api-env` y documentarlo en `.env.example`
   (Render lo deja en `0` explícito).
6. **Deploy con red** (`.github/workflows/ci-cd.yml`): antes de
   `docker compose run --rm migrate`, correr
   `docker compose run --rm api python manage.py backup_db` (fail-closed). Guardar
   los tags `sha` previos (`docker compose images -q`/`docker inspect`); si
   `up -d --wait` o el healthz fallan, re-desplegar la versión anterior y terminar
   el job en rojo indicando el sha. Test manual documentado en el PR.
7. **Cache resiliente** (`DaventProject/`): helper con `cache_get/cache_add/cache_incr`
   que capture excepciones (log + fail-open) para throttles, dedup de webhooks y
   contador de visitas; el rate-limit del login de admin queda fail-closed (503 con
   `Retry-After` si el cache no responde). Tests con `cache` mockeado lanzando
   excepción.
8. **Modelo ONNX** (`StoreApp/domains/stores/services/imaging.py`): descarga a un
   `mkstemp` único, `os.replace` atómico, lock **entre procesos** (`fcntl`/`msvcrt`)
   y tope de bytes con `stream=True`. Test de dos `_ensure_model` concurrentes que
   no corrompen el archivo. Evaluar mover la inferencia fuera del worker HTTP o
   documentar el consumo de RAM.

## Bloque 2 — P2: filtro central de env vars

Crear `DaventProject/envguard.py` con:

- `DANGEROUS_NAMES`: `PYTHONPATH`, `PYTHONSTARTUP`, `LD_PRELOAD`, `LD_LIBRARY_PATH`,
  `DJANGO_SETTINGS_MODULE`, `AUTO_SEED`, `DJANGO_SUPERUSER_PASSWORD`,
  `MP_WEBHOOK_ALLOW_UNSIGNED` (si es true), `DEPLOY_CHECK_STRICT` (si es `0`).
- `DANGEROUS_VALUES`: `ALLOWED_HOSTS` con `*`; `CORS_ALLOWED_ORIGINS`/
  `CSRF_TRUSTED_ORIGINS` con `*` o http en prod; `SECRET_KEY` vacía/placeholder
  (`change-me`, `django-insecure`, `ci-only`) o <50 chars; `REDIS_URL` vacía con
  `DEBUG=False`; `EMAIL_BACKEND` de consola en prod; `MP_PAYER_EMAIL` seteada en
  prod; `SECRETS_HASH_KEY` igual a una master key; `DATABASE_URL` remota sin
  `sslmode`; `DEBUG` no booleano.
- Un `@register(Tags.security, deploy=True)` con ids `project.E006…E0xx` y un comando
  `manage.py check_env` que imprime tabla nombre→OK/ERROR con valores enmascarados
  y sale con código 1 si hay errores.
- Tests por cada regla (positivo y negativo) con `override_settings`/`patch.dict`.
- CI: `python manage.py check_env` en el job `test` con el env de CI y un test que
  verifique que el `.env.example` no dispara errores.

## Bloque 3 — P2: correos fuera del request (Celery)

- `AdminApp/domains/users/tasks.py`: `send_verification_email`,
  `send_password_reset_email`, `send_invoice_email`, `send_contact_email`,
  `send_legal_report_email` con
  `@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)`.
- Los services (`users/services/services.py`, `invoices/services/services.py`,
  `stores/services/contact.py`, `legal/services/services.py`) encolan post-commit
  con `.delay(...)`; el request no espera SMTP.
- `CELERY_TASK_ALWAYS_EAGER=True` en tests: `mail.outbox` no crece en el request y
  crece al ejecutar la task.
- Si se decide NO usar Celery: eliminar `celery` del compose y `DaventProject/celery.py`,
  y bajar `EMAIL_TIMEOUT`; justificarlo en el commit.

## Bloque 4 — P2 restantes

- Captcha (`stores/services/contact.py`): nonce de un solo uso con contador de
  intentos por challenge en cache, respuesta con más entropía (>17 valores) y TTL
  corto; el mismo módulo sirve a reseñas.
- `settings.py`: `PASSWORD_RESET_TIMEOUT = 3600`; token de verificación de email con
  TTL de 24 h propio (generator con `settings` documentado).
- Adjuntos del chat: sin R2 no servir en `/media/` público — mover a un directorio
  privado servido solo por una vista autenticada, o exigir R2 en prod.
- N+1: `DiscountSerializerList` con `Count('products')` anotado en el queryset
  (`StoreApp/domains/catalog/views/viewset_config.py` para `discounts`).
- `ConfirmPasswordResetQuery`/cambio de clave: `bulk_create(..., ignore_conflicts=True)`
  de `BlacklistedToken` y borrar `OutstandingToken` en una sola query.
- Claim de slug: `try/except IntegrityError` → 400 "Ese link ya está en uso".
- CI: borrar `davent-secrets.env` después del scp; bandit + gitleaks en el workflow
  semanal; Trivy `scan-type: config` + `sbom: true` + firma; digests de imágenes y
  acciones por SHA; ruff `["E","F","W","I","B","UP","S"]` + `ruff format --check`;
  ESLint flat config + Vitest para `env.js`/`catalog.api.js`/`flyer.js`; coverage
  `--fail-under` y `manage.py test --parallel`.
- Middlewares: request-id (`X-Request-ID` aceptado/propagado y logueado), `Retry-After`
  en 429, `X-Robots-Tag: noindex` para `/api/`, cap de body también sin nginx.
- Unificar `record_store_visit` con `client_ip()` (un solo parseo de XFF).

## Bloque 5 — P3

- `ai_design.py`: `hashlib.sha1(..., usedforsecurity=False)` o sha256.
- Throttle (o rate-limit por middleware) para `/admin/password_reset/`.
- `tmp*/` en `.gitignore` y `.dockerignore`; borrar los 118 directorios `tmp*`
  locales (verificar rutas antes de borrar).
- `frontend/src/config/env.js`: fallback de `apiBaseUrl` a `/api`.
- CSP: `Content-Security-Policy-Report-Only` en una fase y CORP `same-origin`.
- `LoginView.vue`: `clearInterval` en `onUnmounted`.
- Poda de `StoreDailyVisit` (comando o tarea retención).

## Verificación final (obligatoria antes de entregar)

```
venv/Scripts/python.exe manage.py test                      # 881+ tests OK
venv/Scripts/python.exe manage.py check --deploy            # sin errores nuevos
venv/Scripts/python.exe manage.py check_env                 # verde con .env de prod
venv/Scripts/python.exe -m bandit -r AdminApp StoreApp SuscriptionApp DaventProject -ll
venv/Scripts/python.exe -m pip_audit -r requirements.txt
cd frontend && npm run lint && npm run build && npm audit --omit=dev --audit-level=high
```

Entregar un resumen: hallazgo → archivos tocados → test que lo cubre → resultado del
comando. Nada de explicaciones largas; commits `fix:`/`ci:`/`chore:` cortos.
