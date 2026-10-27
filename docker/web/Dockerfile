# syntax=docker/dockerfile:1
# Imagen web = build del SPA Vue + nginx (reverse proxy + TLS + estáticos).
# Contexto de build: raíz del repo (.) — buildx exige que el Dockerfile viva
# dentro del contexto; los COPY referencian frontend/.

# ---------- Stage 1: build del SPA ----------
FROM node:22-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
# Vars Vite se hornean en el bundle en build-time (no en runtime). Los ARG ya
# son visibles como env en el RUN: el bloque `ENV VITE_*` era redundante y era
# lo único que disparaba SecretsUsedInArgOrEnv.
ARG VITE_API_BASE_URL=/api
ARG VITE_PLATFORM_DOMAIN
ARG VITE_STORE_SUBDOMAINS=
ARG VITE_APP_NAME
ARG VITE_APP_TAGLINE
# Login social (Google): el client ID NO se hornea — el frontend lo pide en
# runtime a GET /api/config/ (env GOOGLE_CLIENT_ID del backend). Sin var
# ahí el botón queda oculto.
RUN npm run build

# ---------- Stage 2: nginx sin privilegios ----------
# nginx-unprivileged: master como uid 101, escucha 8080/8443, logs a stdout y
# pid en /tmp. Reemplaza al nginx oficial (master root) y elimina la necesidad
# de NET_BIND_SERVICE: el mapeo 80->8080 / 443->8443 lo hace Docker.
FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime
# apk necesita root para escribir el rootfs; se vuelve a bajar a 101 al final.
USER root
# Parcheo los paquetes del runtime (openssl/musl/nginx): la imagen base
# queda atrás de los fixes de Alpine ya publicados.
RUN apk upgrade --no-cache
COPY --from=build --chown=101:101 /src/dist /usr/share/nginx/html
# Los vhosts se montan desde ./docker/web/templates y el entrypoint de la
# imagen los procesa con envsubst (${PLATFORM_DOMAIN}) al arrancar.
USER 101
EXPOSE 8080 8443
