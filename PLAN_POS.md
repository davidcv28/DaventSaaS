# PLAN POS — "DAVENT Mostrador" (app de ventas federada)

Integración del POS de `E:\sistemas\app de ventas` (Django 5 + DRF, React + Dexie
offline-first, sync push/pull por cursor) como app federada del SaaS.

**Decisión de arquitectura:** federación, no merge. El POS es single-tenant por
diseño (ningún modelo tiene FK a organización) y su stack frontend (React/Tauri)
difiere del dashboard (Vue). DAVENT actúa como **hub de licencia y —fase
posterior— servidor de sync**: el rol para el que el POS ya fue diseñado
(`Configuración → Servidor/nube` apunta a cualquier URL, contrato de sync fijo
en `CONTRACTS.md` §6).

---

## 1. Catálogo de apps y rubros

DAVENT ya tiene la taxonomía `DesignCategory` (rubros compartidos de patrones y
estilos: `general, indumentaria, calzado, deporte, gastronomia, hogar, turismo,
viajes, tecnologia, computacion, retail, servicios, seguridad, premium`). El
rubro de una tienda se deriva del patrón/estilo activo
(`store.customization` → `DesignPattern.categoria` / `DesignStyle.categoria`).

Nuevo concepto **catálogo de apps** (dominio `StoreApp/domains/pos`, app label
`pos`):

- `PosApp` — entrada de catálogo: `slug`, `nombre`, `descripcion`,
  `rubros` (ArrayField de slugs de `DesignCategory`), `tier_min` (plan mínimo,
  hoy solo `ecommerce`), `version`, `download_key` (R2), `is_active`, `position`.
- Primera entrada: `mostrador` — rubros `['retail']` (+ `general` como
  visibilidad de fallback), tier `ecommerce`. "Mercados, almacenes,
  autoservicios" → `retail` (así mapea STYLE_RUBRO: Supermercado/Marketplace →
  retail).
- El dashboard muestra el catálogo filtrado: `tier_min <= plan vigente` y
  (`rubros ∩ rubro(tienda)` o `general`). Una tienda sin diseño elegido cae a
  `general` — la app sigue visible (no se penaliza la indecisión).

Beneficio de plan: flag `has_pos_app` en `seed_benefits` + `SECTION_BENEFITS` +
`contract.js`, mismo mecanismo que `has_design_advanced`.

## 2. Licenciamiento offline-first (spec)

### Vínculo (pairing)

- El dashboard genera un código de 8 chars (`PosPairingCode`, expira 10 min,
  un solo uso).
- La app lo canjea en `POST /api/pos/pair/` → `{device_token}` JWT firmado
  `{store_id, device_id, iat}`, long-lived, revocable vía `PosDevice.revoked_at`.
- El usuario nunca tipea email/password: el código es la única llave.

### Token de licencia

`POST /api/pos/license/` (auth: device token) → JWT firmado por el servidor:

```jsonc
{ "store_id": 12, "device_id": "uuid", "plan": "ecommerce",
  "status": "active|denied", "denied_reason": "plan_expired|plan_changed|revoked",
  "iat": 1731690000, "exp": 1731690000 + 45d, "grace_until": "iso" }
```

Clave pública embebida en la app → **verifica firma y fecha sin internet**.
La licencia se renueva en cada `license/` o `sync/pull/` exitoso.

### Máquina de estados (al abrir / en background, timeout ~3s)

| Estado | Condición | Comportamiento |
|---|---|---|
| `ACTIVE` | licencia firmada vigente (`now < exp`) | app completa |
| `OFFLINE_GRACE` | sin conexión, `exp <= now < exp+30d` | app completa + badge "sin conexión" |
| `DENIED_GRACE` | server dice `denied`, dentro de `grace_until` (+5d) | aviso visible "plan vencido" |
| `DEGRADED` | `denied` pasada gracia, o `exp+30d` offline | **bloqueo operativo** |

**Bloqueo operativo, nunca de datos:** en `DEGRADED` se rechazan las
mutaciones (ventas, altas/edición de productos/clientes/compras, movimientos de
caja) — capa de permiso sobre los POST. Historial, reportes, consulta, export y
**backup** quedan plenamente accesibles.

### Integridad del estado denegado

`status:"denied"` viaja dentro del JWT firmado (no como flag plano en Dexie —
un flag editable se borra con DevTools). La app solo respeta el modo degradado
si el token lo declara, y no permite "rollback" a una licencia `active` más
vieja que una `denied` ya recibida (regla: `denied.iat` más reciente gana).

## 3. Modelo de datos (DAVENT, `StoreApp/domains/pos`)

```
PosApp            slug, nombre, rubros[], tier_min, version, download_key, is_active
PosDevice         store FK, device_id uuid, name, paired_at, last_seen_at, revoked_at
PosPairingCode    store FK, code, expires_at, used_at, created_by FK user
PosChangeLog      store FK, seq (BigAuto por tienda), entity_type, entity_id uuid,
                  op, payload jsonb          — espejo del ChangeLog del POS
PosProductMap     pos_uuid, product FK → stores.Product, store FK
PosSale           espejo read-only de ventas del mostrador (fase 2+)
```

## 4. Endpoints (DAVENT)

```
POST /api/pos/pair/            canje de código → device_token (JWT)
POST /api/pos/license/         device_token → licencia firmada
GET  /api/pos/apps/            catálogo filtrado por plan+rubro de la tienda
GET  /api/pos/download/<slug>/ URL firmada al instalador en R2
# Fase 2+:
POST /api/pos/sync/push/       contrato §6 CONTRACTS.md, Idempotency-Key, dedup op_id
GET  /api/pos/sync/pull/       ?since=<seq>&limit=500, cursor por tienda
```

## 5. Cambios en el POS (`E:\sistemas\app de ventas`)

Sin tocar el backend local (deploy LAN-only sigue existiendo):

- `src/license/` nuevo: pairing (pantalla "vincular con código"), storage de
  licencia en Dexie, verificación offline de firma (clave pública embebida),
  guard de modo degradado sobre las rutas/mutaciones (`requireCapability`).
- `API_BASE` → URL DAVENT en modo vinculado; el outbox Dexie + push/pull ya
  existen, solo cambia el destino.
- Auth en modo vinculado: device token reemplaza al login `Usuario` (el modo
  self-hosted mantiene JWT propio).

## 6. Fases

| Fase | Alcance | Entregable |
|---|---|---|
| **0** | Flag `has_pos_app` + catálogo `PosApp` (rubro `retail`) + pairing + licencia + degradado en app | El "regalo con el plan" funciona, sin sync de datos |
| **1** | Sync hub: `PosChangeLog`, push/pull scoping por tienda, `ENTITY_REGISTRY` subset `producto`/`venta`/`venta_item`/`pago` + `PosProductMap`/`PosSale` | Catálogo unificado + ventas del mostrador en el dashboard |
| **2** | Resto de entidades (`clientes`, `compras`, `caja`, `comprobantes`), `media`, multi-dispositivo | Sync completo |
| **3** | Build Tauri → instalador en R2 + endpoint de descarga + auto-update | Distribución |

## 7. Seguridad

- Licencia JWT firmada con clave del servidor (Ed25519 o RS256; pública embebida
  en la app). Nunca HS256 con secreto compartido: el secreto viajaría en el binario.
- Device token revocable por dispositivo (`revoked_at`) — "desvincular esta PC"
  desde el dashboard.
- Rate limit en `pair/` (5/min por store) — el código tiene 10 min de vida.
- Todo endpoint `pos/` bajo auth; `sync/push` con `Idempotency-Key` obligatorio
  (mismo patrón que el POS).
- Nada de "chequeo oculto": la conexión se justifica por licencia+sync; el
  estado degradado es siempre visible con aviso.

## 8. Marco legal y política al usuario

Principio rector: la suspensión es **de servicio, nunca de datos**. Informada
de forma pre-contractual (Ley 24.240 art. 4), gradual, con aviso previo y
acceso/exportación garantizados. Todo texto de abajo va listo para aplicar;
la revisión humana queda registrada en `docs/legal-review-ecommerce.md`.

### 8.1 Textos de superficie (visibles para el cliente)

**Descripción del beneficio (grilla de planes):**
> "App de mostrador incluida (requiere plan activo). Tus datos siempre son tuyos."

**Pantalla de vinculación (dashboard + app):**
> "Esta app queda vinculada al plan de tu tienda. Si el plan vence, las
> funciones de venta y de registros nuevos se pausan después de un período de
> aviso, pero tu historial, reportes y copias de seguridad quedan siempre
> accesibles y exportables."

**Aviso in-app durante `DENIED_GRACE`:**
> "Tu plan venció el {fecha}. Podés seguir consultando todo tu historial;
> para volver a registrar ventas, renová tu plan desde tu panel. Tenés
> {N} días antes de que las funciones operativas se pausen. Tu información
> no se pierde."

**Aviso in-app `DEGRADED`:**
> "Funciones de venta pausadas por plan vencido. Tu historial, reportes y
> backups siguen disponibles y podés exportar todo. Renovando el plan la app
> vuelve a funcionar completa sin reinstalar ni perder nada."

### 8.2 Cláusula ToS de DAVENT (nueva sección, misma casa que `docs/ecommerce-legal.md` §1)

> **Aplicaciones vinculadas.** DAVENT puede ofrecer aplicaciones de escritorio
> o móviles (p. ej. punto de venta) incluidas en determinados planes. Las
> aplicaciones se licencian por dispositivo y verifican periódicamente la
> vigencia del plan del titular; para ello transmiten un identificador de
> dispositivo y datos de uso técnico. Si el plan vence o se cancela, las
> funciones operativas de la aplicación se suspenden previo aviso con al menos
> cinco (5) días de anticipación. La suspensión no afecta el acceso,
> consulta, exportación ni las copias de seguridad de la información del
> titular, que permanece disponible en todo momento. DAVENT no elimina datos
> del titular por falta de pago del plan de la aplicación.

### 8.3 Privacidad (anexo a la política de DAVENT — extender `docs/ecommerce-legal.md` §2)

- **Qué reporta la app:** `device_id`, versión de app, IP de origen,
  timestamps de conexión, resultado del chequeo de licencia. En fase de sync:
  los mismos datos que la app ya almacena localmente (productos, ventas,
  clientes del comercio).
- **Rol de DAVENT:** encargado de tratamiento respecto de los datos del
  comercio y de sus clientes finales (misma figura que §2.2); responsable
  respecto de los datos de la cuenta del titular.
- **Base y plazo:** ejecución del contrato; los registros de licencia se
  conservan 24 meses; los datos sincronizados se gobiernan por la misma
  política de retención de la tienda.
- **Lo que la app NO hace:** no envía contenido de ventas sin sync activa,
  no rastrea ubicación, no accede a datos fuera de su base local.

### 8.4 Checklist para revisión legal humana (sumar a `docs/legal-review-ecommerce.md`)

1. Confirmar que el titular del plan se encuadra como comerciante/B2B y no
   "consumidor final" para la suspensión de funciones (si no, evaluar gracia
   mayor o suspensión solo tras baja expresa).
2. Revisar la cláusula §8.2 con letra chica de la provincia del titular
   (Ley 24.240 es nacional y piso; provincias pueden sumar).
3. Verificar que el aviso de renovación automática del plan (Decreto
   274/2019) ya cubre el escenario "plan vence → app se degrada" — enlazarlo
   desde la cláusula, no duplicarlo.
4. Registrar la app como software licenciado (no vendido) en el contrato —
   el cliente compra acceso, no el binario.
5. Exportación en `DEGRADED`: validar formato (CSV/JSON completo) para que la
   promesa "tus datos siempre son tuyos" sea cumplible, no marketing.

### 8.5 Lo que queda prohibido por diseño (guardarraíles)

- Nunca bloqueo sin aviso previo visible.
- Nunca retener datos, historial ni exportación tras la suspensión.
- Nunca re-activar funciones cobrando cargos adicionales no informados.
- Nunca telemetría encubierta: toda comunicación de la app es licencia o
  sync, documentada en §8.3.

## 9. Decisiones abiertas

1. **Multi-caja sin internet**: dos mostradores del mismo local no se ven entre
   sí offline (cada uno synca a DAVENT por su cuenta). Si importa: PC-servidor
   local como edge → esa PC synca a DAVENT. Post-fase 2.
2. **Conflicto producto**: edición simultánea dashboard/mostrador → LWW por
   campo; stock siempre como `movimiento_stock` delta, nunca absoluto.
   `AlertaReconciliacion` del POS se replica en DAVENT.
3. **Grace periods finales**: 45d licencia / 30d offline grace / 5d denied
   grace — números ajustables por config, no hardcode.
4. **Rubros adicionales** del POS si el catálogo crece (`gastronomia` para
   bares/resto con el mismo POS, etc.).
