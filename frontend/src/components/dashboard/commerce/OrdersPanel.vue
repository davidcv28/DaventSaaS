<script setup>
import { ref, computed, watch } from 'vue'
import { ownerOrdersApi } from '../../../api/storeorders.api.js'
import { storePaymentsApi } from '../../../api/storePayments.api.js'
import { apiErr, money, fmtDate, fmtDateTime, statusMeta,
         ORDER_STATUS, ORDER_STATUSES, PAYMENT_METHODS, SHIPPING_METHODS,
         NEXT_ORDER_ACTION, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Bandeja de pedidos del dueño — /api/store-orders/ (ownerOrdersApi).
// Paginado por página (DaventPageNumberPagination → {count,next,previous,results}).
const store = useStoreStore()
const loading = ref(false)
const errMsg = ref('')
const rows = ref([])
const pageInfo = ref({ count: 0, next: null, previous: null })
const page = ref(1)
const statusFilter = ref('')

const detail = ref(null)
const detailLoading = ref(false)
const actionBusy = ref('')
const actionMsg = ref('')
const actionErr = ref('')
// Formularios inline de las acciones que piden dato opcional.
const payRef = ref('')
const cancelReason = ref('')
const showPayForm = ref(false)
const showCancelForm = ref(false)
const invoiceRef = ref('')
const invoiceDirty = ref(false)
const mpRefundBusy = ref(false)
const confirmDlg = ref(null) // {title, desc, danger, label, run}

const hasPrev = computed(() => Boolean(pageInfo.value.previous))
const hasNext = computed(() => Boolean(pageInfo.value.next))

async function load(p = page.value) {
  loading.value = true
  errMsg.value = ''
  try {
    const data = await ownerOrdersApi.list({
      status: statusFilter.value || undefined,
      page: p,
      page_size: PAGE_SIZE,
    })
    const results = Array.isArray(data) ? data : (data?.results || [])
    rows.value = results
    pageInfo.value = Array.isArray(data)
      ? { count: results.length, next: null, previous: null }
      : { count: data?.count || 0, next: data?.next, previous: data?.previous }
    page.value = p
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch(statusFilter, () => load(1))
// hasStore llega por SWR: puede ser false al montar y true un tick después.
watch(() => store.hasStore, (h) => { if (h) load(1) }, { immediate: true })

// ----- Detalle -----
async function openDetail(orderId) {
  detailLoading.value = true
  actionMsg.value = ''
  actionErr.value = ''
  showPayForm.value = false
  showCancelForm.value = false
  invoiceRef.value = ''
  invoiceDirty.value = false
  try {
    detail.value = await ownerOrdersApi.detail(orderId)
    invoiceRef.value = detail.value.invoice_ref || ''
  } catch (e) {
    actionErr.value = apiErr(e, 'No se pudo abrir el pedido.')
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() { detail.value = null }

const detailStatus = computed(() => statusMeta(ORDER_STATUS, detail.value?.status))
const nextAction = computed(() => NEXT_ORDER_ACTION[detail.value?.status] || null)
const canRefundMp = computed(() =>
  detail.value?.payment_method === 'mp'
  && ['PAID', 'PACKING', 'SHIPPED'].includes(detail.value?.status))
const canRefundManual = computed(() =>
  ['PAID', 'PACKING', 'SHIPPED'].includes(detail.value?.status))

function askConfirm(opts) {
  return new Promise((resolve) => {
    confirmDlg.value = { ...opts, resolve }
  })
}
function answerConfirm(ok) {
  const dlg = confirmDlg.value
  confirmDlg.value = null
  dlg?.resolve?.(ok)
}

async function doConfirmPayment() {
  const ref = payRef.value.trim()
  actionBusy.value = 'pay'
  actionErr.value = ''
  actionMsg.value = ''
  try {
    await ownerOrdersApi.confirmPayment(detail.value.id, ref)
    actionMsg.value = 'Pago confirmado — el pedido pasó a preparación.'
    showPayForm.value = false
    payRef.value = ''
    await Promise.all([openDetail(detail.value.id), load(page.value)])
  } catch (e) {
    actionErr.value = apiErr(e)
  } finally {
    actionBusy.value = ''
  }
}

async function doAdvance(target) {
  actionBusy.value = target
  actionErr.value = ''
  actionMsg.value = ''
  try {
    await ownerOrdersApi.advance(detail.value.id, target)
    actionMsg.value = `Pedido marcado como "${statusMeta(ORDER_STATUS, target).label}".`
    await Promise.all([openDetail(detail.value.id), load(page.value)])
  } catch (e) {
    actionErr.value = apiErr(e)
  } finally {
    actionBusy.value = ''
  }
}

async function doRefund(kind) {
  const ok = await askConfirm(kind === 'mp'
    ? {
        title: '¿Reembolsar en Mercado Pago?',
        desc: 'Se devuelve el cobro completo al cliente por Mercado Pago y el pedido queda como reembolsado. No se puede deshacer.',
        label: 'Reembolsar', danger: true,
      }
    : {
        title: '¿Marcar como reembolsado?',
        desc: 'El pedido queda como reembolsado. OJO: esto NO devuelve la plata — la devolución la hacés por tu medio de cobro (transferencia, efectivo, etc.).',
        label: 'Marcar reembolsado', danger: true,
      })
  if (!ok) return
  actionBusy.value = 'refund'
  actionErr.value = ''
  actionMsg.value = ''
  try {
    if (kind === 'mp') {
      await storePaymentsApi.mpRefund(detail.value.id)
    } else {
      await ownerOrdersApi.advance(detail.value.id, 'REFUNDED')
    }
    actionMsg.value = kind === 'mp' ? 'Reembolso procesado por Mercado Pago.' : 'Pedido marcado como reembolsado.'
    await Promise.all([openDetail(detail.value.id), load(page.value)])
  } catch (e) {
    actionErr.value = apiErr(e)
  } finally {
    actionBusy.value = ''
  }
}

async function doCancel() {
  const reason = cancelReason.value.trim()
  actionBusy.value = 'cancel'
  actionErr.value = ''
  actionMsg.value = ''
  try {
    await ownerOrdersApi.cancel(detail.value.id, reason)
    actionMsg.value = 'Pedido cancelado.'
    showCancelForm.value = false
    cancelReason.value = ''
    await Promise.all([openDetail(detail.value.id), load(page.value)])
  } catch (e) {
    actionErr.value = apiErr(e)
  } finally {
    actionBusy.value = ''
  }
}

async function saveInvoiceRef() {
  actionBusy.value = 'invoice'
  actionErr.value = ''
  actionMsg.value = ''
  try {
    await ownerOrdersApi.setInvoiceRef(detail.value.id, invoiceRef.value.trim())
    invoiceDirty.value = false
    actionMsg.value = 'Referencia de factura guardada.'
    await openDetail(detail.value.id)
  } catch (e) {
    actionErr.value = apiErr(e)
  } finally {
    actionBusy.value = ''
  }
}

const shippingRows = computed(() => {
  const a = detail.value?.shipping_address
  if (!a || typeof a !== 'object') return []
  const labels = {
    label: 'Etiqueta', line1: 'Dirección', line2: 'Depto / piso',
    city: 'Ciudad', province: 'Provincia', postal_code: 'Código postal',
    country: 'País',
  }
  return Object.entries(a)
    .filter(([, v]) => v !== null && v !== undefined && String(v).trim() !== '')
    .map(([k, v]) => ({ key: k, label: labels[k] || k, value: String(v) }))
})

const docLabel = computed(() => {
  const d = detail.value
  if (!d) return ''
  const doc = `${d.customer_document_type || ''} ${d.customer_document || ''}`.trim()
  return doc
})

// Etiquetas de la bitácora (OrderEvent.kind — KIND_FOR_STATUS del backend).
const EVENT_LABELS = {
  created: 'Pedido creado',
  paid: 'Pago confirmado',
  packing: 'Pasó a preparación',
  shipped: 'Enviado',
  delivered: 'Entregado',
  cancelled: 'Cancelado',
  refunded: 'Reembolsado',
  expired: 'Venció sin pago',
  stock_conflict: 'Conflicto de stock',
  note: 'Nota',
}
function eventLabel(ev) {
  return EVENT_LABELS[ev?.kind] || ev?.kind || 'Evento'
}
</script>

<template>
  <div>
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a recibir pedidos.</p>
    </div>

    <template v-else>
      <div class="card">
        <div class="toolbar">
          <select v-model="statusFilter" class="select" style="max-width: 220px">
            <option value="">Todos los estados</option>
            <option v-for="s in ORDER_STATUSES" :key="s" :value="s">{{ ORDER_STATUS[s].label }}</option>
          </select>
          <button type="button" class="btn ghost btn-auto" :disabled="loading" @click="load(page)">
            <AppIcon name="refresh" :size="14" /> Actualizar
          </button>
          <span v-if="pageInfo.count" class="hint" style="margin-left: auto">{{ pageInfo.count }} pedido{{ pageInfo.count === 1 ? '' : 's' }}</span>
        </div>

        <div v-if="loading && !rows.length" class="empty-mini"><p>Cargando pedidos…</p></div>
        <div v-else-if="!rows.length" class="empty-mini">
          <p>{{ statusFilter ? 'No hay pedidos con ese estado.' : 'Todavía no entró ningún pedido. Compartí tu link y empezá a vender.' }}</p>
        </div>

        <div v-else class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Fecha</th>
                <th>Cliente</th>
                <th>Pago</th>
                <th>Envío</th>
                <th>Total</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="o in rows" :key="o.id" class="clickable" @click="openDetail(o.id)">
                <td data-label="Pedido"><strong class="mono">{{ o.code || `#${o.number}` }}</strong></td>
                <td data-label="Fecha">{{ fmtDate(o.created_at) }}</td>
                <td data-label="Cliente">
                  <div>{{ o.customer_name || [o.customer_first_name, o.customer_last_name].filter(Boolean).join(' ') || '—' }}</div>
                  <div class="hint">{{ o.customer_email }}</div>
                </td>
                <td data-label="Pago">{{ PAYMENT_METHODS[o.payment_method]?.label || o.payment_method || '—' }}</td>
                <td data-label="Envío">{{ SHIPPING_METHODS[o.shipping_method]?.label || o.shipping_method || '—' }}</td>
                <td data-label="Total"><strong>{{ money(o.total) }}</strong></td>
                <td data-label="Estado"><span class="pill" :class="ORDER_STATUS[o.status]?.kind || 'muted'">{{ ORDER_STATUS[o.status]?.label || o.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="hasPrev || hasNext" class="toolbar" style="justify-content: flex-end; margin: 10px 0 0">
          <button type="button" class="btn ghost btn-auto" :disabled="!hasPrev || loading" @click="load(page - 1)">← Anterior</button>
          <span class="hint">Página {{ page }}</span>
          <button type="button" class="btn ghost btn-auto" :disabled="!hasNext || loading" @click="load(page + 1)">Siguiente →</button>
        </div>
      </div>
    </template>

    <!-- Detalle del pedido (drawer) -->
    <Teleport to="body">
      <Transition name="pf">
        <div v-if="detail || detailLoading" class="pf-overlay" @click.self="closeDetail">
          <aside class="pf-drawer" role="dialog" aria-modal="true" :aria-label="`Pedido ${detail?.code || ''}`">
            <div class="pf-drawer-head">
              <div>
                <h3 class="mono">{{ detail?.code || 'Cargando…' }}</h3>
                <span v-if="detail" class="pill" :class="detailStatus.kind">{{ detailStatus.label }}</span>
              </div>
              <button type="button" class="icon-btn" aria-label="Cerrar" @click="closeDetail"><AppIcon name="x" :size="16" /></button>
            </div>

            <div v-if="detailLoading" class="pf-drawer-body"><div class="empty-mini"><p>Cargando pedido…</p></div></div>
            <div v-else-if="detail" class="pf-drawer-body">
              <AlertMessage v-if="actionErr" kind="error" :message="actionErr" />
              <AlertMessage v-else-if="actionMsg" kind="success" :message="actionMsg" />

              <!-- Acciones del dueño -->
              <section class="card" style="margin-top: 14px">
                <h3>Acciones</h3>

                <div v-if="detail.status === 'PENDING_PAYMENT'" class="pf-actions">
                  <template v-if="!showPayForm">
                    <button type="button" class="btn btn-auto" :disabled="actionBusy === 'pay'" @click="showPayForm = true">Confirmar pago</button>
                    <button type="button" class="btn ghost btn-auto" @click="showCancelForm = !showCancelForm">Cancelar pedido</button>
                  </template>
                  <template v-else>
                    <label class="field" style="flex:1;min-width:180px">
                      <span class="field-label">Referencia (opcional)</span>
                      <input v-model="payRef" class="input" placeholder="Ej: nro. de transferencia, alias que pagó" maxlength="120" />
                    </label>
                    <button type="button" class="btn btn-auto" :disabled="actionBusy === 'pay'" @click="doConfirmPayment">Sí, confirmar</button>
                    <button type="button" class="btn ghost btn-auto" @click="showPayForm = false">Volver</button>
                  </template>
                </div>

                <div v-if="showCancelForm && detail.status === 'PENDING_PAYMENT'" class="pf-actions" style="margin-top: 10px">
                  <label class="field" style="flex:1;min-width:180px">
                    <span class="field-label">Motivo (opcional)</span>
                    <input v-model="cancelReason" class="input" placeholder="Ej: el cliente se arrepintió" maxlength="300" />
                  </label>
                  <button type="button" class="btn danger btn-auto" :disabled="actionBusy === 'cancel'" @click="doCancel">Cancelar pedido</button>
                  <button type="button" class="btn ghost btn-auto" @click="showCancelForm = false">Volver</button>
                </div>

                <div v-if="nextAction" class="pf-actions">
                  <button type="button" class="btn btn-auto" :disabled="actionBusy === nextAction.target" @click="doAdvance(nextAction.target)">
                    {{ nextAction.label }}
                  </button>
                </div>

                <div v-if="canRefundMp || canRefundManual" class="pf-actions" style="margin-top: 10px">
                  <button v-if="canRefundMp" type="button" class="btn danger btn-auto" :disabled="mpRefundBusy || actionBusy === 'refund'" @click="doRefund('mp')">
                    Reembolsar en Mercado Pago
                  </button>
                  <button v-if="canRefundManual" type="button" class="btn ghost btn-auto" :disabled="actionBusy === 'refund'" @click="doRefund('manual')">
                    Marcar como reembolsado
                  </button>
                </div>
              </section>

              <!-- Datos del pedido -->
              <section class="card" style="margin-top: 14px">
                <h3>Pedido</h3>
                <div class="kv">
                  <div><span>Método de pago</span><strong>{{ PAYMENT_METHODS[detail.payment_method]?.label || detail.payment_method || '—' }}</strong></div>
                  <div><span>Envío</span><strong>{{ SHIPPING_METHODS[detail.shipping_method]?.label || detail.shipping_method || '—' }}</strong></div>
                  <div><span>Creado</span><strong>{{ fmtDateTime(detail.created_at) }}</strong></div>
                  <div><span>Vence</span><strong>{{ fmtDateTime(detail.expires_at) }}</strong></div>
                  <div><span>Pagado</span><strong>{{ fmtDateTime(detail.paid_at) }}</strong></div>
                  <div v-if="detail.payment_ref"><span>Ref. de pago</span><strong class="mono">{{ detail.payment_ref }}</strong></div>
                  <div><span>Subtotal</span><strong>{{ money(detail.subtotal) }}</strong></div>
                  <div><span>Descuento</span><strong>{{ money(detail.discount_total) }}</strong></div>
                  <div><span>Costo de envío</span><strong>{{ money(detail.shipping_cost) }}</strong></div>
                  <div><span>Total</span><strong>{{ money(detail.total) }}</strong></div>
                </div>
                <label class="field" style="margin-top: 12px">
                  <span class="field-label">Factura / remito (referencia interna)</span>
                  <div class="pf-actions" style="margin-top: 0">
                    <input v-model="invoiceRef" class="input" placeholder="Ej: A-0001-00001234" maxlength="60" @input="invoiceDirty = invoiceRef !== (detail.invoice_ref || '')" />
                    <button v-if="invoiceDirty" type="button" class="btn ghost btn-auto" :disabled="actionBusy === 'invoice'" @click="saveInvoiceRef">Guardar</button>
                  </div>
                </label>
              </section>

              <!-- Cliente -->
              <section class="card" style="margin-top: 14px">
                <h3>Cliente</h3>
                <div class="kv">
                  <div><span>Nombre</span><strong>{{ [detail.customer_first_name, detail.customer_last_name].filter(Boolean).join(' ') || '—' }}</strong></div>
                  <div><span>Email</span><strong>{{ detail.customer_email || '—' }}</strong></div>
                  <div><span>Teléfono</span><strong>{{ detail.customer_phone || '—' }}</strong></div>
                  <div v-if="docLabel"><span>Documento</span><strong class="mono">{{ docLabel }}</strong></div>
                </div>
              </section>

              <!-- Dirección -->
              <section v-if="shippingRows.length" class="card" style="margin-top: 14px">
                <h3>Dirección de envío</h3>
                <div class="kv">
                  <div v-for="r in shippingRows" :key="r.key"><span>{{ r.label }}</span><strong>{{ r.value }}</strong></div>
                </div>
              </section>

              <!-- Comprobante -->
              <section v-if="detail.proof_uploaded" class="card" style="margin-top: 14px">
                <h3>Comprobante de pago</h3>
                <a v-if="detail.proof_image" :href="detail.proof_image" target="_blank" rel="noopener" class="btn ghost btn-auto">
                  <AppIcon name="external-link" :size="14" /> Abrir comprobante
                </a>
                <p v-else class="hint">El comprador subió un comprobante.</p>
              </section>

              <!-- Productos -->
              <section class="card" style="margin-top: 14px">
                <h3>Productos</h3>
                <ul class="ord-items">
                  <li v-for="it in detail.items" :key="it.id">
                    <div>
                      <strong>{{ it.name }}</strong>
                      <span class="hint"> × {{ it.qty }} — {{ money(it.unit_price) }} c/u</span>
                    </div>
                    <span class="mono">{{ money(it.line_total) }}</span>
                  </li>
                </ul>
              </section>

              <!-- Bitácora -->
              <section v-if="detail.events?.length" class="card" style="margin-top: 14px">
                <h3>Seguimiento</h3>
                <ul class="ord-events">
                  <li v-for="ev in detail.events" :key="ev.id">
                    <span class="ord-event-dot" />
                    <div>
                      <strong>{{ eventLabel(ev) }}</strong>
                      <span v-if="ev.note" class="ord-event-note">{{ ev.note }}</span>
                      <span class="hint">{{ fmtDateTime(ev.created_at) }} · {{ ev.actor }}</span>
                    </div>
                  </li>
                </ul>
              </section>
            </div>
          </aside>
        </div>
      </Transition>

      <!-- Confirmación de acciones destructivas -->
      <Teleport to="body">
        <div v-if="confirmDlg" class="dsg-confirm" role="presentation">
          <div class="dsg-confirm-box" role="alertdialog" aria-modal="true">
            <h3>{{ confirmDlg.title }}</h3>
            <p v-if="confirmDlg.desc">{{ confirmDlg.desc }}</p>
            <div class="dsg-confirm-actions">
              <button type="button" class="btn ghost btn-auto" @click="answerConfirm(false)">Cancelar</button>
              <button type="button" class="btn btn-auto" :class="{ danger: confirmDlg.danger }" @click="answerConfirm(true)">{{ confirmDlg.label }}</button>
            </div>
          </div>
        </div>
      </Teleport>
    </Teleport>
  </div>
</template>

<style scoped>
/* El drawer usa z-index 120 (.pf-overlay): la confirmación va encima. */
.dsg-confirm { z-index: 130; }
.pf-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
.pf-actions .field { margin: 0; }
.ord-items { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.ord-items li { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.ord-events { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.ord-events li { display: flex; gap: 10px; align-items: flex-start; }
.ord-event-dot { flex: none; width: 9px; height: 9px; border-radius: 50%; background: var(--brand-500); margin-top: 5px; }
.ord-event-note { display: block; font-size: 13px; color: var(--ink-2); white-space: pre-line; }
.clickable { cursor: pointer; }
.hint { font-size: 12.5px; color: var(--muted); }
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: block; margin-bottom: 5px; }
</style>
