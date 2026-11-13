<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { fetchSyncState } from '../../../api/storeSync.api.js'
import { apiErr, fmtDateTime, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Panel "Sincronización" — /api/stores/sync/ (dueño, sesión DAVENT).
// Estado de conexión + cola de operaciones pendientes de subir a la web.
const store = useStoreStore()
const loading = ref(false)
const errMsg = ref('')
const pendingCount = ref(0)
const lastSyncAt = ref(null)
const operations = ref([])

// Conexión: navigator.onLine + listeners; un fetch que muere por red
// (sin response) también marca offline hasta que vuelva a responder.
const browserOnline = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const netFailed = ref(false)
const offline = computed(() => !browserOnline.value || netFailed.value)

const STATUS_META = {
  pending: { label: 'Pendiente',    kind: 'warn',   icon: 'clock' },
  done:    { label: 'Sincronizado', kind: 'ok',     icon: 'check' },
  error:   { label: 'Error',        kind: 'danger', icon: 'triangle-alert' },
}
const statusMeta = (s) => STATUS_META[s] || { label: s || '—', kind: 'muted', icon: 'dot' }

// Nombres amigables de operación; si el backend manda otra cosa se muestra tal cual.
const OP_LABELS = {
  'update-empresa':  'Actualización de la empresa',
  'update-diseno':   'Cambio de diseño',
  'update-producto': 'Cambio de producto',
  'update-cobros':   'Cambio de cobros',
  'publish-design':  'Publicación de diseño',
  'publish-diseno':  'Publicación de diseño',
}
const opLabel = (op) => OP_LABELS[op?.op] || op?.op || 'Operación'
const shortId = (id) => String(id ?? '').slice(0, 8)
const opSlug = (op) => String(op?.op || '').replace(/_/g, ' - ')

const lastSyncLabel = computed(() => (lastSyncAt.value ? fmtDateTime(lastSyncAt.value) : 'Nunca'))
const syncTime = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
}

function applyState(data) {
  pendingCount.value = Number(data?.pending_count ?? 0)
  lastSyncAt.value = data?.last_sync_at || null
  operations.value = Array.isArray(data?.operations) ? data.operations : []
  netFailed.value = false
}

async function load() {
  loading.value = true
  errMsg.value = ''
  try {
    applyState(await fetchSyncState())
  } catch (e) {
    if (!e?.response) netFailed.value = true
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
  } finally {
    loading.value = false
  }
}

function onOnline() { browserOnline.value = true; netFailed.value = false; load() }
function onOffline() { browserOnline.value = false }

// Poll suave: al montar y cada 30s solo con la pestaña visible.
let pollTimer = null
onMounted(() => {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
  load()
  pollTimer = setInterval(() => {
    if (document.visibilityState === 'visible') load()
  }, 30000)
})
onBeforeUnmount(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
  if (pollTimer) clearInterval(pollTimer)
})

// hasStore llega por SWR (mismo patrón que OrdersPanel).
watch(() => store.hasStore, (h) => { if (h) load() })
</script>

<template>
  <div class="sync-panel">
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="sp-card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <template v-else>
      <!-- Cards de estado -->
      <div class="sp-stats">
        <div class="sp-card sp-stat">
          <span class="sp-stat-label"><AppIcon :name="offline ? 'circle-alert' : 'lucide:wifi'" :size="14" /> Conexión</span>
          <strong class="sp-stat-value" :class="{ 'is-off': offline }">
            {{ offline ? 'Sin conexión — trabajando local' : 'Conectado' }}
          </strong>
        </div>
        <div class="sp-card sp-stat">
          <span class="sp-stat-label"><AppIcon name="history" :size="14" /> Cambios pendientes</span>
          <strong class="sp-stat-value">{{ pendingCount }}</strong>
        </div>
        <div class="sp-card sp-stat">
          <span class="sp-stat-label"><AppIcon name="badge-check" :size="14" /> Última sync</span>
          <strong class="sp-stat-value">{{ lastSyncLabel }}</strong>
        </div>
      </div>

      <!-- Banner offline -->
      <div v-if="offline" class="sp-banner" role="status">
        <AppIcon name="triangle-alert" :size="15" aria-hidden="true" />
        <p>No hay conexión con el servidor. Todo lo que hagas se guarda local y se sube solo cuando vuelva.</p>
      </div>

      <!-- Operaciones encoladas -->
      <div class="sp-card">
        <div class="sp-card-head">
          <h3>Operaciones encoladas</h3>
          <span class="hint">{{ operations.length }} en la cola</span>
        </div>

        <div v-if="loading && !operations.length" class="empty-mini"><p>Cargando estado de sincronización…</p></div>
        <div v-else-if="!operations.length" class="sp-empty">
          <span class="sp-empty-ico"><AppIcon name="circle-check" :size="22" /></span>
          <strong>Sin operaciones pendientes</strong>
          <p>Tu web está al día: no quedó ningún cambio por subir.</p>
        </div>
        <div v-else class="sp-table-wrap">
          <table class="sp-table">
            <thead>
              <tr>
                <th scope="col">Operación</th>
                <th scope="col">Creada</th>
                <th scope="col">Estado</th>
                <th scope="col">Intentos</th>
                <th scope="col">Detalle</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="op in operations" :key="op.id ?? op.op">
                <td data-label="Operación">
                  <div class="sp-op">
                    <span class="sp-op-name">{{ opSlug(op) }}</span>
                    <span v-if="op.id != null" class="sp-op-id">{{ shortId(op.id) }}…</span>
                  </div>
                </td>
                <td data-label="Creada">{{ syncTime(op.created_at) }}</td>
                <td data-label="Estado">
                  <span class="sp-pill" :class="statusMeta(op.status).kind">
                    <AppIcon :name="statusMeta(op.status).icon" :size="11" /> {{ statusMeta(op.status).label }}
                  </span>
                </td>
                <td data-label="Intentos">{{ op.attempts ?? 0 }}</td>
                <td data-label="Detalle"><span class="sp-detail">{{ op.detail || '—' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Panel "Sincronización" — superficie navy del POS: cards planas con
   borde fino, acentos ámbar para pendiente/offline y verde para la
   acción de sincronizar. */
.sync-panel {
  --sp-card: #151a26;
  --sp-line: #232b3d;
  --sp-ink: #e6e9f0;
  --sp-muted: #8b93a7;
  --sp-amber: #f5a524;
  --sp-amber-bg: rgba(245, 165, 36, 0.10);
  --sp-green: #22c55e;
  min-width: 0;
}
.sp-card {
  background: var(--sp-card);
  border: 1px solid var(--sp-line);
  border-radius: 12px;
  color: var(--sp-ink);
}

/* --- Stats --- */
.sp-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}
.sp-stat { padding: 14px 16px; display: grid; gap: 8px; align-content: start; }
.sp-stat-label {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: 12px; font-weight: 600; color: var(--sp-muted);
}
.sp-stat-value { font-size: 15px; font-weight: 700; line-height: 1.3; }
.sp-stat-value.is-off { color: var(--sp-amber); }

/* --- Banner offline --- */
.sp-banner {
  display: flex; align-items: flex-start; gap: 10px;
  margin: 0 0 14px; padding: 11px 14px;
  border-radius: 12px;
  background: #2a1f0a;
  border: 1px solid rgba(245, 165, 36, 0.35);
  color: var(--sp-amber);
}
.sp-banner .icon { flex: none; margin-top: 1px; }
.sp-banner p { margin: 0; font-size: 13px; line-height: 1.45; font-weight: 550; }

/* --- Tabla --- */
.sp-card-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--sp-line);
}
.sp-card-head h3 { margin: 0; font-size: 14.5px; font-weight: 700; }
.sp-table-wrap { overflow-x: auto; }
.sp-table {
  width: 100%; border-collapse: collapse;
  font-size: 13px;
}
.sp-table th {
  padding: 10px 16px;
  text-align: left;
  font-size: 11.5px; font-weight: 600;
  color: var(--sp-muted);
  border-bottom: 1px solid var(--sp-line);
  white-space: nowrap;
}
.sp-table td {
  padding: 11px 16px;
  border-bottom: 1px solid var(--sp-line);
  vertical-align: middle;
}
.sp-table tbody tr:last-child td { border-bottom: 0; }
.sp-op { display: grid; gap: 2px; min-width: 0; }
.sp-op-name { font-weight: 600; white-space: nowrap; }
.sp-op-id {
  font-family: ui-monospace, 'Cascadia Code', Consolas, monospace;
  font-size: 11px; color: var(--sp-muted);
}
.sp-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; border-radius: 999px;
  font-size: 11.5px; font-weight: 700; white-space: nowrap;
}
.sp-pill.warn   { background: var(--sp-amber-bg); color: var(--sp-amber); box-shadow: inset 0 0 0 1px rgba(245,165,36,.35); }
.sp-pill.ok     { background: rgba(34,197,94,.12); color: #4ade80; box-shadow: inset 0 0 0 1px rgba(34,197,94,.3); }
.sp-pill.danger { background: rgba(239,68,68,.12); color: #f87171; box-shadow: inset 0 0 0 1px rgba(239,68,68,.3); }
.sp-pill.muted  { background: rgba(139,147,167,.12); color: var(--sp-muted); box-shadow: inset 0 0 0 1px var(--sp-line); }
.sp-detail { color: var(--sp-muted); }

/* --- Vacío --- */
.sp-empty { padding: 34px 16px; text-align: center; display: grid; justify-items: center; gap: 6px; }
.sp-empty-ico { color: var(--sp-green); }
.sp-empty p { margin: 0; color: var(--sp-muted); font-size: 13px; }

@media (max-width: 720px) {
  .sp-stats { grid-template-columns: 1fr; }
}
</style>
