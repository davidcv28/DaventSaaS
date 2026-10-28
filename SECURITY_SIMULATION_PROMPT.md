# Prompt — Simulación de ataques (cuentas cliente · pagos · administrador)

> Pegar el bloque de abajo como prompt único a un agente con acceso al repo.
> Alcance: backend Django + DRF de SaaS DAVENT (`AdminApp/`, `StoreApp/`, `SuscriptionApp/`, `DaventProject/`) y el contrato que consume el frontend.
> Complementa — no reemplaza — `SECURITY_AUDIT.md`, `SECURITY_RUNBOOK.md` y `SECURITY_SIMULATION_REPORT.md`.

---

## BLOQUE DEL PROMPT (copiar desde aquí)

Actuás como red team defensivo sobre el repo SaaS DAVENT. Tu tarea es **simular ataques** contra tres superficies — **cuentas de clientes**, **sistema de pagos** y **panel administrador** —, **corregir toda fuga de información sensible** (de clientes y de administradores) y **cerrar el acceso a los pagos de todas las formas razonables**. Todo bajo un **presupuesto cerrado de intentos** para no caer en bucles.

### 0. Reglas de ejecución (obligatorias, se leen antes de tocar nada)

1. **No destructivo.** Nada de `flush`, `drop`, borrado de filas, `rm -rf`, ni llamadas reales a Mercado Pago / Google / R2. Los ataques se ejecutan contra la base de test (`manage.py test`) o con `runserver` + datos sembrados descartables.
2. **No repetir vectores ya cubiertos.** Antes de atacar, leer el índice de `SECURITY_AUDIT.md` y `SECURITY_SIMULATION_REPORT.md` (solo el índice/tablas, no los archivos completos). Si un vector ya está mitigado y su test existe en `users/tests.py`, `stores/tests.py` o `payments/tests.py`, **no se re-ataca**: se marca `YA CUBIERTO` citando el test.
3. **Un cambio por vez.** Cada mitigación es un parche mínimo y aislado; se re-testea **solo el vector atacado** antes de pasar al siguiente. Prohibido refactorizar de paso.
4. **Tope de intentos por vector: 5.** Si al 5º intento el vector sigue abierto: **parar ese vector**, documentarlo como `ABIERTO` con evidencia, y seguir con el resto. No se itera más.
5. **Tope global: 2 rondas por superficie y 1 sola corrida completa de `manage.py test` al final** (más las corridas parciales del área tocada). Si se agota el tope, se entrega el reporte con lo hecho y lo pendiente.
6. **Cero findings críticos/altos abiertos ⇒ no hay push.** Si queda un crítico/alto abierto, se commitea el reporte pero **no se pushea la mitigación a medias**; se escala (ver §7).
7. **Verificación barata.** `manage.py check` + `ruff check` + test del área tocada, con salida truncada (`| tail -n 40`, `2>&1 | grep -iE "error|fail"`). Nada de volcar logs enteros.
8. **Commits.** Al cerrar cada fase aplicada: `git commit` + `git push` a `main`, mensaje corto `fix(security): …` / `test(security): …`. Nunca commitear `.env`, `venv/`, `node_modules/`, `dist/`.

### 1. Fase A — Reconocimiento acotado (máx. 1 pasada)

Mapear, sin leer archivos completos:

- Endpoints y permisos efectivos: `DaventProject/urls.py`, `*/urls/urls.py`, `*/views/viewset_config.py`, `*/views/viewset_base.py`.
- Config de seguridad: `settings.py` (`DEBUG`, `ALLOWED_HOSTS`, `ADMIN_URL`, `CORS_*`, `CSRF_*`, `REST_FRAMEWORK` throttles, `SECURE_*`, `PASSWORD_RESET_TIMEOUT`, `SIMPLE_JWT`), `payments/checks.py`, `payments/views/viewset.py` (`_verify_mp_signature`, `webhook`), `users/services/social.py`, `users/services/*` (mails, tokens).
- Serializers que devuelven datos de personas: `users`, `payments`, `invoices`, `suscriptions` (cupones), `chat`, `stores`.
- Salida: **matriz endpoint × rol** (`anónimo` / `cliente` / `staff` / `admin`) con la respuesta esperada (200/401/403/404/429). Es el contrato que la Fase B intenta romper.

### 2. Fase B — Ataques por superficie

Para cada vector: `ID · precondición · request exacta (método, ruta, headers, body) · esperado · observado · veredicto (BLOQUEADO / ABIERTO / YA CUBIERTO) · evidencia (status + campo filtrado, sin volcar tokens reales)`.

#### B1. Cuentas de clientes

| # | Vector | Esperado |
|---|---|---|
| A-01 | Enumeración de cuentas: `POST /api/password-reset/` con email existente vs inexistente vs malformado (incluye timing y cuerpo de respuesta) | 200 genérico idéntico, sin `detail` variable |
| A-02 | Enumeración por registro: `POST /api/register/` con username/email ya usados y con email nuevo | Mismo formato, sin revelar cuál campo existe; throttle `register` 10/h |
| A-03 | Enumeración por login: `POST /api/token/` usuario válido/clave mala vs usuario inexistente | Mismo 401 genérico, mismo timing, throttle `login` |
| A-04 | Fuerza bruta de reset: 6+ `POST /api/password-reset/` seguidos | 429 desde el 6º (`password_reset` 5/h) |
| A-05 | Token de reset manipulado/expirado/reutilizado (`uid` ajeno, `token` truncado, token ya usado) | 400 sin revelar si el usuario existe |
| A-06 | Reset con contraseña débil (igual al username, < 8, común) | 400 por `AUTH_PASSWORD_VALIDATORS` en reset, no solo en alta |
| A-07 | IDOR de perfil: `GET/PATCH /api/profile/<id_ajeno>/`, `/api/user/<id_ajeno>/` | 403/404; el cliente solo ve lo propio |
| A-08 | Escalada por body: `PATCH /api/profile/` con `is_staff`, `is_superuser`, `email_verified`, `suscription`, `plan` | Campos ignorados/400, nunca aplicados |
| A-09 | Secuestro de sesión: refresh sin cookie, cookie `davent_refresh` de otro usuario, reuso de refresh rotado, `remember` como string `"false"` | 401 + blacklist del rotado; `remember` parseado estricto |
| A-10 | Fixation/CSRF: `POST` con Bearer válido pero sin `davent_csrf` en endpoints con cookie auth | 403 CSRF |
| A-11 | Google login: `credential` con `aud` ajeno, email sin verificar, token expirado, body gigante | 401/503; nunca confía en el email del cliente |
| A-12 | Verificación de email: token de otro usuario, token reusado, `resend` en bucle | 400/429; token autoinvalidable |
| A-13 | Fuga en respuestas de error: 500 con traza, `detail` con SQL, rutas internas o nombres de tabla, validaciones que reflejan el valor enviado | Error opaco, sin `DEBUG` |
| A-14 | Fuga de datos de terceros en endpoints públicos (`/api/stores/public/<slug>/`, contacto, catálogo): emails, teléfonos, DNI, dirección, IDs internos | Solo campos públicos del negocio |

#### B2. Pagos (superficie más sensible — atacar primero)

| # | Vector | Esperado |
|---|---|---|
| P-01 | `POST /api/payments/webhook/` sin firma / firma inválida / firma válida de otro `data.id` | 401; `hmac.compare_digest` sobre manifest `id;request-id;ts` |
| P-02 | Replay del mismo webhook (mismo `request-id` y `payment_id`) | 200 idempotente, **sin** doble rollup ni doble factura (dedup atómico) |
| P-03 | Webhook con `ts` fuera de ventana / futuro / ms vs s | 401 |
| P-04 | Webhook con `external_reference` de otra suscripción / inexistente / `payment_id` ajeno | 400/404, no aplica plan |
| P-05 | Webhook con monto alterado / moneda distinta a la del plan | Rechazo; el monto se valida contra el plan |
| P-06 | Webhook sin secret configurado en prod (`MP_WEBHOOK_SECRET` vacío) | Falla cerrado fuera de `DEBUG` |
| P-07 | `GET /api/payments/` como anónimo / cliente A | 401 / solo pagos propios (sin `payment_id` de otros) |
| P-08 | `GET /api/payments/<id_ajeno>/` y `POST /api/payments/<id_ajeno>/approve/` | 403/404 |
| P-09 | `PATCH /api/payments/<id>/` con `status`, `amount`, `user`, `suscription` | Rechazado; el cliente no escribe estado de pago |
| P-10 | `GET /api/daily-revenues/`, `/api/monthly-revenues/`, `/api/payments/admin-summary/` como cliente / staff sin `is_superuser` | 403 (solo admin) |
| P-11 | `POST /api/payments/checkout/` y `/subscription/` sin datos fiscales | 400 `{billing_required: [...]}` **antes** de tocar MP |
| P-12 | `checkout`/`subscription` con plan `is_trial`, plan inexistente, plan de otro país, body con `price`/`amount` propio | Rechazo; el precio sale del plan, nunca del cliente |
| P-13 | `cancel-renewal`/`sync` sobre preapproval ajeno o sin débito activo | 403/400, idempotente |
| P-14 | Canje de cupón: código inválido/vencido/agotado/ya usado; con débito MP vivo; con plan pago vigente; dos canjes concurrentes en `max_uses=1` | 400/409; lock `select_for_update`; sin superar `max_uses` |
| P-15 | Fuga de datos de pago: `payment_id`, `preapproval_id`, `external_reference`, tokens MP, últimos dígitos de tarjeta, email del pagador en cualquier respuesta **pública** o de otro usuario | Nunca presentes |
| P-16 | Fuga por logs/errores: `logger.*` con payload de MP, `print`, excepción con `preference_id`, respuesta 500 con cuerpo de MP | Sin PII ni secretos en logs |
| P-17 | Enumeración de facturas: `GET /api/invoices/`, `/api/invoices/<id_ajeno>/` como cliente | 403 (solo admin) o solo propias si aplica |
| P-18 | Fuerza bruta / scraping: 200 requests a `payments`, `checkout`, `coupon_redeem` | 429 por scope (`coupon_redeem` 10/h, `public_read`, default) |

#### B3. Panel administrador

| # | Vector | Esperado |
|---|---|---|
| D-01 | Acceso a `/api/coupons/`, `/api/invoices/`, `/api/daily-revenues/`, `/api/monthly-revenues/`, `/api/payments/admin-summary/`, `/api/legal/` como cliente autenticado | 403 en **todas** las acciones (list, retrieve, create, update, partial_update) |
| D-02 | `PATCH /api/user/<id>/` como staff sin superuser si el diseño exige admin | 403 según política; documentar la política real |
| D-03 | Elevación por body en endpoints admin (`is_superuser`, `is_staff`, `password`, `groups`) | Ignorados/rechazados |
| D-04 | Acceso al Django admin (`settings.ADMIN_URL`) y `/api-auth/login/`, `/api/docs/swagger/`, `/api/docs/redoc/`, `/api/schema/` en prod (`DEBUG=False`) | 404/403 o cerrado; nunca público |
| D-05 | Fuga en listados admin: DNI, dirección, teléfono, email, CBU/tarjeta, `payment_id` en respuestas que el frontend admin no necesita | Minimización de campos por serializer |
| D-06 | Fuga cruzada en chat de soporte: cliente leyendo `?thread=<ajeno>`, staff sin flag, adjunto de otro hilo | 403/404; el cliente siempre lee el propio |
| D-07 | Secuestro de cuenta admin: reset de contraseña de un admin (¿manda mail? ¿expone rol?), enumeración de admins | Sin revelar rol ni existencia |
| D-08 | Fuerza bruta sobre admin con sesión de staff comprometida / CSRF en acciones admin | 403 CSRF; throttles activos |

### 3. Fase C — Correcciones (una por vez, con re-test)

Orden obligatorio: **crítico → alto → medio → bajo**, y dentro de igual severidad, **pagos antes que el resto**.

Tipos de fix admitidos:
- **Fuga de información**: minimizar serializer (campos explícitos, `read_only`, `write_only` para secretos), mensajes de error opacos y uniformes, `no-store` en respuestas sensibles, quitar PII de logs, cerrar `schema/docs/api-auth` fuera de `DEBUG`.
- **Acceso a pagos**: default-deny en `viewset_config` (toda acción declara `permissions` explícitas), `IsAdminUser` donde corresponde, filtro por `user=request.user` en querysets de cliente, `get_object` acotado al dueño, validación de estado/monto server-side, `select_for_update` en transiciones, idempotencia por `request-id`.
- **Cuentas**: throttles por scope en cada endpoint sensible, respuestas genéricas anti-enumeración, tokens de un solo uso, blacklist de sesiones en cambios de credencial.

Cada fix lleva **test de regresión** en el archivo del dominio (`payments/tests.py`, `users/tests.py`, `stores/tests.py`), con el mismo request del vector y el status esperado. Sin test, el fix no cuenta como cerrado.

### 4. Fase D — Blindaje de pagos "de todas las formas posibles"

Además de lo que ya exista, verificar y dejar implementado:

1. **Matriz de permisos por acción** en `payments/views/viewset_config.py`: `list`, `retrieve`, `create`, `update`, `partial_update`, `approve`, `webhook`, `checkout`, `subscription`, `cancel-renewal`, `sync`, `admin-summary` — todas con permiso explícito, ninguna cayendo en un default permisivo.
2. **Test de matriz**: un test que recorra esas acciones y afirme `401` anónimo y `403` cliente (salvo las que son de cliente, que afirman solo-lo-propio).
3. **Objeto ≠ dueño** en cada `retrieve/update/approve`: el queryset del cliente está acotado a `user=request.user`.
4. **Sin escritura de estado desde el cliente**: `status`, `amount`, `payment_id`, `external_reference`, `suscription`, `user` son `read_only` en el serializer de cliente.
5. **Webhook**: firma obligatoria fuera de `DEBUG`, ventana de frescura, dedup por `request-id`, `external_reference` propia, monto = plan, transición de estado bajo lock y sin doble factura.
6. **Rollups y reportes**: solo admin; sin `payment_id` ni PII en el payload.
7. **Cupones**: lock por cupón, tope `max_uses`, rechazo con débito vivo y con plan pago vigente, `is_trial` fuera del queryset.
8. **Ruido y enumeración**: throttles dedicados en `checkout`, `subscription`, `coupon_redeem` y `webhook`; respuestas uniformes.
9. **Frontend**: ningún endpoint de pagos se llama desde rutas públicas; los flags (`billingRequired`, `has_*`) no exponen ids de MP; nada de `payment_id` en `localStorage` ni en URLs.
10. **Superficie**: `ADMIN_URL` no obvia, `DEBUG=False` en prod, `schema/docs` cerrados, `ALLOWED_HOSTS`/`CORS` sin comodines.

### 5. Fase E — Verificación final (una sola vez)

```
venv/Scripts/python.exe manage.py check
ruff check .
venv/Scripts/python.exe manage.py test payments users stores   # truncado
```
Luego revisar `git diff --stat` para confirmar que no se tocó nada fuera del alcance.

### 6. Entregable

Crear/actualizar `SECURITY_SIMULATION_REPORT.md` (solo la sección nueva, con fecha) con:

1. **Resumen ejecutivo**: vectores simulados / bloqueados / abiertos / ya cubiertos, y si hubo que frenar por tope de intentos.
2. **Tabla de hallazgos**: `ID · superficie · severidad · veredicto · evidencia · fix aplicado · test de regresión · estado`.
3. **Fugas de información cerradas**: qué campo, en qué endpoint, en qué rol, y cómo se cerró.
4. **Blindaje de pagos**: matriz de permisos final + tests que la sostienen.
5. **Pendientes y riesgo residual**: lo que quedó `ABIERTO` o `NO SIMULADO` (con motivo: sin entorno, requiere MP real, requiere prod).
6. **Escalamiento** (§7) si corresponde.

Formato de la tabla, sin ambigüedad:

| ID | Superficie | Severidad | Veredicto | Evidencia | Fix | Test | Estado |
|---|---|---|---|---|---|---|---|
| P-05 | Pagos | Alta | ABIERTO→CERRADO | 200 con monto 1 en webhook | validación monto vs plan | `test_webhook_amount_mismatch` | ✅ |

### 7. Escalamiento (obligatorio, corta el bucle)

Si un vector sigue `ABIERTO` al 5º intento, o si una mitigación exige cambiar infra/secrets/dependencias que no controlás: **detener ese vector**, escribir en el reporte `vector explotado · evidencia · intentos realizados (1..5) · por qué falló cada uno · riesgo residual · 2 alternativas concretas`, y **pedir decisión al administrador**. No se pushea una mitigación a medias ni se sigue iterando sin respuesta.

### 8. Criterio de terminación (definition of done)

- [ ] Matriz endpoint × rol completa y contrastada contra el código.
- [ ] Todos los vectores de B1/B2/B3 con veredicto explícito.
- [ ] 0 críticos/altos abiertos; medios/bajos documentados con riesgo residual.
- [ ] Cada fix con test de regresión pasando.
- [ ] `manage.py check` + `ruff check` limpios; suite del área tocada en verde.
- [ ] Reporte actualizado y commiteado; push solo si no hay crítico/alto abierto.
- [ ] Ningún vector repetido más de 5 veces; ninguna ronda extra sin justificación escrita.

## FIN DEL BLOQUE DEL PROMPT

---

### Notas de uso (para el humano)

- **Dónde vive:** `SECURITY_SIMULATION_PROMPT.md` (raíz, junto a `SECURITY_AUDIT.md` y `SECURITY_SIMULATION_REPORT.md`).
- **Cómo acotar el costo:** si solo querés una pasada rápida, pedí `Fase B2 + Fase D` (pagos) — es la superficie de mayor riesgo y la de menor cantidad de vectores.
- **Anti-bucle en una línea:** 5 intentos por vector, 2 rondas por superficie, 1 suite completa, y al tope se documenta y se escala — nunca se itera "hasta que salga".
- **Qué NO hace este prompt:** no lanza exploits reales contra producción, no llama a Mercado Pago ni a Google, no borra datos, no modifica políticas de seguridad de CI ni `.npmrc`.
