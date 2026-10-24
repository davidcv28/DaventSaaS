# syntax=docker/dockerfile:1
# Imagen web = build del SPA Vue + nginx (reverse proxy + TLS + estáticos).
# Contexto de build: raíz del repo (.) — buildx exige que el Dockerfile viva
# dentro del contexto; los COPY referencian frontend/.

# ---------- Stage 1: build del SPA ----------
FROM node:20-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
# Vars Vite se hornean en el bundle en build-time (no en runtime).
ARG VITE_API_BASE_URL=/api
ARG VITE_PLATFORM_DOMAIN
ARG VITE_APP_NAME
ARG VITE_APP_TAGLINE
# Firebase Phone Auth (verificación de celular — config pública de cliente;
# vacío = feature deshabilitada en el bundle).
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_APP_ID
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_PLATFORM_DOMAIN=$VITE_PLATFORM_DOMAIN \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_APP_TAGLINE=$VITE_APP_TAGLINE \
    VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY \
    VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN \
    VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID \
    VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID
RUN npm run build

# ---------- Stage 2: nginx sirve el SPA y proxifica /api ----------
FROM nginx:1.27-alpine
# Parcheo los paquetes del runtime (openssl/musl/nginx): la imagen base
# queda atrás de los fixes de Alpine ya publicados.
RUN apk upgrade --no-cache
COPY --from=build /src/dist /usr/share/nginx/html
# Los vhosts se montan desde ./docker/web/templates y nginx:alpine los
# procesa con envsubst (${PLATFORM_DOMAIN}) al arrancar.
EXPOSE 80 443
