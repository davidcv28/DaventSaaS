# syntax=docker/dockerfile:1
# Imagen web = build del SPA Vue + nginx (reverse proxy + TLS + estáticos).
# Contexto de build: ./frontend

# ---------- Stage 1: build del SPA ----------
FROM node:20-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Vars Vite se hornean en el bundle en build-time (no en runtime).
ARG VITE_API_BASE_URL=/api
ARG VITE_PLATFORM_DOMAIN
ARG VITE_APP_NAME
ARG VITE_APP_TAGLINE
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_PLATFORM_DOMAIN=$VITE_PLATFORM_DOMAIN \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_APP_TAGLINE=$VITE_APP_TAGLINE
RUN npm run build

# ---------- Stage 2: nginx sirve el SPA y proxifica /api ----------
FROM nginx:1.27-alpine
COPY --from=build /src/dist /usr/share/nginx/html
# Los vhosts se montan desde ./docker/web/templates y nginx:alpine los
# procesa con envsubst (${PLATFORM_DOMAIN}) al arrancar.
EXPOSE 80 443
