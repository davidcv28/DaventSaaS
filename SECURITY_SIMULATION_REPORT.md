# Reporte de simulación de ataque — SaaS DAVENT

**Fecha:** 2026-10-25  
**Alcance:** Backend Django + DRF (`AdminApp/`, `StoreApp/`, `SuscriptionApp/`, `DaventProject/`) y capa de seguridad definida en `AGENTS.md`.  
**Método:** revisión estática adversarial (código fuente) + ejecución de la suite de tests (`manage.py test`) + comandos de lint (`manage.py check`, `ruff check`).  
**Modalidad:** simulacro acotado y no destructivo. No se lanzaron exploits reales contra endpoints en ejecución ni se repitió ningún vector en bucle.

---

## 1. Resultado ejecutivo

| Métrica | Estado |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `ruff check` | ✅ All checks passed |
| Suite `manage.py test` | ✅ 230 tests, 0 fallos (~116s) |
| Auditoría ofensiva previa documentada | ✅ `SECURITY_AUDIT.md` — 3 rondas, 15 vectores, 3 issues reales remediados + 1 hardening + 10 falsos positivos |
| Hallazgos críticos abiertos de este simulacro | **Ninguno** |

Conclusión: los vectores de ataque más peligrosos (falsificación de webhook de pagos, IDOR de cobros, canje de cupón con débito activo, anti-replay, firma HMAC, tope de usos de cupón bajo carrera) ya están mitigados en el código. No se detectaron brechas críticas sin parche en esta revisión.


## 2. Áreas atacadas y resultado del simulacro

Cada área se revisó contra los vectores de la "Regla de los 5 intentos" de `AGENTS.md` (§Auditoría, punto 5) sin superar ese límite.

| # | Área | Vectores simulados | Resultado | Mitigación verificada |
|---|---|---|---|---|
| 1 | **Pagos / Webhook MP** | Replay de webhook, firma inválida/ausente, `payment_id` ajeno, monto alterado, doble `approved` sin doble rollup | ✅ Bloqueados | `_verify_mp_signature` con `hmac.compare_digest`, manifest `id;request-id;ts`, ventana de frescura (ts en seg/ms), dedup atómico `cache.add` TTL 600s; `CreatePaymentQuery` valida `external_reference` = suscripción propia y rechaza pagos ajenos; `ApplyPendingPlanQuery` reinicia `end_date` (nunca acumula) bajo `select_for_update` |
| 2 | **Suscripciones / Cupones** | Canje con débito MP vivo, cupón concurrente superando `max_uses`, plan pagado vigente como target, plan `is_trial` como target | ✅ Bloqueados | `RedeemCouponQuery`: `select_for_update()` en cupón + suscripción, rechaza si `preapproval_id` y no `cancelled_at`, rechaza plan pagado vigente, tope `max_uses` bajo lock, `is_trial` excluido de `plan_suscription` |
| 3 | **Autenticación / Sesión** | Brute-force login/refresh, `remember='false'` string truthy, robo de refresh por XSS | ✅ Bloqueados | `_remember_requested` parseo estricto; refresh en cookie `httpOnly` scopeada `/api/token/`; access solo en memoria; throttles `login`, `token_refresh`, `logout`; rotación + blacklist |
| 4 | **Reset de contraseña / Email** | Enumeración de correo, token con `last_login`, reenvío sin límite | ✅ Bloqueados | `password_reset` siempre 200 genérico + throttle 5/h por IP; `EmailVerificationTokenGenerator` sin `last_login`; `VerifyEmailResendView` throttle `email_verification`; reset/cambio blacklistean `OutstandingToken` |
| 5 | **Verificación celular (Firebase)** | Token de número ajeno, falta `FIREBASE_API_KEY`, cambio de celular sin reset | ✅ Bloqueados | `ConfirmPhoneVerificationQuery` valida `phoneNumber` de Identity Toolkit vs `profile.phone` tras `_national_phone`; 503 sin `FIREBASE_API_KEY`; `UpdateProfileQuery` resetea `phone_verified` al cambiar el número |
| 6 | **Tiendas públicas / Catálogo** | Claim de slug sin email verificado, IDOR de tienda ajena, catálogo con `Decimal('1e999')`, sort crudo por query param | ✅ Bloqueados | `email_verified` gate en `POST /api/stores/`; staff `listMine` con `?mine=1`; `_price_bound` parseo defensivo + clamp; `CATALOG_SORTS` whitelist (nunca `order_by` crudo) |
| 7 | **Formulario de contacto** | Captcha timing-compare, email-bombing sin throttle, honeypot ausente | ✅ Bloqueados | `hmac.compare_digest` en captcha, `TimestampSigner` firmado, throttle `store_contact` 10/h por IP, honeypot `website`, mínimo 3s desde captcha (`CAPTCHA_MIN_SECONDS`) |

## 3. Hallazgos por severidad

### Crítico / Alta — sin hallazgos abiertos
Los 3 issues de alta severidad de la auditoría anterior (firma del webhook sin ventana de frescura, unicidad case-sensitive de email, IDOR de cobros) ya están remediados. Este simulacro no reabrió ninguno.

### Medio — residuales documentados (no bloquean)
- **W-5 (webhook autorizado tardío tras canje de cupón):** si MP ejecutó un cobro antes de la baja del débito y su monto ≠ precio del plan nuevo, el `Payment` no se registra localmente; el dinero sí se cobró en MP y hay rastro en el panel de MP. Riesgo residual aceptado; reconciliación manual como mejora futura.
- Imágenes R2: la cuota de almacenamiento se fuerza contra `max_storage_mb` bajo `select_for_update`; TOCTOU previo ya cerrado.

### Bajo — sin hallazgos nuevos
Todos los bajos de la auditoría anterior (regex de planes, `IntegrityError`→400, `assign` ids no numéricos, captcha timing, reorden de galería, `min_price` desborde, 405 en content-reports) ya están corregidos.

## 4. Evidencia de código (mitigaciones clave)

- `AdminApp/domains/payments/views/viewset.py:52-94` — `_verify_mp_signature`: HMAC-SHA256, `compare_digest`, requiere `MP_WEBHOOK_SECRET` (salvo `DEBUG` + `MP_WEBHOOK_ALLOW_UNSIGNED`), ventana ts, dedup `WEBHOOK_DEDUP_SECONDS = 600`.
- `AdminApp/domains/payments/services/services.py:49-72` — `CreatePaymentQuery`: idempotencia por `external_reference`, rechazo si el pago pertenece a otra suscripción.
- `AdminApp/domains/suscriptions/services/services.py:21-67` — `RedeemCouponQuery`: `select_for_update` en cupón y suscripción, rechazo con `preapproval_id` y no `cancelled_at` (regresión C-01), tope `max_uses` bajo lock.
- `AdminApp/domains/users/views/auth_views.py:47-54` — `_remember_requested`: parseo estricto del flag `remember` (el string `'false'` no es truthy).
- `StoreApp/domains/stores/services/contact.py` — captcha firmado con `TimestampSigner`, comparación `hmac.compare_digest`, honeypot, throttle por IP.

## 5. Recomendaciones

1. **Suite de tests:** ✅ verificada post-reporte — `manage.py test` completó 230 tests con 0 fallos (~116s).
2. **Webhook MP en producción:** asegurar que `MP_WEBHOOK_SECRET` esté configurado en el `.env` real y `DEBUG=False`; `MP_WEBHOOK_ALLOW_UNSIGNED` solo en desarrollo. Habilitar eventos `subscription_*` en el panel de webhooks de MP apuntando a `/api/payments/webhook/`.
3. **Firebase SMS:** configurar `VITE_FIREBASE_*` y `FIREBASE_API_KEY`; recordar la cuota Spark (~10 SMS/día) y el dominio autorizado en Firebase Console.
4. **Seguimiento de cobros huérfanos:** registrar/alertar pagos de MP cuyo monto no coincida con el plan (reconciliación manual vía panel MP) — mejora futura, no crítico.
5. **Mantener `SECURITY_AUDIT.md` actualizado:** si se aplican cambios de seguridad, agregar el vector, veredicto y fix en la misma tabla.

## 6. Nota sobre el método

Este simulacro fue deliberadamente **acotado y no recursivo**: se revisó cada área una vez, con los vectores del protocolo de auditoría de `AGENTS.md`, respetando la "regla de los 5 intentos" (no se iteró indefinidamente sobre ningún vector). No se realizaron peticiones reales de pago, ni se forjaron webhooks contra un servidor en ejecución, ni se expusieron secretos del `.env` (que no se leyó ni se commitea).

