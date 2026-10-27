# syntax=docker/dockerfile:1
# Imagen de la API DRF (gunicorn) — también la usa el worker Celery y el job migrate.

# ---------- Stage 1: compila wheels de requirements.txt ----------
FROM python:3.11-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# gcc/libpq por si alguna dependencia no trae wheel para py3.11.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends gcc libpq-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# pip pinneado: el binario que descarga de PyPI en este stage. Sin pin, el
# resolver cambia entre minors y el build deja de ser reproducible.
RUN python -m pip install --upgrade "pip==24.3.1"
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------- Stage 1b: build de la SPA Vue (servida por el propio contenedor) ----------
# En deploys serverless (Render free) no hay un segundo host para el front ni
# proxy de confianza: la API sirve el dist estático ella misma. VITE_* se
# hornean acá porque Vite las inyecta en build-time — para otro dominio hay
# que rebuildear pasando --build-arg.
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Vite hornea las VITE_* en build-time. Los ARG ya llegan al RUN como
# variables de entorno: el bloque `ENV VITE_*=...` era redundante y era lo
# único que disparaba el check SecretsUsedInArgOrEnv (de ahí el skip global).
ARG VITE_API_BASE_URL=/api
ARG VITE_PLATFORM_DOMAIN=daventsaas.onrender.com
ARG VITE_STORE_SUBDOMAINS=
ARG VITE_APP_URL=https://daventsaas.onrender.com
ARG VITE_APP_NAME=DAVENT
ARG VITE_APP_TAGLINE="Gestion SaaS para e-commerce tecnologicos"
# Login social (Google): el client ID NO se hornea — el frontend lo pide en
# runtime a GET /api/config/ (env GOOGLE_CLIENT_ID del backend). Sin var
# ahí el botón queda oculto.
RUN npm run build

# ---------- Stage 2: runtime mínimo, sin toolchain ----------
FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
# Parcho la imagen base primero: la slim queda semanas atrás de los security
# updates de Debian (openssl, libc, ca-certificates). Sin esto el contenedor
# arranca con CVEs ya corregidos upstream y un store de CAs potencialmente
# desactualizado para TLS saliente (R2, MercadoPago, SMTP).
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends wget gnupg ca-certificates
# pg_dump para `manage.py backup_db` (cron del host -> compose exec api).
# La imagen base solo ofrece el cliente 15 y el server de compose es 16:
# se instala postgresql-client-16 desde el repo oficial PGDG.
RUN echo "deb https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*
# Usuario no-root: un RCE dentro del contenedor no es root.
RUN groupadd -r app && useradd -r -g app -d /app -s /usr/sbin/nologin app
WORKDIR /app
COPY requirements.txt .
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
# --chown en el COPY en vez de `chown -R /app` después: el chown recursivo
# generaba una capa extra con una copia completa de la app.
COPY --chown=app:app . .
COPY --chown=app:app --from=frontend /fe/dist /app/frontend_dist
COPY --chown=app:app docker/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media \
    && chown app:app /app/staticfiles /app/media
USER app
EXPOSE 8000
# Los compose declaran su propio healthcheck; este cubre Render y cualquier
# `docker run` suelto (sin HEALTHCHECK, orquestadores externos no ven estado).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz/',timeout=4)"
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "-c", "docker/api/gunicorn.conf.py", "DaventProject.wsgi:application"]
