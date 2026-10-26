# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv
# La config web de Firebase (apiKey/authDomain/...) es PÚBLICA por diseño:
# viaja en el bundle del browser; la protección real son los Authorized
# domains del proyecto + la cuota Spark. No son secretos — el check no aplica.
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
# Firebase Phone Auth (verificación de celular — la config web es PÚBLICA por
# diseño: viaja en el bundle que sirve cualquier browser; la protección real
# son los Authorized domains del proyecto + la cuota Spark, no la clave).
# Van como defaults del ARG para que el build en Render (que no recibe las
# env vars del dashboard en build-time) hornee la feature sin plomería extra;
# un --build-arg las sobreescribe si algún día hay otro proyecto Firebase.
ARG VITE_FIREBASE_API_KEY=AIzaSyAUE2OoFITeDNAsEQxnoGDqfIvj6mfrWJs
ARG VITE_FIREBASE_AUTH_DOMAIN=davent-f089b.firebaseapp.com
ARG VITE_FIREBASE_PROJECT_ID=davent-f089b
ARG VITE_FIREBASE_APP_ID=1:647641643379:web:adb1f08585ee7270986d06
# Login social (Google + Facebook): también públicos por diseño; vacíos =
# botones ocultos. Rellenar los defaults al crear las apps OAuth.
ARG VITE_GOOGLE_CLIENT_ID=
ARG VITE_FACEBOOK_APP_ID=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_PLATFORM_DOMAIN=$VITE_PLATFORM_DOMAIN \
    VITE_APP_NAME=$VITE_APP_NAME \
    VITE_APP_TAGLINE=$VITE_APP_TAGLINE \
    VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY \
    VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN \
    VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID \
    VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
    VITE_FACEBOOK_APP_ID=$VITE_FACEBOOK_APP_ID
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
