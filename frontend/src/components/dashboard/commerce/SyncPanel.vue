<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { fetchSyncState, runSync } from '../../../api/storeSync.api.js'
import { apiErr, fmtDateTime, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Panel "Sincronización" — /api/stores/sync/ (dueño, sesión DAVENT).
// Estado de conexión + cola de operaciones pendientes de subir a la web.
const store = useStoreStore()
const loading = ref(false)
const running = ref(false)
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
  pending: { label: 'Pendiente',   kind: 'warn',   icon: 'clock' },
  done:    { label: 'Sincronizado', kind: 'ok',    icon: 'check' },
  error:   { label: 'Error',       kind: 'danger', icon: 'triangle-alert' },
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

const lastSyncLabel = computed(() => (lastSyncAt.value ? fmtDateTime(lastSyncAt.value) : 'Nunca'))

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

async function doSync() {
  if (offline.value || running.value) return
  running.value = true
  errMsg.value = ''
  try {
    applyState(await runSync())
  } catch (e) {
    if (!e?.response) netFailed.value = true
    errMsg.value = apiErr(e, 'No se pudo sincronizar. Intentá de nuevo.')
    // Aunque falle el run, refrescamos el estado por si quedó desactualizado.
    try { applyState(await fetchSyncState()) } catch { /* sigue el errMsg del run */ }
  } finally {
    running.value = false
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

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <template v-else>
      <!-- Cards de estado -->
      <div class="stats">
        <div class="stat">
          <span class="stat-icon" :class="{ 'is-off': offline }" aria-hidden="true">
            <AppIcon :name="offline ? 'circle-alert' : 'lucide:wifi'" :size="20" />
          </span>
          <div class="stat-body">
            <strong>{{ offline ? 'Sin conexión' : 'Conectado' }}</strong>
            <small>{{ offline ? 'trabajando local' : 'Conexión con el servidor' }}</small>
          </div>
        </div>
        <div class="stat">
          <span class="stat-icon" aria-hidden="true"><AppIcon name="history" :size="20" /></span>
          <div class="stat-body">
            <strong>{{ pendingCount }}</strong>
            <small>Cambio{{ pendingCount === 1 ? '' : 's' }} pendiente{{ pendingCount === 1 ? '' : 's' }}</small>
          </div>
        </div>
        <div class="stat">
          <span class="stat-icon" aria-hidden="true"><AppIcon name="badge-check" :size="20" /></span>
          <div class="stat-body">
            <strong>{{ lastSyncLabel }}</strong>
            <small>Última sincronización</small>
          </div>
        </div>
      </div>

      <!-- Banner offline -->
      <div v-if="offline" class="sync-banner" role="status">
        <AppIcon name="triangle-alert" :size="16" aria-hidden="true" />
        <p>No hay conexión con el servidor. Todo lo que hagas se guarda local y se sube solo cuando vuelva.</p>
      </div>

      <!-- Operaciones encoladas -->
      <div class="card">
        <div class="toolbar">
          <h3 class="sync-card-title"><AppIcon name="clipboard-list" :size="16" /> Operaciones encoladas</h3>
          <span class="hint" style="margin-left: auto">{{ operations.length }} en la cola</span>
          <button
            type="button"
            class="btn btn-auto"
            :disabled="offline || running || loading"
            :aria-busy="running"
            @click="doSync"
          >
            <AppIcon name="refresh-cw" :size="15" :class="{ spin: running }" />
            {{ running ? 'Sincronizando…' : 'Sincronizar ahora' }}
          </button>
        </div>

        <div v-if="loading && !operations.length" class="empty-mini"><p>Cargando estado de sincronización…</p></div>
        <div v-else-if="!operations.length" class="pnl-empty">
          <span class="pnl-empty-ico"><AppIcon name="circle-check" :size="22" /></span>
          <strong>Sin operaciones pendientes</strong>
          <p>Tu web está al día: no quedó ningún cambio por subir.</p>
        </div>
        <div v-else class="table-wrap">
          <table class="pay-table">
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
                  <div class="sync-op">
                    <span>{{ opLabel(op) }}</span>
                    <span v-if="op.id != null" class="mono sync-op-id">{{ shortId(op.id) }}</span>
                  </div>
                </td>
                <td data-label="Creada">{{ fmtDateTime(op.created_at) }}</td>
                <td data-label="Estado">
                  <span class="pill" :class="statusMeta(op.status).kind">
                    <AppIcon :name="statusMeta(op.status).icon" :size="12" /> {{ statusMeta(op.status).label }}
                  </span>
                </td>
                <td data-label="Intentos">{{ op.attempts ?? 0 }}</td>
                <td data-label="Detalle"><span class="hint">{{ op.detail || '—' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sync-panel { min-width: 0; }
.stat-body { min-width: 0; }
.stat-body strong { font-size: 17px; }
.stat-icon.is-off {
  background: var(--warn-bg);
  color: var(--warn-ink);
  box-shadow: inset 0 0 0 1px var(--warn-line);
}
/* Banner offline (ámbar): mismo lenguaje que las pills warn del dashboard. */
.sync-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 0 0 16px;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--warn-bg);
  border: 1px solid var(--warn-line);
  color: var(--warn-ink);
}
.sync-banner .icon { flex: none; margin-top: 1px; }
.sync-banner p { margin: 0; font-size: 13.5px; line-height: 1.45; font-weight: 550; }
.sync-card-title {
  display: inline-flex; align-items: center; gap: 8px;
  margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -.01em;
}
.sync-op { display: grid; gap: 4px; min-width: 0; }
.sync-op-id { justify-self: start; font-size: 11px; }
/* Spinner del botón mientras corre la sincronización. */
.spin { animation: sync-spin 1s linear infinite; }
@keyframes sync-spin { to { transform: rotate(360deg); } }
@media (max-width: 720px) {
  .stats { grid-template-columns: 1fr; }
}
</style>
