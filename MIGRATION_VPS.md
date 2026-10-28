# DAVENT — Migración a VPS (DonWeb Cloud Server)

Runbook completo para mover el stack de **Render + Neon** a un **VPS propio**
(Docker Compose, Argentina, dominio propio con subdominios por tienda).

> ⚠️ **Este archivo se mantiene sincronizado con `.env.example` y
> `docker-compose.yml`.** Si cambian env vars, servicios o el compose,
> actualizar las secciones §2 y §4 en el mismo commit.

Referencia rápida del estado actual (free tier):
- API + SPA: Render free (`daventsaas.onrender.com`, keepalive por Actions)
- DB: Neon free (o Aiven free si se migró antes)
- Imágenes: Cloudflare R2 (no migran — las URLs no cambian)
- Emails: Brevo SMTP

---

## 0. Qué migra y qué no

| Dato | Dónde vive | ¿Migra? |
|---|---|---|
| Usuarios, tiendas, productos, suscripciones, cupones, facturas, chats, tokens | Postgres | ✅ Sí (dump) |
| Imágenes de tiendas y adjuntos de chat | R2 | ❌ No — URLs intactas |
| `.env` | Local / Render dashboard | ✅ Copia + vars nuevas (§2) |
| Sesiones activas | Tablas `token_blacklist` en la DB | ✅ Viajan con el dump — nadie se desloguea |

---

## 1. Prerequisitos

- [ ] **Dominio** `.com.ar` comprado en nic.ar (CUIL + Clave Fiscal nivel 2)
      y delegado a los nameservers de **Cloudflare** (cuenta gratis).
      Placeholder en esta guía: `davent.com.ar`.
- [ ] **VPS DonWeb Cloud Server** activo — mínimo recomendado producción:
      **2 vCPU / 2 GB RAM / 20 GB SSD** (Ubuntu + Docker + Compose v2
      preinstalados). Con 1 GB arranca pero va justo de RAM.
- [ ] Acceso **SSH** al VPS (usuario + clave).
- [ ] **PAT de GitHub** con `read:packages` (para `docker login ghcr.io`
      y bajar las imágenes que buildea el CI).
- [ ] **Token API de Cloudflare** con permiso `Zone.DNS:Edit` sobre la zona
      (para el cert wildcard ACME DNS-01 — archivo `docker/certbot/cloudflare.ini`,
      `chmod 600`, **no commitear**).
- [ ] `pg_dump` 16 accesible para sacar el dump de Neon (instalar
      `postgresql-client-16` local, o `docker run --rm postgres:16-alpine pg_dump`,
      o correr `backup_db` local con `.env` apuntando a Neon → dump queda en R2).

---

## 2. `.env` del VPS

El `.env` **nunca va por git** (ya está en `.gitignore`). Viaja por `scp`:

```bash
scp .env usuario@<IP-VPS>:/opt/davent/.env
```

Pero **no se copia tal cual**. Tabla completa:

### Copiar igual desde el `.env` actual

```
SECRET_KEY=
SECRET_MP_KEY=
MP_WEBHOOK_SECRET=
MP_PAYER_EMAIL=              # solo credenciales TEST
S3_API=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
R2_PUBLIC_URL=
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=2525
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
LEGAL_REPORTS_EMAIL=
ADMIN_URL=                   # path no obvio del admin
GOOGLE_CLIENT_ID=
ISSUER_NAME=DAVENT
ISSUER_CUIT=
ISSUER_ADDRESS=
ISSUER_EMAIL=
ISSUER_TAX_CONDITION=
ISSUER_IIBB=
ISSUER_ACTIVITY_START=
BACKUP_RETENTION_DAYS=14
AUTO_SEED=1
DJANGO_SUPERUSER_USERNAME=   # primer arranque; luego se puede quitar
DJANGO_SUPERUSER_PASSWORD=
DJANGO_SUPERUSER_EMAIL=
```

### Generar nuevas (servicios locales del VPS)

```bash
# Generar con: openssl rand -hex 24   (o similar)
POSTGRES_DB=davent
POSTGRES_USER=davent
POSTGRES_PASSWORD=<nueva-fuerte>
REDIS_PASSWORD=<nueva-fuerte>
GUNICORN_WORKERS=3
GUNICORN_THREADS=4
```

> `DATABASE_URL` / `REDIS_URL` / `CELERY_BROKER_URL` **no se cargan**: el
> compose las deriva de estas vars (ver `x-api-env` en docker-compose.yml).
> Si el `.env` trae `DATABASE_URL` de Neon queda ignorada (environment > env_file).

### Cambiar por el dominio propio

```
PLATFORM_DOMAIN=davent.com.ar
ALLOWED_HOSTS=.davent.com.ar                  # el punto = apex + *.subdominios
CORS_ALLOWED_ORIGINS=https://www.davent.com.ar,https://davent.com.ar
CORS_ALLOW_CREDENTIALS=True
CSRF_TRUSTED_ORIGINS=https://www.davent.com.ar,https://davent.com.ar,https://*.davent.com.ar
FRONTEND_URL=https://www.davent.com.ar        # canónico www (apex -> 301 www)
BACKEND_URL=https://www.davent.com.ar         # links de mails
SECURE_PROXY_SSL=True
SECURE_SSL_REDIRECT=False                     # el 80->443 lo hace nginx
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=False
DEBUG=False
```

> **URLs canónicas (regla fija, ver `AGENTS.md`)**: plataforma en
> `https://www.davent.com.ar` (el apex lo redirige nginx) y cada tienda en
> `https://<slug>.davent.com.ar` — **un solo label**. Nunca `www.<slug>.davent.com.ar`:
> el wildcard DNS y el cert `*.davent.com.ar` no cubren dos niveles.

> Subdominios `<slug>.davent.com.ar`: en el build de la imagen `web` pasar
> `VITE_PLATFORM_DOMAIN=davent.com.ar` (sale de `PLATFORM_DOMAIN` del `.env`
> vía build-arg del compose) y dejar `VITE_STORE_SUBDOMAINS` vacío = auto-on.
> El build lo hace el CI a GHCR — verificar el `vars.PLATFORM_DOMAIN` del repo.

---

## 3. DNS (dominio + wildcard)

nic.ar solo **registra** — los registros DNS se administran en Cloudflare:

1. En Cloudflare: *Add site* → `davent.com.ar` → plan Free → te da 2 nameservers.
2. En nic.ar: *Delegar* → poner esos 2 nameservers (propaga en horas).
3. En Cloudflare DNS:

   | Tipo | Nombre | Valor | Proxy |
   |---|---|---|---|
   | A | `@` | `<IP-VPS>` | Solo DNS (recomendado al inicio) |
   | A | `*` | `<IP-VPS>` | Solo DNS |
   | A | `www` | `<IP-VPS>` | Solo DNS |

   > El `*` es el wildcard que hace resolver `cualquier-slug.davent.com.ar`.
   > Certbot DNS-01 funciona igual con o sin proxy naranja.

4. Token API para certbot: *My Profile → API Tokens → Create* → template
   "Edit zone DNS" → zona `davent.com.ar` → guardar el token en
   `docker/certbot/cloudflare.ini` (en el VPS, `chmod 600`):

   ```ini
   dns_cloudflare_api_token = <token>
   ```

---

## 4. Setup inicial del VPS

```bash
ssh usuario@<IP-VPS>

# 1. Repo (compose, templates nginx, certbot)
git clone https://github.com/davidcv28/DaventSaaS.git /opt/davent
cd /opt/davent

# 2. .env real (desde tu PC: scp .env usuario@IP:/opt/davent/.env)

# 3. Credenciales GHCR para bajar las imágenes del CI
docker login ghcr.io -u davidcv28 -p <PAT-read:packages>

# 4. Bajar imágenes (api + web ya buildeadas por el CI)
docker compose pull

# 5. Levantar SOLO Postgres (DB vacía — necesario para el restore limpio,
#    ver §5). NO hacer 'up -d' completo todavía.
docker compose up -d db
```

---

## 5. Migración de la base de datos

**Hacerlo de madrugada / baja actividad**: lo que se escriba en Neon entre el
dump y el cutover se pierde. Con la DB chica (MBs) el dump tarda segundos.

### 5a. Dump de Neon (desde tu PC)

```bash
# Opción A — directo (necesita pg_dump 16 local o vía docker):
pg_dump --format=plain --no-owner --no-privileges "<DATABASE_URL_NEON>" \
  | gzip > davent.sql.gz

# Opción B — con el comando del proyecto (dump queda en R2):
#   .env local con DATABASE_URL=neon → venv/Scripts/python.exe manage.py backup_db
#   y en el VPS: aws s3 cp s3://<bucket>/backups/<file>.sql.gz - | gunzip | ...
```

### 5b. Subir y restaurar en el VPS

```bash
scp davent.sql.gz usuario@<IP-VPS>:/tmp/
ssh usuario@<IP-VPS>
cd /opt/davent

# Restaurar en la DB vacía levantada en §4:
gunzip -c /tmp/davent.sql.gz | docker compose exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Levantar el stack completo: el job 'migrate' corre solo (no-op, el schema
# del dump ya es el actual) y luego api/celery/web.
docker compose up -d
```

> **Orden importante**: restaurar ANTES del primer `up` completo. El dump
> trae schema+datos; si migrate creara el schema primero, el restore pisaría
> con errores de "relation already exists".

### 5c. Verificación antes del cutover

Entrar por `http://<IP-VPS>` (o dominio temporal) y chequear:

- [ ] Login con un usuario existente (sesión migra con los tokens)
- [ ] `GET /healthz/` → `{"status":"ok"}`
- [ ] Una tienda pública responde por slug
- [ ] Las imágenes cargan (R2 — nada cambió)
- [ ] Canje de un cupón de prueba funciona

---

## 6. TLS wildcard (certbot DNS-01)

Con el dominio ya delegado a Cloudflare y el `cloudflare.ini` en
`docker/certbot/` (chmod 600, no commiteado):

```bash
cd /opt/davent

# Emisión única del wildcard (apex + *.dominio):
docker compose --profile certbot run --rm certbot \
  certonly --dns-cloudflare \
  --dns-cloudflare-credentials /run/secrets/cloudflare.ini \
  -d davent.com.ar -d "*.davent.com.ar" \
  -m <tu-email> --agree-tos --no-eff-email

# Recargar nginx para tomar el cert:
docker compose exec web nginx -s reload
```

Los certs quedan en el volumen `letsencrypt` (montado ro en `web`; el vhost
`server_name .${PLATFORM_DOMAIN}` ya cubre apex + subdominios).

**Cron de renovación** en el host (`crontab -e`):

```cron
0 4 * * 1 cd /opt/davent && docker compose --profile certbot run --rm certbot renew --quiet && docker compose exec web nginx -s reload
0 5 * * *  cd /opt/davent && docker compose exec -T api python manage.py backup_db
```

---

## 7. Cutover DNS

1. Un día antes: bajar TTL de los records a ~300s (propagación en minutos).
2. Cambiar los A records `@` / `*` / `www` a la IP del VPS (si estaban
   apuntando a Render por el interino).
3. Verificar desde el exterior: `https://davent.com.ar` y
   `https://<slug-real>.davent.com.ar` con TLS válido.
4. Tráfico ya corre en el VPS.

---

## 8. CI/CD (deploys futuros por push)

El workflow `ci-cd.yml` ya tiene el job `deploy` (SSH → inyecta secretos de
webhook + `git pull` + `compose pull` + `migrate` + `up -d --wait` + healthz
externo). En GitHub:

- **Secrets** (Settings → Secrets → Actions): `SSH_HOST`, `SSH_PORT`,
  `SSH_USERNAME`, `SSH_PRIVATE_KEY`, `SSH_HOST_FINGERPRINT`,
  `MP_WEBHOOK_SECRET`, `SECRET_MP_KEY`
  - `SSH_HOST_FINGERPRINT` pineade la host key del VPS (sin esto el SSH no
    verifica contra quién habla): `ssh-keyscan -p <puerto> <host> | ssh-keygen -lf -`
  - `MP_WEBHOOK_SECRET` / `SECRET_MP_KEY` los escribe el deploy en el `.env`
    del VPS (merge atómico, `chmod 600`) y **falla antes de tocar contenedores**
    si faltan o son cortos: sin firma HMAC los webhooks de MP quedan en 401.
  - Mejor definirlos en el **Environment `production`** (Settings →
    Environments) para que requieran aprobación y no estén disponibles en
    cualquier job del repo.
- **Variable**: `PLATFORM_DOMAIN` = `davent.com.ar` (alimenta el build-arg
  `VITE_PLATFORM_DOMAIN` de la imagen web)

Después de esto, cada push a `main` deploya solo al VPS.

---

## 9. Rollback y apagado del free tier

**NO apagar Render/Neon el mismo día** — quedan de rollback gratis:

- [ ] Día D → D+2/3: VPS en producción, Render+Neon arriba sin tocar.
      Si el VPS falla: revertir DNS → vuelve todo en minutos.
- [ ] Verificado estable → Render: *Suspend service*. Neon: *Delete project*
      (con un dump final en R2 por las dudas).
- [ ] Quitar el workflow `keepalive.yml` (ya no aplica — hay nota en su header)
      o dejarlo, no molesta.
- [ ] Confirmar cron de `backup_db` corriendo en el VPS (logs de R2).

---

## 10. Checklist resumen

```
[ ] Dominio comprado + delegado a Cloudflare
[ ] VPS activo + SSH + docker login ghcr.io
[ ] cloudflare.ini (token DNS) en docker/certbot/
[ ] .env del VPS armado (§2)
[ ] Madrugada: dump de Neon → scp → restore en db vacía
[ ] up -d → verificación completa (§5c)
[ ] certbot wildcard + reload nginx
[ ] DNS cutover + probar apex y subdominio de tienda
[ ] Crons: backup_db diario + certbot renew
[ ] Secrets SSH_* + var PLATFORM_DOMAIN en GitHub
[ ] 2-3 días de gracia → apagar Render + Neon
```
