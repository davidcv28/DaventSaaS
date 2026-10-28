# SECURITY RUNBOOK — validación externa y rotación de secretos

Documento operativo. Cada paso trae el comando que lo prueba; si un comando no
se puede correr sin un secreto o un panel externo, se indica explícitamente.
Complementa `SECURITY_AUDIT.md` (§15 despliegue, §17 cierre).

---

## 1. DAST: OWASP ZAP baseline contra staging

**Nunca contra producción.** El spider crea visitas (`StoreDailyVisit`), dispara
throttles y puede dejar usuarios/cupones de prueba. Usar una base de staging
descartable.

Requisitos:

- URL de staging con HTTPS y `DEBUG=False` (mismo build que producción).
- Una cuenta de prueba ya registrada (ver §2) — el baseline es **pasivo**
  (spider + reglas pasivas), no hace fuzzing ni fuerza credenciales.

```bash
# 1. Baseline pasivo (no modifica datos salvo navegación GET)
mkdir -p zap-out
docker run --rm -t -v "$PWD/zap-out:/zap/wrk:rw" ghcr.io/zaproxy/zap-stable \
  zap-baseline.py -t https://staging.<dominio> -r zap-baseline.html -I -m 5

# 2. Leer el resultado (falla el exit code con -I solo por HIGH)
grep -E "FAIL|WARN-NEW" zap-out/zap-baseline.html | head -40
```

Reglas de uso:

- `-I` = no falla por warnings; el criterio de release es **cero FAIL**.
- No usar `zap-full-scan.py` (activo) contra staging sin ventana acordada: puede
  crear pedidos/opiniones y ensuciar métricas.
- Los `429` en el informe son los throttles de DRF funcionando — no son un
  hallazgo, se documentan como tales.
- Excluir del spider: `/api/payments/webhook/` (POST firmado, no navegable),
  `/api/auth/google/` y cualquier `POST` de mutación.

Evidencia a guardar: `zap-out/zap-baseline.html` + commit desplegado en staging.

---

## 2. Endpoints autenticados: token de prueba

ZAP no puede loguearse solo contra JWT. Se emite un access token de una cuenta
**de staging** y se inyecta con el Replacer.

Endpoints que requieren `Authorization: Bearer <access>` (muestra, no exhaustiva):

| Área | Endpoints |
|------|-----------|
| Cuenta | `/api/profile/me/`, `/api/profile/update/`, `/api/password_update/` |
| Tienda | `/api/stores/`, `/api/stores/stats/`, `/api/stores/customization/` |
| Pagos | `/api/payments/checkout/`, `/api/payments/subscription/`, `/api/suscriptions/redeem-coupon/` |
| Chat | `/api/chat/`, `/api/chat/messages/`, `/api/chat/send/`, `/api/chat/heartbeat/` |
| Admin | `/api/coupons/` (staff), bandeja de chat (staff) |

```bash
# Token (staging, cuenta de prueba con email verificado)
ACCESS=$(curl -s -X POST https://staging.<dominio>/api/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"dast-user","password":"<clave-de-staging>","remember":false}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access"])')

# Verificación mínima de que el token sirve
curl -s -o /dev/null -w '%{http_code}\n' https://staging.<dominio>/api/profile/me/ \
  -H "Authorization: Bearer $ACCESS"     # -> 200

# ZAP con el header inyectado (replacer en todas las requests)
docker run --rm -t -v "$PWD/zap-out:/zap/wrk:rw" ghcr.io/zaproxy/zap-stable \
  zap-baseline.py -t https://staging.<dominio> -r zap-auth.html -I \
  -z "-config replacer.full_list(0).description=auth \
      -config replacer.full_list(0).enabled=true \
      -config replacer.full_list(0).matchtype=REQ_HEADER \
      -config replacer.full_list(0).matchstr=Authorization \
      -config replacer.full_list(0).replacement=Bearer\ $ACCESS"
```

- El token dura lo que diga `SIMPLE_JWT` (7d por defecto); si expira, ZAP empieza
  a recibir 401 — regenerarlo y repetir.
- La cuenta de staging **no** debe ser staff salvo que se quiera cubrir `/api/coupons/`.

---

## 3. Rotación de secretos

Regla de oro: **primero el keyring de PII, después `SECRET_KEY`**. Rotar
`SECRET_KEY` sin keyring deja el ciphertext de `UserProfile` ilegible (la llave
"self" se deriva de él). Ver `SECURITY_AUDIT.md` §15.2/C.

### 3.1 Keyring de PII (`SECRETS_MASTER_KEYS`)

1. Generar la nueva llave:
   ```bash
   docker compose exec api python manage.py encrypt_secret --gen-master-key k2
   ```
2. En `/opt/davent/.env` **anteponer** la nueva, conservando la vieja:
   `SECRETS_MASTER_KEYS=k2:<nueva>,k1:<vieja>`. La primera cifra; todas descifran.
3. Reiniciar API y workers: `docker compose up -d --force-recreate api celery`.
4. Re-cifrar todas las filas:
   ```bash
   docker compose exec api python manage.py rotate_encrypted_fields --batch 500
   # repetir hasta que no reporte filas rotadas
   ```
5. Recién entonces retirar `k1` del `.env` y reiniciar.

Verificación: `manage.py check --deploy` sin errores + `GET /api/profile/me/` de
una cuenta real devuelve los datos (si falla con `VaultError`, la llave activa no
puede descifrar esa fila → **no** retirar la vieja).

### 3.2 `SECRET_KEY`

Impacto: invalida sesiones JWT (simplejwt firma con `SECRET_KEY`), links de reset
y de verificación de email. No toca la PII **si ya hay keyring**.

Orden: 3.1 completo y verificado → nuevo `SECRET_KEY` (≥50 chars aleatorios) →
reiniciar api/celery → avisar que todos deben re-loguearse.

```bash
docker compose exec api python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

### 3.3 `SECRETS_HASH_KEY`

**No se rota en caliente.** `document_hash`/`phone_hash` ya emitidos dependen de
ella: cambiarla rompe unicidad y búsqueda. Si hay que rotarla, es una migración
con re-hash completo en ventana de mantenimiento (no implementada).

### 3.4 Mercado Pago (`SECRET_MP_KEY`, `MP_WEBHOOK_SECRET`)

Orden: panel de MP → `.env`/secrets → reinicio.

1. En MP: rotar el access token y/o la clave secreta de webhooks.
2. Actualizar `SECRET_MP_KEY` / `MP_WEBHOOK_SECRET` en GitHub Environment
   `production`, Render y `/opt/davent/.env` (el deploy los escribe con merge
   atómico; el resto del `.env` no se toca).
3. `docker compose up -d --force-recreate api celery`.
4. Verificar:
   ```bash
   docker compose exec api python manage.py check --deploy   # 0 errores
   docker compose logs -f api | grep -i webhook              # 200 con firma nueva
   ```
   Durante la ventana de cambio, los webhooks viejos reciben 401 (fail-closed) y
   MP reintenta — no se pierden cobros, se acreditan al reintento.

### 3.5 `SSH_HOST_FINGERPRINT`

```bash
ssh-keyscan -p <SSH_PORT> <SSH_HOST> | ssh-keygen -lf -
```
Comparar con el valor del Environment `production` antes de deployar. Si no
coincide, **no** deployar: o cambió la host key (legítimo, actualizar) o hay MITM.

---

## 4. Verificación posterior a cualquier rotación

```bash
docker compose exec api python manage.py check --deploy
docker compose exec api python manage.py test
curl -s -o /dev/null -w '%{http_code}\n' https://<dominio>/healthz/
docker compose logs --since 10m api | grep -iE "error|vault|401"
```

## 5. Qué NO está cubierto acá

- Pentest activo autenticado con lógica de negocio (cupones, checkout): requiere
  ventana y entorno aislado; el baseline pasivo no lo reemplaza.
- Escaneo de imágenes en runtime: lo hace `trivy image` en `ci-cd.yml` y
  `security-schedule.yml` (fs).
