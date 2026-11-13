# Attack Report — Autenticación y cuenta del comprador

Fecha: 2026-11-13 · Alcance: `/api/customer-auth/*`, `/api/customer/*`, seguimiento público de pedidos, StoreAuthForm/Modal/View, `/cuenta`. Backend local `:8000`, front `:5173`. Cuentas de prueba: `atk-a@test.com` (id 17), `atk-b@test.com` (id 18) sobre tienda `mt-qa`.

**Resultado general: el área está notablemente endurecida.** No se encontraron 500s, IDOR, bypass de auth ni XSS ejecutable. Los hallazgos son de enumeración y post-explotación de bajo impacto.

## Hallazgos confirmados

| ID | Superficie | Ataque | Esperado | Obtenido | Severidad | Archivo:línea |
|----|-----------|--------|----------|----------|-----------|---------------|
| AC-01 | POST `/api/customer-auth/password-reset/` | Timing de enumeración: medir `time_total` para email existente vs inexistente | Respuesta uniforme (send mail async o delay dummy) | **Existente ≈ 1.8–2.5 s, inexistente ≈ 0.27 s** (el mail se encola/emite sincrónicamente vía Celery eager/smtp). Enumeración de clientes registrados pese al mensaje genérico | **Media** | `services/customers.py` `RequestCustomerPasswordResetQuery` (~l.240+) / `tasks.py` — falta dummy-delay o cola realmente asíncrona |
| AC-02 | POST `/api/customer-auth/register/` | Email duplicado (`ATK-A@test.com` vs `atk-a@test.com`) | Respuesta indistinguible (p. ej. "revisá tu correo") o al menos mismo timing | **400 `{"email":["Ya existe una cuenta con esos datos."]}`** — el comentario del serializer dice "anti-enumeración/mensaje genérico" pero el texto revela explícitamente que la cuenta existe. El timing existe/nuevo era similar (~0.21 s) por el hash temprano, pero el mensaje lo delata igual | Media-baja (mitigado: throttle `register` 10/h) | `serializers.py:121-124` |
| AC-03 | POST `/api/customer-auth/register/` | Email homógrafo Unicode: `аtk-a@test.com` (а cirílica U+0430) | Rechazo o normalización NFKC/confusable-detection | **200 + sesión emitida** — se creó customer con email visualmente idéntico al de la víctima. En el panel del vendedor (CustomersPanel/OrdersPanel, snapshot `buyer_name`) los dos clientes se ven iguales → suplantación visual / fraude ante el vendedor | Media | `serializers.py:114` (EmailField acepta EAI sin chequeo de confusables); `services/customers.py:normalize_email` |
| AC-04 | POST `/api/customer-auth/register/` | Plus-addressing `atk-a+tag@test.com` | (política) | 200 — cuenta distinta que recibe correo en el mismo buzón. Permite cuentas ilimitadas por casilla (abuso de cupones/beneficios por cuenta nueva, bypass de límites por comprador) | Baja | `services/customers.py:normalize_email` (no strip de `+tag`) |
| AC-05 | PATCH `/api/customer-auth/me/` + POST `/api/customer/addresses/` | XSS almacenado: `first_name="<img src=x onerror=alert(1)>"`, `last_name="<script>…"`, `label`/`line1`/`city` con `<svg/onload>` | Sanitización o escape en todos los sinks | **Backend persiste el payload crudo y lo devuelve.** No ejecuta en `/cuenta` ni en el panel (Vue `{{ }}` + comentarios "jamás v-html" en paneles) — riesgo residual si aparece un `v-html`/email `|safe`/export PDF que renderice estos campos | Baja (almacenado, sin sink activo hoy) | `serializers.py:91` (whitelist sin sanitizar), `profile_views.py:48` |
| AC-06 | Sesión — logout | Reusar `access` JWT tras `POST /logout/` | Access revocado | **200 en `/me` hasta su exp (≤30 min).** Diseño documentado (access stateless, lifetime recortado de 12 h→30 min); ventana residual para un token filtrado post-logout | Baja | `tokens.py:29` (CUSTOMER_ACCESS_LIFETIME), `auth_views.py:333` (logout solo blacklistea refresh) |
| AC-07 | GET `/api/customer/notifications/stream/` | Ticket SSE emitido antes de un password-reset | Ticket ligado a `tokens_valid_after` | El ticket firmado solo chequea `is_active`, no `customer_session_valid` — una sesión revocada conserva el stream ≤120 s (TTL del ticket) | Baja | `notification_views.py:162-169` |
| AC-08 | `/{slug}/cuenta` (front) | Acceso directo sin sesión | Redirect a login | La ruta `store-account` no tiene `meta.requiresAuth` — devuelve 200 y la vista resuelve auth client-side (los datos sí exigen Bearer → 401). Sin fuga de datos; posible flash/estado raro del modal | Info | `frontend/src/router/index.js:124-129` |

## Ataques resistidos (evidencia negativa)

| Superficie | Ataque | Resultado |
|-----------|--------|-----------|
| IDOR direcciones | GET/PATCH/DELETE `/api/customer/addresses/7/` (ajena, token de B) | **404** en los tres verbos — queryset scopeado (`profile_views.py:83-84`); PUT rechazado 405 (`http_method_names`) |
| IDOR perfil | PATCH `/me` con `{"id":18,"email":…,"is_active":false,"email_verified":true}` | Campos ignorados (whitelist `CustomerProfileUpdateSerializer`); email/is_active/email_verified inalterados |
| IDOR notificaciones | POST `/notifications/read/` con ids ajenos | 404 sin filtrar existencia (`notification_views.py:105-107`) |
| IDOR checkout | `address_id` de otra customer | Filtrado por `customer=` → 400 "no existe o no es tuya" (`views/public.py:97`) |
| JWT | Token tampered, token DAVENT (`token_type=access`) en endpoints customer y viceversa | 401 / 404 — separación por `token_type` + claim `customer_id` (`authentication.py:53-73`) |
| Refresh/CSRF | Refresh por cookie sin `X-CSRFToken`; replay del refresh rotado; logout sin CSRF | 403 / **401** (blacklist + rotación, fail-closed `auth_views.py:317-321`) / 403 |
| Password reset | Confirm con uid/token ajeno, replay del token real | 400 genérico; tras reset: access previo → **401** (`tokens_valid_after`) y token → inválido (PasswordResetTokenGenerator) |
| Login | Timing exists/no-exists | Homogeneizado con dummy hash (`customers.py:136-139`); respuesta genérica 401 |
| Social login | Credential basura, slug inexistente, aud/iss/email_verified | Verificación server-side contra tokeninfo: aud == client_id de ESA tienda (BYO o central), iss Google, exp, `email_verified=true` (`google.py:90-103`); anti-pre-hijacking: invalida password usable + sella tokens (`google.py:160-165`) |
| Seguimiento pedido | Brute-force `/stores/public/<slug>/orders/<token>/` | Token aleatorio 64 chars único + scoped a tienda → 404 |
| Register | Email malformado, password <8/común/numérica, `store_slug` inexistente, mass-assignment (`is_active`, `email_verified`) | 400 con validación correcta; campos extra ignorados; duplicado por case cubierto por `normalize_email`+`iexact` |
| Origin check | POST de emisión de sesión cross-origin | `_session_origin_allowed` rechaza orígenes no confiables (`auth_views.py:110-140`) |
| Throttling | Spam register/resend | `register` 10/h (confirmado 429), `email_verification` 5/h, `password_reset` 10/h, `logout` 30/h, confirm 30/h |

## Recomendaciones

1. **AC-01**: hacer el envío del mail de reset realmente asíncrono (o aplicar un sleep dummy constante ~2 s cuando el email no existe) para eliminar el oráculo de timing.
2. **AC-02**: cambiar el mensaje por uno ambiguo ("Si el correo está disponible te enviamos la verificación") o al menos documentar que la enumeración por registro se acepta a cambio de UX.
3. **AC-03**: rechazar o normalizar confusables en `normalize_email` (`unicodedata.normalize('NFKC')` + blocklist de rangos no-latinos en la parte local) y/o mostrar el email en el panel del vendedor en vez de solo el nombre.
4. **AC-05**: defensa en profundidad — strip o escape de `<>&"'` en first_name/last_name/label de direcciones, y `bleach`/escape explícito en cualquier mail/PDF futuro que use `buyer_name`.
5. **AC-07**: incluir `iat` o versión de sesión en el ticket SSE y re-chequear `customer_session_valid` al abrir el stream.
6. **AC-08**: agregar `meta.requiresCustomerAuth` (o guard equivalente) a `store-account` para evitar render de la vista sin sesión.
