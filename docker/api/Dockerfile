# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv
# La config web de Firebase (apiKey/authDomain/...) es PÚBLICA por diseño:
# viaja en el bundle del browser; la protección real son los Authorized
# domains del proyecto + la cuota Spark. No son secretos — el check no aplica.
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
# pip actualizado: es el binario que descarga de PyPI en este stage.
RUN python -m pip install --upgrade pip
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
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL=/api
ARG VITE_PLATFORM_DOMAIN=daventsaas.onrender.com
ARG VITE_APP_URL=https://daventsaas.onrender.com
ARG VITE_APP_NAME=DAVENT
ARG VITE_APP_TAGLINE="Gestion SaaS para e-commerce tecnologicos"
# Firebase Phone Auth: config web pública por diseño (viaja en el bundle);
# defaults = el proyecto davent-f089b. Render no pasa env vars al build, así
# que el default es lo que hace que la feature exista en el bundle de prod.
ARG VITE_FIREBASE_API_KEY=AIzaSyAUE2OoFITeDNAsEQxnoGDqfIvj6mfrWJs
ARG VITE_FIREBASE_AUTH_DOMAIN=davent-f089b.firebaseapp.com
ARG VITE_FIREBASE_PROJECT_ID=davent-f089b
ARG VITE_FIREBASE_APP_ID=1:647641643379:web:adb1f08585ee7270986d06
# Login social (Google): el client ID es público por diseño (viaja en cada
# página). Vacío = botón oculto.
ARG VITE_GOOGLE_CLIENT_ID=10828662216-ff1ocahbbaj7ul6qpv3p5c3so3jk25p7.apps.googleusercontent.com
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_PLATFORM_DOMAIN=$VITE_PLATFORM_DOMAIN \
    VITE_APP_URL=$VITE_APP_URL \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_APP_TAGLINE=$VITE_APP_TAGLINE \
    VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY \
    VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN \
    VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID \
    VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
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
COPY . .
COPY --from=frontend /fe/dist /app/frontend_dist
COPY docker/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app
USER app
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "-c", "docker/api/gunicorn.conf.py", "DaventProject.wsgi:application"]
