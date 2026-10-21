# DAVENT · Frontend (Vue 3)

Interfaz web de **autenticación, registro y recuperación** conectada a la API Django (`ARCHITECTURE.md`).

## Stack
Vue 3.4 + Vite 5 + Router 4 + Pinia 2 + Axios 1. CSS con tokens propios (sin UI lib).

## Reglas
Ver **`FRONTEND_RULES.md`** — es la fuente de verdad para próximos prompts (estructura, contrato API, validaciones, UX).

## Puesta en marcha
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxy /api -> 127.0.0.1:8000)
npm run build    # dist/ para producción
```

Backend esperado: Django en `http://127.0.0.1:8000` con `POST /api/token/` activo.
CORS ya habilita `http://localhost:5173`.

## Rutas
- `/login` — JWT + throttle 5/min + refresh automático
- `/register` — wizard 3 pasos (cuenta → fiscal → contacto), espejo de validadores Django
- `/forgot-password` y `/reset-password` — cableadas, en modo `pending-backend` hasta que Django exponga `password-reset`
- `/dashboard` — protegida: resumen + estado de suscripción + catálogo de planes
  (`GET /suscription-plans/`, `GET/POST /suscriptions/`, `PUT /suscriptions/<pk>/`),
  placeholders de catálogos (próximo dominio) y cuenta (perfil + cambio de clave).

## Pendiente backend (avisos ya contemplados en UI)
1. Montar `AdminApp.domains.users.urls.urls` en `DaventProject/urls.py` (`/register/`, `/user/`, `/profile/`, `/password_update/`).
2. Corregir `IsAnonimous.is_athenticated` (typo + falta `return True`).
3. Implementar dominio `locations` (provincias/ciudades) y `password-reset`.
