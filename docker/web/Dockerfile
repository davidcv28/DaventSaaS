# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv
# El client ID de Google es PÚBLICO por diseño: viaja en el bundle del
# browser; no es un secreto — el check de ARG/ENV no aplica.
# Imagen web = build del SPA Vue + nginx (reverse proxy + TLS + estáticos).
# Contexto de build: raíz del repo (.) — buildx exige que el Dockerfile viva
# dentro del contexto; los COPY referencian frontend/.

# ---------- Stage 1: build del SPA ----------
FROM node:22-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
# Vars Vite se hornean en el bundle en build-time (no en runtime).
ARG VITE_API_BASE_URL=/api
ARG VITE_PLATFORM_DOMAIN
ARG VITE_APP_NAME
ARG VITE_APP_TAGLINE
# Login social (Google): también público por diseño; vacío = botón oculto.
ARG VITE_GOOGLE_CLIENT_ID=10828662216-ff1ocahbbaj7ul6qpv3p5c3so3jk25p7.apps.googleusercontent.com
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_PLATFORM_DOMAIN=$VITE_PLATFORM_DOMAIN \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_APP_TAGLINE=$VITE_APP_TAGLINE \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
RUN npm run build

# ---------- Stage 2: nginx sirve el SPA y proxifica /api ----------
FROM nginx:1.30-alpine
# Parcheo los paquetes del runtime (openssl/musl/nginx): la imagen base
# queda atrás de los fixes de Alpine ya publicados.
RUN apk upgrade --no-cache
COPY --from=build /src/dist /usr/share/nginx/html
# Los vhosts se montan desde ./docker/web/templates y nginx:alpine los
# procesa con envsubst (${PLATFORM_DOMAIN}) al arrancar.
EXPOSE 80 443
