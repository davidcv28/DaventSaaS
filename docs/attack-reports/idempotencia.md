# Attack report — Idempotencia y operaciones reintentables (fuera del checkout)

Fecha: 2026-11-13. Entorno local (`manage.py runserver` :8000, SQLite + cache vivo).
Continuación de `checkout.md` — mismas tiendas (`davent` vendible), customer descartable
`idem-a@test.local` (pk 50) creado solo para la prueba, usuarios `idem-*`/`c1..c3` para canjes.
Método: requests reales (threads con barrier) + service calls concurrentes en `manage.py shell`.
Caveat de entorno: SQLite no honra `select_for_update` (no-op) y serializa escrituras —
en Postgres las ventanas de carrera son iguales o más anchas, nunca más chicas.

**Resultado global: mayormente bien blindado.** Dos carreras reales con evidencia:
reviews duplicadas por TOCTOU sin unique constraint, y refresh-token replay
concurrente que emite dos sesiones válidas.

## Tabla de hallazgos

| ID | Operación | Ataque | Esperado | Obtenido | Severidad | Ubicación |
|----|-----------|--------|----------|----------|-----------|-----------|
| IDM-01 | Reviews (POST opinión) | 2 POST paralelos misma review, mismo comprador (barrier-synced) | 1×201 + 1×409 | **2×201 y 2 filas** `ProductReview` (pk 4 y 5, mismo customer+producto, 5 ms de diferencia). La dedupe es `exists()` → `create()` sin unique constraint en DB: TOCTOU puro. Secuencial (el segundo request sí ve la fila) → 409 correcto. Rating inflable por doble-click/race del front (el front no manda idempotency key ni hay constraint que lo impida). | **media** | `StoreApp/domains/stores/views/viewset.py:1332-1346` (check-then-create); `StoreApp/domains/catalog/models/models.py:255-296` — `Meta.constraints` solo trae `ck_review_vote_or_text`, falta `UniqueConstraint(product, customer)` |
| IDM-02 | Refresh token replay | 2 POST `/api/token/refresh/` paralelos con el MISMO refresh (body, path API sin CSRF) | 1×200 + 1×401 (token de un solo uso) | **[200,200] en 3 de 6 corridas**: ambos rotan y devuelven access+refresh válidos — un refresh robado usado en paralelo al legítimo NO quema el token (SimpleJWT hace verify → blacklist sin lock sobre el jti). En serie el replay sí da 401 (blacklist funciona). Ventana corta pero real: mitiga el "stolen token detection" que el rotation promete. | **media** | `AdminApp/domains/users/views/auth_views.py:292-331` (`CookieTokenRefreshView` hereda el comportamiento de SimpleJWT `TokenRefreshSerializer.validate` + `RefreshToken.blacklist` — check-then-insert no atómico) |
| IDM-03 | Cart DELETE retry | DELETE `/items/<id>/` ×2 (serie y paralelo) | 404 tras borrar o 200 idempotente | 200 + **400** `{"item":"El item no está en tu carrito."}` (serie) y [400,200] paralelo. No es error de seguridad (el recurso ya no existe), pero un retry de red del front ve un "error" en vez de éxito idempotente — si el front lo muestra como falla, UX engañosa. Sin idempotency key necesaria, pero convendría 200/204 idempotente o 404 consistente. | **baja** | `StoreApp/domains/cart/services/cart.py:165-168` (`remove_item` raise `ValidationError`); `views/views.py:139-141` |
| IDM-04 | Contacto | POST contact ×2 mismo challenge (paralelo); luego mismo contenido con captcha nuevo | 1 mail por envío; idealmente dedupe por cliente+hash | Mismo challenge → [400,200] (nonce quemado atómico, 1 mail). **Captcha nuevo + contenido idéntico → 200 y segundo mail en cola**: no hay dedupe por hash/tiempo ni idempotency key — un doble-submit lento del usuario (o 2 posts desde 2 captchas) manda N mails al vendedor. Mitigado por captcha+throttle 10/h; el doble-click rápido queda cubierto por el nonce. | **baja** | `StoreApp/domains/stores/views/viewset.py:1248-1272`; `services/contact.py:192-201` (`send_contact_message` sin dedupe); `AdminApp/domains/users/tasks.py:58-63` |
| IDM-05 | Social login (alta) | 2 `SocialLoginQuery` concurrentes mismo email | 1 alta + 1 login | Cubierto: `IntegrityError` → re-query por email y entra como login (`social.py:124-130`). **Edge no cubierto**: 2 altas concurrentes con emails DISTINTOS pero mismo local-part/username base (ej. `juan@a.com` y `juan@b.com`): ambos pasan `_social_username` con el mismo candidato libre → el perdedor recibe `IntegrityError`, busca por SU email, `user=None` → `raise` pelado → 500. | **baja** | `AdminApp/domains/users/services/social.py:71-82` (`_social_username` check-then-create), `124-130` (fallback solo contempla carrera por email) |
| IDM-06 | Profile PATCH concurrente | 2 cambios de perfil en paralelo | Last-write-wins o merge | Lost update clásico (read-modify-write del serializer, sin lock ni ETag): dos pestañas editan, gana la última — comportamiento estándar aceptable, sin detección de conflicto. | **info** | `AdminApp/domains/users/views/viewset.py` (`UserProfileViewSet`, PATCH convencional) |

## Ataques que NO funcionaron (verificado con evidencia)

| ID | Operación | Ataque | Resultado |
|----|-----------|--------|-----------|
| IDM-P01 | Cart add ×2 | POST `/items/` mismo `{product_id, qty}` ×2 paralelo | [200,200]; una sola línea con `qty=2` (upsert — qty se REEMPLAZA, no se suma). Retry secuencial → mismo resultado. `cart.py:131-146` |
| IDM-P02 | Cart PATCH qty | PATCH `qty=5` ×2 paralelo | [200,200]; línea queda en 5. Idempotente por naturaleza. |
| IDM-P03 | Proof upload ×2 | POST `/proof/` mismo archivo ×2 paralelo (barrier) | **1×201 + 1×400** `"ya tiene un comprobante"`. First-write-wins con re-check bajo `select_for_update`; el perdedor borra su objeto R2 en el `except` (`_delete_object`). Cuota consumida UNA vez: `storage_used_bytes` 693448 → 693746 (+298 = un solo WebP). `orders/views/public.py:227-277` |
| IDM-P04 | Register ×2 | POST `/api/register/` mismo email ×2 paralelo | 1×201 + 1×400 `"Ya existe una cuenta con esos datos."` — el `IntegrityError` se traduce a 400, sin user duplicado. `users/services/services.py:171-175` |
| IDM-P05 | Cupón canje | `RedeemCouponQuery` ×2 paralelo mismo perfil; y max_uses=1 con 2 perfiles | 1×OK + 1×400 `"Ya usaste este cupón."` / `"llegó a su límite de usos."`. `select_for_update` sobre la fila del cupón + `UniqueCouponRedemptionConstraint(coupon,user)`: 1 sola redención en ambos casos. `suscriptions/services/services.py:36-72`, `models/models.py:169-174` |
| IDM-P06 | Webhook MP re-entrega | `StoreMpWebhookQuery` con mismo `payment_id` ×2 (MP API mockeado) | 1 fila `MpPayment` (unique `mp_payment_id` + `IntegrityError`→re-read), pedido `PENDING_PAYMENT→PACKING` una vez, eventos `paid`+`packing` sin duplicar. Re-entregas no producen efectos dobles. `storepayments/services/webhook.py:99-144,202-316` |
| IDM-P07 | Notificaciones | POST `/notifications/read/` `{all:true}` y `{id}` ×2 | 200,200 ambos — `update(read_at=now)` filtrado por `read_at__isnull` es inherentemente idempotente. `notifications/views/viewset.py:68-77` |
| IDM-P08 | Contacto captcha replay | Mismo challenge_id + respuesta correcta ×2 paralelo | [400,200] — `cache_add_strict` atómico sobre el nonce: un solo ganador. `services/contact.py:118-121` |

## Notas

- **Sin idempotency key donde convendría** (doble-click del usuario): `POST reviews`
  (no acepta key ni hay constraint — IDM-01) y `POST contact` (sin dedupe de contenido —
  IDM-04, mitigado por captcha de un solo uso). El checkout sí soporta `idempotency_key`
  (ver `checkout.md`, funciona); extender el patrón a estos dos endpoints es barato.
- Fix sugerido para IDM-01: `UniqueConstraint(fields=['product','customer'])` en
  `ProductReview` + capturar `IntegrityError` → 409 (mismo patrón que el coupon
  `UniqueCouponRedemptionConstraint`). El `exists()` actual puede quedarse como fast-path.
- Fix sugerido para IDM-02: es un TOCTOU upstream de SimpleJWT (blacklist check e
  insert no atómicos). Opciones: `select_for_update` sobre el `OutstandingToken` del
  jti antes de validar la blacklist, o aceptar el riesgo (la ventana es ms; el access
  robado igual vive 30 min). El 401 serial funciona — solo falla la ejecución
  simultánea exacta.
- El `refresh` usado en replay queda blacklistado tras la carrera (la blacklist se
  llena igual): el daño es una ventana de dos tokens válidos, no replay infinito.
- Order events `/orders/<token>/events/` es GET — re-entrega trivialmente segura.
- Logout (`/api/token/logout/`) es idempotente por diseño (200 sin cookie).

## Repro

Scripts (scratch, fuera de git): `pwtmp/idem_http.py` (cart/reviews/contact/register/
refresh/proof vía HTTP real), `pwtmp/idem_services.py` (coupon + webhook + constraints
vía service calls con threads + barrier), `pwtmp/idem_creds.json` (tokens minteados),
`pwtmp/idem_http_out.json` (salida cruda).
