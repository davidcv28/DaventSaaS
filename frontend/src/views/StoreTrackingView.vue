<script setup>
// Seguimiento público del pedido: /<slug>/seguimiento?token=<tracking_token>
// El tracking_token ES la credencial (anti-IDOR) — no requiere login, pero
// si el comprador está logueado puede saltar a su cuenta.
//
// - Stepper visual PENDING_PAYMENT → PAID → PACKING → SHIPPED → DELIVERED
//   (+ estados terminales EXPIRED/CANCELLED/REFUNDED como banner).
// - payment_instructions del server mientras está pendiente (transfer con
//   copiar alias, whatsapp wa.me, cash, mp → botón que pide preferencia).
// - Comprobante: valida tipo/tamaño client-side y sube multipart (el
//   server normaliza a WebP — acá solo preview, sin pipeline nuevo).
// - Comprobante NO FISCAL: datos armados por el server (build_receipt_payload).
// - Polling de events cada ~15 s SOLO mientras el pedido está activo.
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderPublicApi } from '../api/storeorders.api.js'
import { useCustomerStore } from '../stores/customer.store.js'
import { formatARS } from '../api/billing.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import PaymentInstructions from '../components/ecommerce/PaymentInstructions.vue'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')

const route = useRoute()
const router = useRouter()
const customer = useCustomerStore()

const token = computed(() => String(route.query.token || ''))
const order = ref(null)
const phase = ref('loading') // loading | ready | error | missing
const error = ref('')

const POLL_MS = 15000
let pollTimer = null

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')
const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' }) : ''
const fmtDateTime = (iso) => iso ? new Date(iso).toLocaleString('es-AR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''

const STATUS_LABELS = {
  PENDING_PAYMENT: 'Pendiente de pago',
  PAID: 'Pagado',
  PACKING: 'Preparando tu pedido',
  SHIPPED: 'En camino',
  DELIVERED: 'Entregado',
  EXPIRED: 'Vencido',
  CANCELLED: 'Cancelado',
  REFUNDED: 'Reembolsado',
}
const PAYMENT_LABELS = {
  transfer: 'Transferencia / depósito',
  whatsapp: 'WhatsApp',
  cash: 'Efectivo / en persona',
  mp: 'Mercado Pago',
}
// Etiqueta de entrega: con tarifa fija cargada por la tienda el envío a
// domicilio muestra "Envío a domicilio" (el precio va en Detalle); sin
// tarifa queda "A coordinar" (shipping_priced=False — el 0 no es gratis).
const ACTIVE = new Set(['PENDING_PAYMENT', 'PAID', 'PACKING', 'SHIPPED'])
const TERMINAL_BAD = new Set(['EXPIRED', 'CANCELLED', 'REFUNDED'])

const statusLabel = computed(() => STATUS_LABELS[order.value?.status] || order.value?.status || '')
const shipLabel = computed(() => {
  const m = order.value?.shipping_method
  if (m === 'pickup') return 'Retiro sin cargo'
  if (m === 'home') return order.value?.shipping_priced ? 'Envío a domicilio' : 'A coordinar con la tienda'
  return m || ''
})
// Detalle/recibo: precio fijo cobrado, "Sin cargo" si la tarifa es $0,
// "A coordinar" cuando la tienda no cargó precio (shipping_cost=0).
const shipCostLabel = (priced, cost) => {
  if (!priced) return 'A coordinar'
  const n = Number(cost)
  return n > 0 ? money(n) : 'Sin cargo'
}
const orderShipCost = computed(() => shipCostLabel(order.value?.shipping_priced, order.value?.shipping_cost))
const receiptShipCost = computed(() => shipCostLabel(receipt.value?.order?.shipping_priced, receipt.value?.totals?.shipping_cost))
const isActive = computed(() => ACTIVE.has(order.value?.status))
const isTerminalBad = computed(() => TERMINAL_BAD.has(order.value?.status))

// Stepper: pasos visibles según estado (los terminales muestran todos
// marcados hasta donde llegó + banner del desenlace).
const STEPS = [
  { key: 'PENDING_PAYMENT', label: 'Pedido recibido' },
  { key: 'PAID', label: 'Pago acreditado' },
  { key: 'PACKING', label: 'Preparando' },
  { key: 'SHIPPED', label: 'Enviado' },
  { key: 'DELIVERED', label: 'Entregado' },
]
const stepIndex = computed(() => {
  const s = order.value?.status
  if (s === 'DELIVERED') return 4
  if (s === 'SHIPPED') return 3
  if (s === 'PACKING') return 2
  if (s === 'PAID') return 1
  return 0
})

const eventsDesc = computed(() => [...(order.value?.events || [])].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))))
// Fecha/hora del último movimiento (el payload ya trae events[].created_at).
const lastChangeAt = computed(() => eventsDesc.value[0]?.created_at || '')
// Fecha del evento que dejó el pedido en cada paso del stepper: se busca
// el evento más reciente cuyo status_to coincide con el paso.
function stepDate(stepKey) {
  const ev = eventsDesc.value.find((e) => e.status_to === stepKey)
  return ev ? fmtDateTime(ev.created_at) : ''
}

const cuentaTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta`, query: { view: 'soporte', order: token.value } }))
// "Mis pedidos" sin el token del pedido actual: es el destino cuando el
// link no llega o el pedido no aparece (la lista ya linkea cada pedido).
const cuentaPedidosTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta`, query: { view: 'pedidos' } }))
const comprobanteTo = computed(() => ({
  path: storeHostSlug ? `/pedido/${token.value}/comprobante` : `/${slug.value}/pedido/${token.value}/comprobante`
}))
const catalogoTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const legalTo = computed(() => ({ path: storeHostSlug ? '/legal/terminos' : `/${slug.value}/legal/terminos` }))

// ---------- carga / polling ----------
async function load() {
  if (!token.value) { phase.value = 'missing'; return }
  phase.value = 'loading'
  error.value = ''
  try {
    order.value = await orderPublicApi.track(slug.value, token.value)
    phase.value = 'ready'
    schedulePoll()
  } catch (err) {
    error.value = extractApiError(err).nonField || 'No encontramos ese pedido. Revisá el link.'
    phase.value = 'error'
  }
}

function schedulePoll() {
  stopPoll()
  if (!isActive.value) return
  pollTimer = setInterval(pollEvents, POLL_MS)
}
function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

// Polling liviano: solo la timeline — si el último evento trae un
// status_to nuevo, refrescamos el track completo una vez.
async function pollEvents() {
  if (!token.value || !isActive.value) { stopPoll(); return }
  try {
    const events = await orderPublicApi.events(slug.value, token.value)
    const list = Array.isArray(events) ? events : (events?.results || [])
    if (list.length && order.value) {
      order.value.events = list
      const newest = list[0]
      if (newest?.status_to && newest.status_to !== order.value.status) {
        order.value = await orderPublicApi.track(slug.value, token.value)
      }
    }
    if (!isActive.value) stopPoll()
  } catch { /* polling silencioso: el próximo tick reintenta */ }
}

// Si el usuario vuelve a la pestaña, refrescar de una.
function onVisible() { if (document.visibilityState === 'visible' && phase.value === 'ready') load() }

// ---------- comprobante de pago ----------
const proofInput = ref(null)
const proofFile = ref(null)
const proofPreview = ref('')
const proofBusy = ref(false)
const proofError = ref('')
const proofDone = ref(false)
const canUploadProof = computed(() => (
  order.value?.status === 'PENDING_PAYMENT' &&
  order.value?.payment_method !== 'mp' &&
  order.value?.proof_required !== false &&
  !order.value?.proof_uploaded
))

function pickProof(e) {
  const file = e.target.files?.[0]
  proofError.value = ''
  proofDone.value = false
  if (!file) { proofFile.value = null; proofPreview.value = ''; return }
  if (!file.type.startsWith('image/')) { proofError.value = 'El comprobante tiene que ser una imagen (JPG, PNG o WebP).'; e.target.value = ''; return }
  if (file.size > 4 * 1024 * 1024) { proofError.value = 'La imagen no puede pesar más de 4 MB.'; e.target.value = ''; return }
  proofFile.value = file
  if (proofPreview.value) URL.revokeObjectURL(proofPreview.value)
  proofPreview.value = URL.createObjectURL(file)
}

async function uploadProof() {
  if (!proofFile.value || proofBusy.value || !token.value) return
  proofBusy.value = true
  proofError.value = ''
  try {
    await orderPublicApi.uploadProof(slug.value, token.value, proofFile.value)
    proofDone.value = true
    order.value.proof_uploaded = true
    proofFile.value = null
    if (proofPreview.value) { URL.revokeObjectURL(proofPreview.value); proofPreview.value = '' }
  } catch (err) {
    proofError.value = extractApiError(err).image || extractApiError(err).nonField || 'No pudimos subir el comprobante. Probá de nuevo.'
  } finally {
    proofBusy.value = false
  }
}

// ---------- comprobante NO FISCAL ----------
const receipt = ref(null)
const receiptOpen = ref(false)
const receiptBusy = ref(false)
const receiptError = ref('')
const addressLine = (a) => a ? [a.line1, a.line2, a.city, a.province, a.postal_code].filter(Boolean).join(', ') : ''

async function toggleReceipt() {
  if (receiptOpen.value) { receiptOpen.value = false; return }
  receiptOpen.value = true
  if (receipt.value || receiptBusy.value) return
  receiptBusy.value = true
  receiptError.value = ''
  try {
    receipt.value = await orderPublicApi.receipt(slug.value, token.value)
  } catch (err) {
    receiptError.value = extractApiError(err).nonField || 'No pudimos cargar el comprobante.'
  } finally {
    receiptBusy.value = false
  }
}

onMounted(() => {
  load()
  document.addEventListener('visibilitychange', onVisible)
})
onUnmounted(() => {
  stopPoll()
  document.removeEventListener('visibilitychange', onVisible)
  if (proofPreview.value) URL.revokeObjectURL(proofPreview.value)
})
</script>

<template>
  <div class="sp-page-root ec-track">
    <header class="ec-track-head">
      <h1 class="ec-track-title">Seguimiento de tu pedido</h1>
      <p v-if="order?.code" class="ec-track-code">Pedido <strong>{{ order.code }}</strong> · {{ shopName }}</p>
    </header>

    <!-- Mini-explicación para el comprador: <details> nativo (acordeón sin
         JS, summary como primer hijo, sin interactivos adentro). -->
    <details class="ec-track-help">
      <summary class="ec-track-help-summary">
        <AppIcon name="circle-help" :size="16" aria-hidden="true" />
        <span>¿Cómo funciona el seguimiento?</span>
        <AppIcon name="chevron-down" :size="15" class="ec-track-help-caret" aria-hidden="true" />
      </summary>
      <div class="ec-track-help-body">
        <ul class="ec-track-help-list">
          <li><AppIcon name="key" :size="14" aria-hidden="true" /><span>El link que recibiste al comprar <strong>es tu credencial</strong>: no lo compartas ni lo publiques.</span></li>
          <li><AppIcon name="route" :size="14" aria-hidden="true" /><span>El paso a paso muestra por dónde va tu pedido: recibido → pago acreditado → preparando → enviado → entregado.</span></li>
          <li><AppIcon name="package" :size="14" aria-hidden="true" /><span>Si tu pedido no aparece acá, revisá <RouterLink :to="cuentaPedidosTo">Mis pedidos</RouterLink> en tu cuenta: cada uno tiene su propio link.</span></li>
          <li><AppIcon name="clock" :size="14" aria-hidden="true" /><span>Los tiempos de cada estado los confirma el comercio — acá ves cuándo cambió, no una fecha prometida.</span></li>
        </ul>
      </div>
    </details>

    <div v-if="phase === 'missing'" class="ec-track-card ec-track-note">
      <span class="ec-track-note-ico" aria-hidden="true"><AppIcon name="file-text" :size="22" /></span>
      <div>
        <h2 class="ec-track-h2">Nos falta el link de seguimiento</h2>
        <p class="ec-track-muted">Necesitás el link que recibiste al crear el pedido. Si lo perdiste, podés encontrarlo en Mis pedidos de tu cuenta.</p>
      </div>
      <div class="ec-track-note-acts">
        <RouterLink :to="cuentaPedidosTo" class="ec-btn-primary">Ver mis pedidos</RouterLink>
        <RouterLink :to="catalogoTo" class="ec-btn-ghost">Volver al catálogo</RouterLink>
      </div>
    </div>

    <div v-else-if="phase === 'loading'" class="ec-track-card ec-track-skel" role="status" aria-busy="true" aria-label="Buscando tu pedido">
      <span class="ec-sk-line ec-sk-title"></span>
      <span class="ec-sk-line"></span>
      <div class="ec-sk-steps"><span v-for="n in 5" :key="n" class="ec-sk-dot"></span></div>
      <span class="ec-sk-line short"></span>
    </div>

    <div v-else-if="phase === 'error'" class="ec-track-card ec-track-note" role="alert">
      <span class="ec-track-note-ico is-danger" aria-hidden="true"><AppIcon name="circle-alert" :size="22" /></span>
      <div>
        <h2 class="ec-track-h2">No encontramos ese pedido</h2>
        <p class="ec-track-error">{{ error }}</p>
      </div>
      <div class="ec-track-note-acts">
        <button type="button" class="ec-btn-primary" @click="load">Reintentar</button>
        <RouterLink :to="cuentaPedidosTo" class="ec-btn-ghost">Ver mis pedidos</RouterLink>
        <RouterLink :to="catalogoTo" class="ec-btn-ghost">Volver al catálogo</RouterLink>
      </div>
    </div>

    <template v-else-if="order">
      <!-- Estado -->
      <section class="ec-track-card">
        <div class="ec-track-status-row">
          <span class="ec-track-status" :class="`is-${order.status.toLowerCase()}`">{{ statusLabel }}</span>
          <span v-if="order.expires_at && order.status === 'PENDING_PAYMENT'" class="ec-track-exp">
            <AppIcon name="clock" :size="13" aria-hidden="true" /> Vence {{ fmtDateTime(order.expires_at) }}
          </span>
        </div>

        <div v-if="isTerminalBad" class="ec-track-banner" :class="`is-${order.status.toLowerCase()}`">
          <AppIcon name="circle-alert" :size="18" aria-hidden="true" />
          <span v-if="order.status === 'EXPIRED'">El plazo para pagar venció. Si ya pagaste, escribinos.</span>
          <span v-else-if="order.status === 'CANCELLED'">Este pedido fue cancelado.</span>
          <span v-else>Este pedido fue reembolsado.</span>
        </div>
        <!-- CTA del desenlace terminal: reintentar la compra o hablar con
             el comercio según el motivo. -->
        <div v-if="isTerminalBad" class="ec-track-banner-acts">
          <RouterLink v-if="order.status === 'EXPIRED'" :to="catalogoTo" class="ec-btn-primary">
            <AppIcon name="shopping-bag" :size="15" aria-hidden="true" /> Hacer el pedido de nuevo
          </RouterLink>
          <RouterLink :to="cuentaTo" class="ec-btn-ghost">
            <AppIcon name="message-circle" :size="15" aria-hidden="true" /> Escribinos sobre este pedido
          </RouterLink>
        </div>

        <!-- Stepper -->
        <ol v-if="!isTerminalBad" class="ec-stepper" aria-label="Estado del pedido">
          <li v-for="(step, i) in STEPS" :key="step.key" class="ec-step"
              :class="{ 'is-done': i < stepIndex || order.status === 'DELIVERED', 'is-current': i === stepIndex && order.status !== 'DELIVERED' }"
              :aria-current="i === stepIndex && order.status !== 'DELIVERED' ? 'step' : undefined">
            <span class="ec-step-dot"><AppIcon v-if="i < stepIndex || order.status === 'DELIVERED'" name="check" :size="12" /><template v-else>{{ i + 1 }}</template></span>
            <span class="ec-step-label">{{ step.label }}</span>
            <small v-if="stepDate(step.key)" class="ec-track-step-date">{{ stepDate(step.key) }}</small>
          </li>
        </ol>

        <!-- Datos del pedido -->
        <dl class="ec-track-chips">
          <div class="ec-track-chip"><AppIcon name="calendar" :size="13" aria-hidden="true" /><span>Realizado el {{ fmtDate(order.created_at) }}</span></div>
          <div v-if="order.payment_method" class="ec-track-chip"><AppIcon name="credit-card" :size="13" aria-hidden="true" /><span>{{ PAYMENT_LABELS[order.payment_method] || order.payment_method }}</span></div>
          <div v-if="order.shipping_method" class="ec-track-chip"><AppIcon :name="order.shipping_method === 'home' ? 'truck' : 'store'" :size="13" aria-hidden="true" /><span>{{ shipLabel }}</span></div>
          <div v-if="lastChangeAt" class="ec-track-chip"><AppIcon name="clock" :size="13" aria-hidden="true" /><span>Último movimiento · {{ fmtDateTime(lastChangeAt) }}</span></div>
        </dl>
      </section>

      <!-- Instrucciones de pago -->
      <section v-if="order.status === 'PENDING_PAYMENT' && order.payment_instructions" class="ec-track-card">
        <PaymentInstructions :slug="slug" :instructions="order.payment_instructions" :order-token="token" :total="money(order.total)" />
      </section>

      <!-- Comprobante -->
      <section v-if="canUploadProof || order.proof_uploaded" class="ec-track-card">
        <h2 class="ec-track-h2">Comprobante de pago</h2>
        <p v-if="order.proof_uploaded" class="ec-track-ok"><AppIcon name="check" :size="15" aria-hidden="true" /> Ya recibimos tu comprobante — el comercio lo está verificando.</p>
        <template v-else>
          <p class="ec-track-muted">Subí la foto del comprobante para que el comercio acredite tu pago más rápido.</p>
          <div class="ec-proof">
            <label class="ec-proof-drop" :class="{ 'is-busy': proofBusy }">
              <input ref="proofInput" type="file" accept="image/*" class="ec-hp" :disabled="proofBusy" @change="pickProof" />
              <span v-if="proofPreview"><img :src="proofPreview" alt="Vista previa del comprobante" /></span>
              <span v-else class="ec-proof-cta">
                <AppIcon :name="proofBusy ? 'refresh' : 'plus'" :size="18" aria-hidden="true" />
                {{ proofBusy ? 'Subiendo…' : 'Elegir imagen' }}
              </span>
            </label>
            <div class="ec-proof-side">
              <button v-if="proofFile" type="button" class="ec-btn-primary" :disabled="proofBusy" @click="uploadProof">
                {{ proofBusy ? 'Subiendo…' : 'Subir comprobante' }}
              </button>
              <p class="ec-proof-hint">JPG, PNG o WebP · hasta 4 MB</p>
            </div>
          </div>
          <p v-if="proofError" class="sp-form-error" role="alert">{{ proofError }}</p>
          <p v-if="proofDone" class="ec-track-ok"><AppIcon name="check" :size="15" aria-hidden="true" /> Comprobante enviado.</p>
        </template>
      </section>

      <!-- Items + totales -->
      <section class="ec-track-card">
        <h2 class="ec-track-h2">Detalle</h2>
        <ul class="ec-track-items">
          <li v-for="(item, i) in order.items" :key="i">
            <img v-if="item.image" :src="item.image" :alt="item.name" class="ec-track-thumb" loading="lazy" />
            <div v-else class="ec-track-thumb is-empty" aria-hidden="true"><AppIcon name="package" :size="16" /></div>
            <div class="ec-track-item-info">
              <span>{{ item.name }}</span>
              <small>{{ item.qty }} × {{ money(item.unit_price) }}</small>
            </div>
            <strong>{{ money(item.line_total) }}</strong>
          </li>
        </ul>
        <dl class="ec-track-totals">
          <div><dt>Subtotal</dt><dd>{{ money(order.subtotal) }}</dd></div>
          <div v-if="Number(order.discount_total) > 0"><dt>Descuentos</dt><dd>−{{ money(order.discount_total) }}</dd></div>
          <div v-if="order.shipping_method === 'home'"><dt>Envío</dt><dd>{{ orderShipCost }}</dd></div>
          <div v-else><dt>Retiro</dt><dd>Sin cargo</dd></div>
          <div class="ec-track-grand"><dt>Total</dt><dd>{{ money(order.total) }}</dd></div>
        </dl>
        <p v-if="order.shipping_address && Object.keys(order.shipping_address).length" class="ec-track-muted">
          <AppIcon name="map-pin" :size="13" aria-hidden="true" /> Envío a: {{ addressLine(order.shipping_address) }}
        </p>
        <p v-if="order.invoice_ref" class="ec-track-muted">Factura/recibo del comercio: {{ order.invoice_ref }}</p>
      </section>

      <!-- Comprobante no fiscal -->
      <section class="ec-track-card">
        <div class="ec-track-receipt-row">
          <button type="button" class="ec-track-receipt-btn" @click="toggleReceipt">
            <AppIcon name="receipt" :size="17" aria-hidden="true" />
            {{ receiptOpen ? 'Ocultar comprobante' : 'Ver comprobante (no fiscal)' }}
          </button>
          <RouterLink :to="comprobanteTo" class="ec-track-receipt-link" target="_blank">
            <AppIcon name="printer" :size="14" aria-hidden="true" /> Versión para imprimir
          </RouterLink>
        </div>
        <div v-if="receiptOpen" class="ec-receipt">
          <p v-if="receiptBusy" class="ec-track-muted">Cargando…</p>
          <p v-else-if="receiptError" class="sp-form-error" role="alert">{{ receiptError }}</p>
          <template v-else-if="receipt">
            <header class="ec-rc-head">
              <div>
                <strong>{{ receipt.seller?.store_name || shopName }}</strong>
                <p class="ec-track-muted">
                  <template v-if="receipt.seller?.legal_name">{{ receipt.seller.legal_name }} · </template>
                  <template v-if="receipt.seller?.cuit">CUIT {{ receipt.seller.cuit }} · </template>
                  <template v-if="receipt.seller?.tax_condition_label">{{ receipt.seller.tax_condition_label }}</template>
                </p>
                <p v-if="receipt.seller?.fiscal_address" class="ec-track-muted">{{ receipt.seller.fiscal_address }}<template v-if="receipt.seller?.point_of_sale"> · PTO VTA {{ receipt.seller.point_of_sale }}</template></p>
              </div>
              <div class="ec-rc-meta">
                <strong>{{ receipt.order?.code }}</strong>
                <small>{{ fmtDate(receipt.order?.created_at) }}</small>
              </div>
            </header>
            <ul class="ec-rc-items">
              <li v-for="(item, i) in receipt.items" :key="i">
                <span>{{ item.name }} × {{ item.qty }}</span>
                <strong>{{ money(item.line_total) }}</strong>
              </li>
            </ul>
            <dl class="ec-rc-totals">
              <div><dt>Subtotal</dt><dd>{{ money(receipt.totals?.subtotal) }}</dd></div>
              <div v-if="Number(receipt.totals?.discount_total) > 0"><dt>Descuento</dt><dd>−{{ money(receipt.totals.discount_total) }}</dd></div>
              <div v-if="receipt.order?.shipping_method === 'home'"><dt>Envío</dt><dd>{{ receiptShipCost }}</dd></div>
              <div><dt>Total</dt><dd>{{ money(receipt.totals?.total) }}</dd></div>
            </dl>
            <p v-if="receipt.legend" class="ec-rc-legend">{{ receipt.legend }}</p>
          </template>
        </div>
      </section>

      <!-- Timeline + acciones -->
      <section class="ec-track-card">
        <h2 class="ec-track-h2">Movimientos</h2>
        <ul v-if="eventsDesc.length" class="ec-timeline">
          <li v-for="(ev, i) in eventsDesc" :key="i">
            <span class="ec-tl-dot" aria-hidden="true"></span>
            <div>
              <strong>{{ STATUS_LABELS[ev.status_to] || ev.status_to }}</strong>
              <small>{{ fmtDateTime(ev.created_at) }}</small>
            </div>
          </li>
        </ul>
        <p v-else class="ec-track-muted">Todavía no hay movimientos. Te avisamos acá cuando cambie el estado.</p>

        <div class="ec-track-actions">
          <RouterLink :to="cuentaTo" class="ec-btn-primary">
            <AppIcon name="message-circle" :size="16" aria-hidden="true" /> Escribinos sobre este pedido
          </RouterLink>
          <button v-if="customer.isAuthenticated" type="button" class="ec-btn-ghost" @click="router.push(cuentaTo)">Ver en mi cuenta</button>
        </div>
        <p class="ec-track-legal">
          La venta se realiza entre vos y el comercio: DAVENT solo provee la plataforma.
          <RouterLink :to="legalTo" target="_blank">Términos y condiciones</RouterLink>
        </p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.ec-track { display: grid; gap: 16px; }
.ec-track-head { display: grid; gap: 4px; }
.ec-track-title { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.ec-track-code { margin: 0; font-size: 14px; color: var(--sp-muted, inherit); }
.ec-track-card { display: grid; gap: 14px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.ec-track-h2 { margin: 0; font-size: 15px; font-weight: 800; }
.ec-track-muted { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ec-track-error { margin: 0; color: var(--sp-danger, #dc2626); }
.ec-track-note { grid-template-columns: auto 1fr; align-items: center; }
.ec-track-note > div { display: grid; gap: 4px; }
.ec-track-note-ico { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--store-accent, inherit); }
.ec-track-note-ico.is-danger { background: color-mix(in srgb, var(--sp-danger, #dc2626) 12%, transparent); color: var(--sp-danger, #dc2626); }
.ec-track-note-acts { grid-column: 1 / -1; display: flex; gap: 10px; flex-wrap: wrap; }
.ec-track-status-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.ec-track-status { font-size: 13px; font-weight: 800; padding: 6px 13px; border-radius: 999px; background: color-mix(in srgb, var(--store-accent, #111) 14%, transparent); }
.ec-track-status.is-pending_payment { background: color-mix(in srgb, var(--sp-warning, #B45309) 16%, transparent); color: var(--sp-warning, #B45309); }
.ec-track-status.is-paid, .ec-track-status.is-packing, .ec-track-status.is-shipped { background: color-mix(in srgb, var(--store-accent, #111) 14%, transparent); }
.ec-track-status.is-delivered { background: color-mix(in srgb, var(--sp-success, #0E7A55) 15%, transparent); color: var(--sp-success, #0E7A55); }
.ec-track-status.is-cancelled, .ec-track-status.is-expired, .ec-track-status.is-refunded { background: color-mix(in srgb, var(--sp-danger, #dc2626) 13%, transparent); color: var(--sp-danger, #dc2626); }
.ec-track-exp { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; color: var(--sp-warning, #B45309); font-weight: 600; }
.ec-track-banner { display: flex; align-items: center; gap: 8px; padding: 11px 13px; border-radius: calc(var(--sp-radius) * .7); font-size: 13.5px; background: color-mix(in srgb, var(--sp-danger, #dc2626) 10%, transparent); color: var(--sp-danger, #dc2626); }
.ec-track-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0; }
.ec-track-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 11px; border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: 999px; font-size: 12.5px; font-weight: 600; color: var(--sp-muted, inherit); }
.ec-track-chip svg { color: var(--store-accent, inherit); flex: none; }

/* Stepper con conectores */
.ec-stepper { list-style: none; margin: 6px 0 0; padding: 0; display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
.ec-step { position: relative; display: grid; justify-items: center; gap: 6px; text-align: center; }
.ec-step::after { content: ''; position: absolute; top: 15px; left: calc(50% + 17px); right: calc(-50% + 17px); height: 2px; border-radius: 2px; background: var(--sp-line, rgba(0,0,0,.16)); }
.ec-step.is-done::after { background: var(--sp-success, #0E7A55); }
.ec-step:last-child::after { display: none; }
.ec-step-dot { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; border: 2px solid var(--sp-line, rgba(0,0,0,.18)); font-size: 12px; font-weight: 800; color: var(--sp-muted, inherit); background: var(--sp-card, transparent); }
.ec-step.is-done .ec-step-dot { border-color: var(--sp-success, #0E7A55); background: var(--sp-success, #0E7A55); color: #fff; }
.ec-step.is-current .ec-step-dot { border-color: var(--store-accent, #111); color: var(--store-accent, #111); box-shadow: 0 0 0 4px color-mix(in srgb, var(--store-accent, #111) 15%, transparent); }
.ec-step-label { font-size: 11px; line-height: 1.25; color: var(--sp-muted, inherit); }
.ec-step.is-done .ec-step-label, .ec-step.is-current .ec-step-label { color: inherit; font-weight: 600; }

/* Mini-explicación "¿Cómo funciona el seguimiento?" (<details> nativo) */
.ec-track-help { border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .8); background: var(--sp-card, transparent); overflow: hidden; }
.ec-track-help-summary { display: flex; align-items: center; gap: 9px; padding: 13px 16px; font-size: 13.5px; font-weight: 700; color: var(--sp-ink-2, inherit); cursor: pointer; list-style: none; min-height: 44px; }
.ec-track-help-summary::-webkit-details-marker { display: none; }
.ec-track-help-summary svg:first-child { color: var(--store-accent, inherit); flex: none; }
.ec-track-help-caret { margin-left: auto; color: var(--sp-muted, inherit); transition: transform .18s ease; }
.ec-track-help[open] .ec-track-help-caret { transform: rotate(180deg); }
.ec-track-help-body { padding: 0 16px 14px; }
.ec-track-help-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.ec-track-help-list li { display: flex; align-items: flex-start; gap: 9px; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }
.ec-track-help-list svg { flex: none; margin-top: 2px; color: var(--store-accent, inherit); }
.ec-track-help-list strong { color: var(--sp-ink-2, inherit); }
.ec-track-help-list a { color: var(--sp-accent-text, var(--store-accent, inherit)); font-weight: 700; }

/* Fecha del paso en el stepper + acciones del estado terminal */
.ec-track-step-date { font-size: 10.5px; font-weight: 600; color: var(--sp-muted, inherit); font-variant-numeric: tabular-nums; }
.ec-step.is-done .ec-track-step-date, .ec-step.is-current .ec-track-step-date { color: inherit; }
.ec-track-banner-acts { display: flex; gap: 10px; flex-wrap: wrap; }

.ec-track-ok { display: flex; align-items: center; gap: 7px; margin: 0; font-size: 13.5px; font-weight: 600; color: var(--sp-success, #0E7A55); }
.ec-proof { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.ec-proof-drop { display: grid; place-items: center; min-width: 120px; min-height: 90px; border: 2px dashed var(--sp-line, rgba(0,0,0,.2)); border-radius: calc(var(--sp-radius) * .85); cursor: pointer; overflow: hidden; transition: border-color .15s, background .15s; }
.ec-proof-drop:hover { border-color: var(--store-accent, #111); background: color-mix(in srgb, var(--store-accent, #111) 4%, transparent); }
.ec-proof-drop.is-busy { opacity: .6; cursor: default; }
.ec-proof-drop img { width: 100%; height: 100%; object-fit: cover; max-height: 140px; }
.ec-proof-cta { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 600; color: var(--sp-muted, inherit); padding: 18px; }
.ec-proof-side { display: grid; gap: 8px; justify-items: start; }
.ec-proof-hint { margin: 0; font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-track-items { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.ec-track-items li { display: grid; grid-template-columns: 44px 1fr auto; gap: 10px; align-items: center; }
.ec-track-thumb { width: 44px; height: 44px; object-fit: cover; border-radius: calc(var(--sp-radius) * .55); background: var(--sp-line, rgba(0,0,0,.06)); }
.ec-track-thumb.is-empty { display: grid; place-items: center; color: var(--sp-muted, inherit); }
.ec-track-item-info { display: grid; gap: 2px; min-width: 0; font-size: 13.5px; }
.ec-track-item-info small { font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-track-items strong { font-size: 13.5px; font-variant-numeric: tabular-nums; }
.ec-track-totals { margin: 0; display: grid; gap: 6px; }
.ec-track-totals div { display: flex; justify-content: space-between; font-size: 13.5px; }
.ec-track-totals dt { color: var(--sp-muted, inherit); }
.ec-track-totals dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
.ec-track-grand { padding-top: 8px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.1)); font-size: 15px !important; }
.ec-track-grand dt { font-weight: 700; color: inherit !important; }
.ec-track-grand dd { font-size: 18px; font-weight: 800; }
.ec-track-receipt-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.ec-track-receipt-link { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: var(--store-accent, inherit); text-decoration: underline; text-underline-offset: 3px; }
.ec-track-receipt-btn { justify-self: start; display: inline-flex; align-items: center; gap: 8px; padding: 10px 14px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .7); background: transparent; color: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer; }
.ec-track-receipt-btn:hover { background: color-mix(in srgb, currentColor 6%, transparent); }
.ec-receipt { display: grid; gap: 12px; padding: 14px; border: 1px dashed var(--sp-line, rgba(0,0,0,.2)); border-radius: calc(var(--sp-radius) * .75); }
.ec-rc-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ec-rc-head p { margin: 2px 0 0; }
.ec-rc-meta { text-align: right; display: grid; gap: 2px; }
.ec-rc-items { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; font-size: 13px; }
.ec-rc-items li { display: flex; justify-content: space-between; gap: 10px; }
.ec-rc-totals { margin: 0; display: grid; gap: 5px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.12)); padding-top: 10px; }
.ec-rc-totals div { display: flex; justify-content: space-between; font-size: 13px; }
.ec-rc-totals dd { margin: 0; font-weight: 700; font-variant-numeric: tabular-nums; }
.ec-rc-legend { margin: 0; padding: 9px 11px; border-radius: calc(var(--sp-radius) * .55); background: color-mix(in srgb, var(--sp-warning, #B45309) 12%, transparent); color: var(--sp-warning, #B45309); font-size: 12px; font-weight: 600; }
.ec-timeline { list-style: none; margin: 0; padding: 0; display: grid; gap: 0; }
.ec-timeline li { display: flex; gap: 12px; padding: 9px 0; position: relative; }
.ec-timeline li:not(:last-child)::before { content: ''; position: absolute; left: 5px; top: 26px; bottom: -4px; width: 2px; background: var(--sp-line, rgba(0,0,0,.15)); }
.ec-tl-dot { flex: none; width: 12px; height: 12px; margin-top: 4px; border-radius: 50%; background: var(--store-accent, #111); }
.ec-timeline strong { display: block; font-size: 13.5px; }
.ec-timeline small { font-size: 12px; color: var(--sp-muted, inherit); }
.ec-track-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.ec-track-legal { margin: 0; padding-top: 12px; border-top: 1px dashed var(--sp-line, rgba(0,0,0,.14)); font-size: 12px; line-height: 1.55; color: var(--sp-muted, inherit); }
.ec-track-legal a { color: inherit; font-weight: 600; }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .75); background: transparent; color: inherit; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; }
.ec-hp { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }

/* Skeletons */
.ec-track-skel { gap: 12px; }
.ec-sk-line { display: block; height: 12px; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.ec-sk-title { width: 36%; height: 18px; }
.ec-sk-line.short { width: 50%; }
.ec-sk-steps { display: flex; gap: 10px; padding: 4px 0; }
.ec-sk-dot { width: 30px; height: 30px; border-radius: 50%; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
@media (prefers-reduced-motion: no-preference) {
  .ec-sk-line, .ec-sk-dot { animation: ec-track-shimmer 1.4s ease-in-out infinite; }
  .ec-sk-line:nth-child(2) { animation-delay: .1s; }
  .ec-sk-dot:nth-child(2) { animation-delay: .1s; }
  @keyframes ec-track-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

.ec-track-note .ec-btn-primary:focus-visible, .ec-track-note .ec-btn-ghost:focus-visible,
.ec-track-receipt-btn:focus-visible, .ec-track-receipt-link:focus-visible,
.ec-proof-drop:focus-within, .ec-track-legal a:focus-visible,
.ec-track-help-summary:focus-visible, .ec-track-help-list a:focus-visible,
.ec-track-banner-acts .ec-btn-primary:focus-visible, .ec-track-banner-acts .ec-btn-ghost:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .ec-track-help-caret { transition: none; }
}

@media (max-width: 560px) {
  .ec-stepper { grid-template-columns: 1fr; gap: 10px; }
  .ec-step { grid-template-columns: 30px 1fr; justify-items: start; text-align: left; }
  .ec-step::after { display: none; }
  .ec-step::before { content: ''; position: absolute; left: 14px; top: 32px; bottom: -9px; width: 2px; background: var(--sp-line, rgba(0,0,0,.16)); }
  .ec-step.is-done::before { background: var(--sp-success, #0E7A55); }
  .ec-step:last-child::before { display: none; }
  .ec-track-step-date { grid-column: 2; justify-self: start; }
  .ec-track-note { grid-template-columns: 1fr; justify-items: start; }
  .ec-track-note-acts { grid-column: auto; }
}
</style>
