<script setup>
import { ref, computed, watch } from 'vue'
import { storeAdminApi } from '../../../api/storeadmin.api.js'
import { apiErr, money, fmtDate, daysAgoISO, todayISO,
         ORDER_STATUS, ORDER_STATUSES, PAYMENT_METHODS, PAYMENT_METHOD_KEYS,
         statusMeta, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Ventas del dueño — /api/store-admin/sales/* (summary + daily + CSV).
// Rango from/to (YYYY-MM-DD, máx 366 días) + filtros de método/estado que
// aplican a TODO el agregado (summary, serie y export comparten filtros).
const store = useStoreStore()
const loading = ref(false)
const exporting = ref(false)
const errMsg = ref('')
const exportMsg = ref('')
const summary = ref(null)
const daily = ref(null)

const filters = ref({
  from: daysAgoISO(29),
  to: todayISO(),
  payment_method: '',
  status: '',
})

const hasFilters = computed(() =>
  Boolean(filters.value.payment_method || filters.value.status))

async function load() {
  if (!store.hasStore) return
  loading.value = true
  errMsg.value = ''
  try {
    const params = {
      from: filters.value.from || undefined,
      to: filters.value.to || undefined,
      payment_method: filters.value.payment_method || undefined,
      status: filters.value.status || undefined,
    }
    const [sum, ser] = await Promise.all([
      storeAdminApi.salesSummary(params),
      storeAdminApi.salesDaily({ ...params, days: undefined }),
    ])
    summary.value = sum
    daily.value = ser
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
    summary.value = null
    daily.value = null
  } finally {
    loading.value = false
  }
}

// Recarga con debounce al tocar filtros de fecha/método/estado.
let t = null
watch(filters, () => {
  clearTimeout(t)
  t = setTimeout(load, 350)
}, { deep: true })

// hasStore llega por SWR: puede ser false al montar y true un tick después.
watch(() => store.hasStore, (h) => { if (h) load() }, { immediate: true })

async function exportCsv() {
  exporting.value = true
  exportMsg.value = ''
  errMsg.value = ''
  try {
    const name = await storeAdminApi.exportSalesCsv({
      from: filters.value.from || undefined,
      to: filters.value.to || undefined,
      payment_method: filters.value.payment_method || undefined,
      status: filters.value.status || undefined,
    })
    exportMsg.value = `CSV descargado: ${name}`
  } catch (e) {
    errMsg.value = e?.isExportError ? e.message : apiErr(e, 'No se pudo exportar el CSV.')
  } finally {
    exporting.value = false
  }
}

// ----- Gráfico de barras CSS (sin dependencias) -----
const series = computed(() => daily.value?.series || [])
const maxDaily = computed(() => {
  const m = Math.max(0, ...series.value.map((p) => Number(p.total_cobrado) || 0))
  return m || 1
})
const chartBars = computed(() =>
  series.value.map((p) => ({
    date: p.date,
    label: fmtDate(p.date),
    total: Number(p.total_cobrado) || 0,
    orders: p.orders_count || 0,
    pct: Math.max(2, Math.round(((Number(p.total_cobrado) || 0) / maxDaily.value) * 100)),
  })))

// Cortes del summary (shape estable del backend: siempre las 4/8 claves).
const pmRows = computed(() =>
  PAYMENT_METHOD_KEYS
    .map((k) => ({ key: k, ...summary.value?.by_payment_method?.[k] }))
    .filter((r) => r.orders_count > 0 || hasFilters.value))
const statusRows = computed(() =>
  ORDER_STATUSES
    .map((k) => ({ key: k, ...summary.value?.by_status?.[k] }))
    .filter((r) => r.orders_count > 0))

// Iconos de estado y método de pago (label y color salen de shared.js).
const ORDER_STATUS_ICON = {
  PENDING_PAYMENT: 'clock',
  PAID: 'badge-check',
  PACKING: 'package',
  SHIPPED: 'truck',
  DELIVERED: 'circle-check',
  CANCELLED: 'x',
  REFUNDED: 'rotate-cw',
  EXPIRED: 'timer',
}
function orderStatusIcon(s) { return ORDER_STATUS_ICON[s] || 'dot' }
const PAY_ICON = { transfer: 'building-2', whatsapp: 'whatsapp', cash: 'wallet', mp: 'credit-card' }
function payIcon(k) { return PAY_ICON[k] || 'wallet' }
</script>

<template>
  <div>
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />
    <AlertMessage v-if="exportMsg" kind="success" :message="exportMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <template v-else>
      <!-- Filtros -->
      <div class="card">
        <div class="toolbar sales-filters">
          <label class="field">
            <span class="field-label"><AppIcon name="calendar" :size="13" /> Desde</span>
            <input v-model="filters.from" type="date" class="input" :max="filters.to || undefined" />
          </label>
          <label class="field">
            <span class="field-label"><AppIcon name="calendar" :size="13" /> Hasta</span>
            <input v-model="filters.to" type="date" class="input" :min="filters.from || undefined" />
          </label>
          <label class="field field-grow">
            <span class="field-label"><AppIcon name="wallet" :size="13" /> Método de pago</span>
            <select v-model="filters.payment_method" class="select sel-chev">
              <option value="">Todos</option>
              <option v-for="k in PAYMENT_METHOD_KEYS" :key="k" :value="k">{{ PAYMENT_METHODS[k].label }}</option>
            </select>
          </label>
          <label class="field field-grow">
            <span class="field-label"><AppIcon name="filter" :size="13" /> Estado</span>
            <select v-model="filters.status" class="select sel-chev">
              <option value="">Todos</option>
              <option v-for="s in ORDER_STATUSES" :key="s" :value="s">{{ ORDER_STATUS[s].label }}</option>
            </select>
          </label>
          <button type="button" class="btn ghost btn-auto" :disabled="exporting || loading" @click="exportCsv">
            <AppIcon name="download" :size="14" /> {{ exporting ? 'Exportando…' : 'Exportar CSV' }}
          </button>
        </div>
      </div>

      <!-- Resumen -->
      <div v-if="loading && !summary" class="card"><div class="empty-mini"><p>Cargando ventas…</p></div></div>
      <template v-else-if="summary">
        <div class="stats">
          <div class="stat">
            <span class="stat-icon tone-ok"><AppIcon name="trending-up" :size="20" /></span>
            <div><strong>{{ money(summary.gross_total) }}</strong><small>Cobrado · {{ summary.cobrado_count }} pedido{{ summary.cobrado_count === 1 ? '' : 's' }} pago</small></div>
          </div>
          <div class="stat">
            <span class="stat-icon"><AppIcon name="receipt" :size="20" /></span>
            <div><strong>{{ money(summary.avg_ticket) }}</strong><small>Ticket promedio por pedido cobrado</small></div>
          </div>
          <div class="stat">
            <span class="stat-icon tone-warn"><AppIcon name="clock" :size="20" /></span>
            <div><strong>{{ money(summary.pending_total) }}</strong><small>Pendiente de pago · {{ summary.pending_count }} pedido{{ summary.pending_count === 1 ? '' : 's' }}</small></div>
          </div>
          <div class="stat">
            <span class="stat-icon tone-danger"><AppIcon name="rotate-cw" :size="20" /></span>
            <div><strong>{{ money(summary.refunded_total) }}</strong><small>Reembolsado · {{ summary.refunded_count }} pedido{{ summary.refunded_count === 1 ? '' : 's' }}</small></div>
          </div>
          <div class="stat">
            <span class="stat-icon tone-info"><AppIcon name="package" :size="20" /></span>
            <div><strong>{{ summary.orders_count }}</strong><small>Pedidos totales · {{ summary.from }} → {{ summary.to }}</small></div>
          </div>
        </div>

        <p v-if="summary.note" class="hint" style="margin: -4px 0 14px">{{ summary.note }}</p>

        <!-- Serie diaria -->
        <div class="card">
          <h3>Ventas por día</h3>
          <div v-if="chartBars.length" class="stats-chart" role="img" aria-label="Ventas por día">
            <span
              v-for="b in chartBars" :key="b.date" class="stats-bar"
              :style="{ height: `${b.pct}%` }"
              :title="`${b.label}: ${money(b.total)} · ${b.orders} pedido${b.orders === 1 ? '' : 's'}`"
            ></span>
          </div>
          <div v-if="chartBars.length" class="stats-chart-axis">
            <span>{{ fmtDate(daily?.from) }}</span>
            <span>{{ fmtDate(daily?.to) }}</span>
          </div>
          <div v-else class="stats-empty">
            <span class="stats-empty-icon"><AppIcon name="trending-up" :size="24" /></span>
            <strong>Sin ventas en este rango</strong>
            <p>Cuando entren pedidos, la serie diaria aparece acá.</p>
          </div>
        </div>

        <!-- Cortes -->
        <div class="grid-2">
          <div class="card">
            <h3>Por método de pago</h3>
            <div v-if="pmRows.some((r) => r.orders_count > 0)" class="table-wrap" style="border:none;box-shadow:none">
              <table class="pay-table">
                <thead><tr><th>Método</th><th>Pedidos</th><th>Cobrado</th><th>Pendiente</th></tr></thead>
                <tbody>
                  <tr v-for="r in pmRows.filter((x) => x.orders_count > 0)" :key="r.key">
                    <td data-label="Método"><span class="pm-cell"><AppIcon :name="payIcon(r.key)" :size="14" /> {{ PAYMENT_METHODS[r.key]?.label || r.key }}</span></td>
                    <td data-label="Pedidos">{{ r.orders_count }}</td>
                    <td data-label="Cobrado">{{ money(r.total_cobrado) }}</td>
                    <td data-label="Pendiente">{{ money(r.total_pendiente) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="empty-mini"><span>Sin pedidos en el rango.</span></p>
          </div>
          <div class="card">
            <h3>Por estado</h3>
            <div v-if="statusRows.length" class="table-wrap" style="border:none;box-shadow:none">
              <table class="pay-table">
                <thead><tr><th>Estado</th><th>Pedidos</th><th>Total</th></tr></thead>
                <tbody>
                  <tr v-for="r in statusRows" :key="r.key">
                    <td data-label="Estado"><span class="pill" :class="statusMeta(ORDER_STATUS, r.key).kind"><AppIcon :name="orderStatusIcon(r.key)" :size="12" /> {{ statusMeta(ORDER_STATUS, r.key).label }}</span></td>
                    <td data-label="Pedidos">{{ r.orders_count }}</td>
                    <td data-label="Total">{{ money(r.total) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="empty-mini"><span>Sin pedidos en el rango.</span></p>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
/* Stat-icon con tinte semántico: cobrado verde, pendiente ámbar, etc. */
.stat-icon.tone-ok { background: var(--ok-bg); color: var(--ok-ink); box-shadow: inset 0 0 0 1px var(--ok-line); }
.stat-icon.tone-warn { background: var(--warn-bg); color: var(--warn-ink); box-shadow: inset 0 0 0 1px var(--warn-line); }
.stat-icon.tone-danger { background: var(--danger-bg); color: var(--danger-ink); box-shadow: inset 0 0 0 1px var(--danger-line); }
.stat-icon.tone-info { background: var(--info-bg); color: var(--info-ink); box-shadow: inset 0 0 0 1px var(--info-line); }
.pm-cell { display: inline-flex; align-items: center; gap: 7px; }
.pm-cell .icon { color: var(--muted); }
/* Fila de filtros: campos parejos que crecen y el botón alineado abajo. */
.sales-filters { align-items: flex-end; }
.sales-filters .field { margin: 0; flex: 1 1 150px; }
.sales-filters .field-grow { flex: 1 1 190px; }
.sales-filters .btn { flex: none; }
/* Serie diaria: rangos largos (hasta 366 días) scrollean en vez de desbordar la card. */
.stats-chart { overflow-x: auto; padding-bottom: 4px; }
@media (max-width: 640px) {
  .sales-filters .field, .sales-filters .btn { flex: 1 1 100%; justify-content: center; }
  /* Tablas de cortes dentro de cards: filas planas, sin doble "card" anidada. */
  .grid-2 .pay-table tbody tr { box-shadow: none; border-color: var(--line-soft); }
}
@media (max-width: 480px) {
  /* styles.css pone .grid-2 en gap:0 — acá las dos cards sí necesitan aire. */
  .grid-2 { gap: 14px; }
}
</style>
