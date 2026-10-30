# REGLAS DE DESARROLLO FRONTEND — SaaS DAVENT
> Fuente de verdad para proximos prompts. Si un prompt contradice este archivo, se respeta este archivo y se avisa.

## 0. Stack congelado
- Vue 3.4 + Composition API `<script setup>`. Nada de Options API en codigo nuevo.
- Vite 5 (dev :5173, proxy `/api -> http://127.0.0.1:8000`).
- Vue Router 4 (`createWebHistory`). Rutas solo en `src/router/index.js`.
- Pinia 2. Stores en `src/stores/*.store.js` estilo Composition.
- Axios 1 solo via `src/api/http.js`. Prohibido `fetch` o `axios` suelto en vistas.
- CSS vanilla con tokens en `src/assets/styles.css`. Sin Tailwind/Bootstrap salvo decision explicita.
- ESM, `lang="es"`, 2 espacios, comillas simples, punto y coma.

## 1. Arquitectura de carpetas
```
frontend/
├── index.html / vite.config.js / .env.* / FRONTEND_RULES.md / README.md
└── src/
    ├── main.js (bootstrap pinia+router+styles, sin logica de negocio)
    ├── App.vue (shell con RouterView, sin fetch)
    ├── config/env.js (unico lugar que lee import.meta.env)
    ├── api/http.js (axios + interceptores JWT + refresh single-flight)
    ├── api/auth.api.js (login/register/me/password, adapta payloads)
    ├── api/locations.api.js (provinces/cities con fallback local)
    ├── api/billing.api.js (suscription-plans + suscriptions + marketing)
    ├── api/payments.api.js (payments + daily/monthly revenues + statusMeta)
    ├── api/invoices.api.js (invoices list + detail + formatDate para DateField)
    ├── api/stores.api.js (stores + customization + paletas STORE_ACCENTS/STORE_THEMES + validadores espejo)
    ├── stores/billing.store.js (planes, mi suscripción, subscribe/changePlan)
    ├── stores/payments.store.js (pagos, confirmar pago MP, rollups admin)
    ├── stores/invoices.store.js (facturas del usuario)
    ├── stores/store.store.js (mi tienda + saveCustomization)
    ├── stores/auth.store.js (unica fuente de sesion, localStorage)
    ├── router/index.js (rutas + guards requiresAuth/requiresGuest/requiresStaff + onboarding sin tienda)
    ├── validators/auth.validators.js (espejo de validadores Django)
    ├── composables/useFormErrors.js (mapea errores DRF a UI)
    ├── composables/useSlugCheck.js (check de slug con debounce)
    ├── directives/reveal.js (vReveal: revelado en scroll compartido por las páginas públicas)
    ├── components/ (AppInput, AppButton, AlertMessage, PasswordStrength, AuthLayout, DashLayout, LegalLayout, PlanCard, AppIcon, BrandLogo)
    ├── views/ (Login, Register, ForgotPassword, ResetPassword, Dashboard, Admin, Terms, Report, InvoicePrint, StoreClaim, StorePublicLayout, StorePublic, StoreCatalog)
    └── assets/styles.css (tokens + componentes)
```

## 2. Contrato API (Django DRF + SimpleJWT)
| Accion | Metodo + path | Body | Respuesta |
|---|---|---|---|
| Login | `POST /token/` | `{username, password}` | `{access, refresh}` |
| Refresh | `POST /token/refresh/` | `{refresh}` | `{access}` |
| Verify | `POST /token/verify/` | `{token}` | `200 {}` |
| Registro | `POST /register/` | ver `buildRegisterPayload` | `201 {Exito}` |
| Mi usuario | `GET /user/me/` + `GET /profile/me/` | `Bearer` | cuenta + perfil comercial combinados |
| Cambio pass | `POST /password_update/` | `{old_password,new_password,confirm_password}` | `200 {Exito}` |
| Planes | `GET /suscription-plans/` | público | `[{id,name,price}]` |
| Mi suscripción | `GET /suscriptions/` | `Bearer` | `[{id,plan_suscription,plan_name,plan_price,start_date,end_date,status}]` |
| Suscribirme | `POST /suscriptions/` | `{plan_suscription: <pk>}` | `201 {Exito}` (una por perfil) |
| Cambiar plan | `PUT /suscriptions/<pk>/` | `{plan_suscription: <pk>}` | `200 {Exito}` — deja el plan en `pending_plan`: se aplica recién cuando el cobro se acredita (nunca gratis) |
| Mis pagos | `GET /payments/` | `Bearer` | `[{id,suscription,plan_name,amount,currency,status,status_display,external_reference,paid_at,created_at}]` |
| Confirmar pago MP | `POST /payments/` | `{suscription:<pk>,payment_id:<int>}` | `201 {Exito}` (verifica monto vs plan en MP) |
| Mis facturas | `GET /invoices/` | `Bearer` | `[{id,comprobante,type,type_display,total,issued_at,plan_name,paid_at,currency,customer_name,document,type_document,tax_condition_display,address,city_name,province_name}]` |
| Detalle factura | `GET /invoices/<pk>/` | `Bearer` | mismo payload (404 si es de otro usuario) |
| Rollups admin | `GET /daily-revenues/` + `GET /monthly-revenues/` | `Bearer` solo staff (403 al resto) | listas de rollups |
| Denuncia contenido | `POST /content-reports/` | `{reporter_name,reporter_email,kind,reported_url,original_work,description,good_faith}` público (AllowAny) | `201 {Exito}` |
| Mi tienda | `GET /stores/` | `Bearer` | `[{id,slug,is_published,created_at,public_path,customization,storage:{used_bytes,max_mb,images,max_images}}]` (0..1) |
| Diseño web | `GET/PATCH /stores/customization/` | `Bearer {headline?,description?,theme?,accent?,whatsapp?,instagram?,show_location?}` | `200 {Exito,customization}` · 403 sin `has_customization` · sin `has_design_advanced` se descartan `name_font/name_font_size/accent` · sin `has_location_map` se descarta `show_location` |
| Tienda pública | `GET /stores/public/<slug>/` | público | `{slug,business_name,city_name,province_name,customization,location_address}` · 404 si pausada · `location_address` null sin `has_location_map` (Estándar+) o con el mapa apagado |
| Pedir reset | `POST /password-reset/` | `{email}` | `200 {Exito}` genérico (anti-enumeración) |
| Confirmar reset | `POST /password-reset/confirm/` | `{uid,token,new_password,confirm_password}` | `200 {Exito}`; `400 {token/new_password}` |
| Verificar email | `GET /verify-email/?uid&token` | backend marca y **redirige** a `/verificar-email?status=` | 302 |
| Reenviar verificación | `POST /verify-email/resend/` | Bearer | `200 {Exito}` (throttle 5/h por usuario) |
| Verificar celular | `POST /verify-phone/` | Bearer `{id_token}` — Firebase Phone Auth en el cliente (SMS + código → idToken) | `200 {Exito}` · 400 sin `profile.phone` / token inválido / número no coincide · 503 sin `FIREBASE_API_KEY` (throttle 5/h por usuario) |
| Estado celular | `GET /verify-phone/status/` | Bearer | `200 {phone_verified}` |

> Hallazgos senior: `DaventProject/urls.py` hoy monta `suscriptions` + `users` + `locations` + JWT.
> Registro `POST /register/` y selects `GET /provinces/`, `GET /cities/?province=<id>` son reales
> (AllowAny, paginados). `IsAnonimous` corregido (`is_authenticated` + `return True`).
> Si la API cae o da 404, locations usa fallback local de emergencia + aviso.

## 3. Autenticacion (reglas duras)
1. Tokens solo en `localStorage`: `davent.access`, `davent.refresh`.
2. `http.js` inyecta `Bearer` y hace refresh single-flight: 401 + refresh -> reintenta 1 vez. Si falla -> `logout()` + `/login?expired=1`.
3. Throttle login `5/min` -> vista deshabilita 60s tras `429`.
4. Store expone: `accessToken, refreshToken, isAuthenticated, user, status, fieldErrors, login(), register(), logout(), fetchMe(), initFromStorage()`.
5. Guards: `/dashboard` requiere auth; `/login /register /forgot-password /reset-password` requieren guest. `/verificar-email` es pública (el link del correo puede abrirse logueado o no — sin requiresGuest).
6. Recuperación real: `requestPasswordReset(email)`/`confirmPasswordReset({uid,token,new_password,confirm_password})` ya están cableadas a `/api/password-reset*/`. El link del correo llega como `/reset-password?uid&token` y la vista exige ambos. Email no verificado = banner + reenvío en Dashboard/`/bienvenida` (`auth.user.profile.email_verified`); el claim del slug da 403 en backend.

## 4. Formularios y validacion
- Espejo backend: username >=6, email solo gmail/hotmail/outlook/yahoo/live, password >=8 + minuscula + mayuscula + numero + especial, document DNI 7-8 / CUIT 11 con checksum y prefijos 20,23,24,27,30,33,34, business_name obligatorio si tax!=CF, phone `+54...`, ciudad debe pertenecer a provincia.
- Componentes controlados `<AppInput :error>` + `<AlertMessage>`. Errores DRF via `useFormErrors`.
- Registro en 3 pasos (Cuenta -> Fiscal -> Contacto). No avanzar con errores. Payload via `buildRegisterPayload` (type_document auto CF->DNI resto->CUIT). El paso 3 exige `accept_terms` obligatorio y el backend sella `terms_accepted/_at/_version` en el perfil.
- Password con medidor + toggle. Accesible con `aria-invalid`.

## 5. Estilo / UX
- Layout auth split: panel marca (gradiente indigo->violet) + card. Responsive <960px a 1 columna.
- Tokens CSS en `:root`. Estados `idle|loading|success|error`. Botones con spinner, nada de `alert()`. UI en es-AR.

## 6. Calidad y proximos prompts
- Vista nueva: ruta + guard + store-action + validadores + estados + manejo 401/429/404. Nada de HTTP en `.vue` fuera de `api/*.api.js`.
- No agregar dependencias sin justificar.
- Verificar endpoints en `DaventProject/urls.py` + `domains/*/urls/urls.py` + `viewset_config.py`. Si falta, fallback + aviso.
- Comandos: `npm install` -> `npm run dev` (5173). Backend en `127.0.0.1:8000`. CORS ya incluye `http://localhost:5173`.

