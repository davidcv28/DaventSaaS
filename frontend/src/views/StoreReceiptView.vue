<script setup>
// Comprobante imprimible NO FISCAL: /<slug>/pedido/<token>/comprobante
// (o /pedido/<token>/comprobante en subdominio). Público — el
// tracking_token del path ES la credencial (anti-IDOR).
// Los datos los arma el server (build_receipt_payload); el front solo
// los renderiza y los imprime (window.print + @media print).
import { ref, computed, inject, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { orderPublicApi } from '../api/storeorders.api.js'
import { formatARS } from '../api/billing.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')
// Logo de la tienda (custom.logo del contexto público — string URL).
const custom = ctx?.custom
const logoUrl = computed(() => custom?.value?.logo || '')

const route = useRoute()
const token = computed(() => String(route.params.token || ''))

const receipt = ref(null)
const phase = ref('loading') // loading | ready | error
const error = ref('')

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')
const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' }) : ''
const addressLine = (a) => a ? [a.line1, a.line2, a.city, a.province, a.postal_code].filter(Boolean).join(', ') : ''

const seguimientoTo = computed(() => ({
  path: storeHostSlug ? '/seguimiento' : `/${slug.value}/seguimiento`,
  query: { token: token.value }
}))
const catalogoTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))

const STATUS_LABELS = {
  PENDING_PAYMENT: 'Pendiente de pago', PAID: 'Pagado', PACKING: 'Preparando',
  SHIPPED: 'Enviado', DELIVERED: 'Entregado', EXPIRED: 'Vencido',
  CANCELLED: 'Cancelado', REFUNDED: 'Reembolsado',
}
// Con tarifa fija cargada por la tienda el envío a domicilio muestra
// "Envío a domicilio" (el precio va en Totales); sin tarifa queda
// "A coordinar" — shipping_priced=False, el 0 no es gratis.
const shipLabel = computed(() => {
  const m = receipt.value?.order?.shipping_method
  if (m === 'pickup') return 'Retiro sin cargo'
  if (m === 'home') return receipt.value?.order?.shipping_priced ? 'Envío a domicilio' : 'A coordinar con la tienda'
  return m || ''
})
const shipCostLabel = computed(() => {
  if (!receipt.value?.order?.shipping_priced) return 'A coordinar'
  const n = Number(receipt.value?.totals?.shipping_cost)
  return n > 0 ? money(n) : 'Sin cargo'
})

// invoice_ref puede ser un código/número de factura o una URL a un
// archivo que subió el vendedor — si es URL la mostramos como descarga,
// pero solo hacia hosts de confianza (storage propio, AFIP, plataforma):
// un link arbitrario en el comprobante público sería phishing al cliente.
const INVOICE_LINK_HOST_RE = /(^|\.)(r2\.dev|r2\.cloudflarestorage\.com|afip\.gob\.ar)$|^(davent\.com\.ar|daventsaas\.onrender\.com|localhost|127\.0\.0\.1)$/
const invoiceUrl = computed(() => {
  const v = String(receipt.value?.invoice_ref || '')
  if (!/^https?:\/\//i.test(v)) return ''
  try {
    return INVOICE_LINK_HOST_RE.test(new URL(v).hostname.toLowerCase()) ? v : ''
  } catch {
    return ''
  }
})

async function load() {
  if (!token.value) { error.value = 'El link del comprobante está incompleto.'; phase.value = 'error'; return }
  phase.value = 'loading'
  error.value = ''
  try {
    receipt.value = await orderPublicApi.receipt(slug.value, token.value)
    phase.value = 'ready'
  } catch (err) {
    error.value = extractApiError(err).nonField || 'No pudimos cargar el comprobante. Revisá el link.'
    phase.value = 'error'
  }
}

function print() { window.print() }

onMounted(load)
</script>

<template>
  <div class="sp-page-root ec-receiptpg">
    <!-- Barra de acciones (no se imprime) -->
    <div class="ec-rp-actions no-print">
      <RouterLink :to="seguimientoTo" class="ec-rp-link">
        <AppIcon name="arrow-left" :size="15" aria-hidden="true" /> Volver al seguimiento
      </RouterLink>
      <div class="ec-rp-actions-right">
        <RouterLink :to="catalogoTo" class="ec-rp-link">Catálogo</RouterLink>
        <button v-if="phase === 'ready'" type="button" class="ec-btn-primary" @click="print">
          <AppIcon name="printer" :size="16" aria-hidden="true" /> Imprimir
        </button>
      </div>
    </div>

    <div v-if="phase === 'loading'" class="ec-rp-card ec-rp-skel" aria-busy="true" aria-label="Cargando el comprobante">
      <span class="ec-sk-line ec-sk-title"></span>
      <span class="ec-sk-line"></span>
      <span class="ec-sk-line short"></span>
      <span class="ec-sk-line ec-sk-table"></span>
    </div>

    <div v-else-if="phase === 'error'" class="ec-rp-card ec-rp-note" role="alert">
      <span class="ec-rp-note-ico is-danger" aria-hidden="true"><AppIcon name="circle-alert" :size="22" /></span>
      <div>
        <h2 class="ec-rp-h2">No pudimos cargar el comprobante</h2>
        <p class="ec-rp-error">{{ error }}</p>
      </div>
      <div class="ec-rp-note-acts">
        <button type="button" class="ec-btn-primary" @click="load">Reintentar</button>
        <RouterLink :to="catalogoTo" class="ec-rp-link">Volver al catálogo</RouterLink>
      </div>
    </div>

    <article v-else-if="receipt" class="ec-rp-doc">
      <!-- Encabezado del comercio -->
      <header class="ec-rp-head">
        <div class="ec-rp-seller">
          <img v-if="logoUrl" :src="logoUrl" :alt="`Logo de ${receipt.seller?.store_name || shopName}`" class="ec-rp-logo" />
          <div class="ec-rp-seller-txt">
            <strong class="ec-rp-store">{{ receipt.seller?.store_name || shopName }}</strong>
            <p v-if="receipt.seller?.legal_name" class="ec-rp-meta">{{ receipt.seller.legal_name }}</p>
            <p class="ec-rp-meta">
              <template v-if="receipt.seller?.cuit">CUIT {{ receipt.seller.cuit }}</template>
              <template v-if="receipt.seller?.tax_condition_label"><template v-if="receipt.seller?.cuit"> · </template>{{ receipt.seller.tax_condition_label }}</template>
            </p>
            <p v-if="receipt.seller?.fiscal_address" class="ec-rp-meta">
              {{ receipt.seller.fiscal_address }}<template v-if="receipt.seller?.point_of_sale"> · PTO VTA {{ receipt.seller.point_of_sale }}</template>
            </p>
          </div>
        </div>
        <div class="ec-rp-order">
          <span class="ec-rp-kind">Comprobante de pedido</span>
          <strong class="ec-rp-code">{{ receipt.order?.code }}</strong>
          <small>{{ fmtDate(receipt.order?.created_at) }}</small>
          <span v-if="receipt.order?.status" class="ec-rp-status">{{ STATUS_LABELS[receipt.order.status] || receipt.order.status }}</span>
        </div>
      </header>

      <!-- Datos del pedido -->
      <section class="ec-rp-sec">
        <h2 class="ec-rp-sec-title">Datos del pedido</h2>
        <dl class="ec-rp-fields">
          <div><dt>Comprador</dt><dd>{{ receipt.customer?.first_name || '—' }}</dd></div>
          <div><dt>Entrega</dt><dd>{{ shipLabel || '—' }}</dd></div>
          <div v-if="addressLine(receipt.shipping_address)">
            <dt>Dirección</dt><dd>{{ addressLine(receipt.shipping_address) }}</dd>
          </div>
        </dl>
      </section>

      <!-- Ítems -->
      <section class="ec-rp-sec">
        <h2 class="ec-rp-sec-title">Detalle</h2>
        <table class="ec-rp-table">
          <thead>
            <tr><th>Producto</th><th class="is-num">Cant.</th><th class="is-num">Precio</th><th class="is-num">Subtotal</th></tr>
          </thead>
          <tbody>
            <tr v-if="!receipt.items?.length"><td colspan="4" class="is-empty">Sin ítems cargados.</td></tr>
            <tr v-for="(item, i) in receipt.items" :key="i">
              <td>{{ item.name }}</td>
              <td class="is-num">{{ item.qty }}</td>
              <td class="is-num">{{ money(item.unit_price) }}</td>
              <td class="is-num">{{ money(item.line_total) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Totales -->
      <section class="ec-rp-sec">
        <dl class="ec-rp-totals">
          <div><dt>Subtotal</dt><dd>{{ money(receipt.totals?.subtotal) }}</dd></div>
          <div v-if="Number(receipt.totals?.discount_total) > 0"><dt>Descuento</dt><dd>−{{ money(receipt.totals.discount_total) }}</dd></div>
          <div><dt>{{ receipt.order?.shipping_method === 'home' ? 'Envío' : 'Retiro' }}</dt><dd>{{ receipt.order?.shipping_method === 'home' ? shipCostLabel : 'Sin cargo' }}</dd></div>
          <div class="ec-rp-grand"><dt>Total</dt><dd>{{ money(receipt.totals?.total) }}</dd></div>
        </dl>
      </section>

      <!-- Factura del comercio -->
      <section v-if="receipt.invoice_ref" class="ec-rp-sec ec-rp-invoice">
        <p class="ec-rp-meta">
          Factura/recibo del comercio:
          <a v-if="invoiceUrl" :href="invoiceUrl" target="_blank" rel="noopener" class="ec-rp-link">
            Descargar factura <AppIcon name="external-link" :size="13" aria-hidden="true" />
          </a>
          <strong v-else>{{ receipt.invoice_ref }}</strong>
        </p>
      </section>

      <footer class="ec-rp-foot">
        <p class="ec-rp-legend">{{ receipt.legend || 'Este comprobante no es una factura fiscal — la factura la emite el comercio.' }}</p>
        <p class="ec-rp-meta">Generado por DAVENT · {{ receipt.seller?.store_name || shopName }}</p>
      </footer>
    </article>
  </div>
</template>

<style scoped>
.ec-receiptpg { display: grid; gap: 16px; }
.ec-rp-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ec-rp-actions-right { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.ec-rp-link { display: inline-flex; align-items: center; gap: 6px; color: var(--store-accent, inherit); font-weight: 700; font-size: 14px; text-decoration: underline; text-underline-offset: 3px; }
.ec-rp-card { display: grid; gap: 12px; padding: 24px 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.ec-rp-note { grid-template-columns: auto 1fr; align-items: center; }
.ec-rp-note > div { display: grid; gap: 4px; }
.ec-rp-note-ico { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 50%; background: color-mix(in srgb, var(--sp-danger, #dc2626) 12%, transparent); color: var(--sp-danger, #dc2626); }
.ec-rp-h2 { margin: 0; font-size: 16px; font-weight: 800; }
.ec-rp-error { margin: 0; color: var(--sp-danger, #dc2626); }
.ec-rp-note-acts { grid-column: 1 / -1; display: flex; gap: 10px; flex-wrap: wrap; }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 18px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }

/* Skeletons */
.ec-rp-skel { gap: 14px; }
.ec-sk-line { display: block; height: 12px; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.ec-sk-title { width: 40%; height: 20px; }
.ec-sk-line.short { width: 55%; }
.ec-sk-table { height: 120px; border-radius: calc(var(--sp-radius) * .75); margin-top: 8px; }
@media (prefers-reduced-motion: no-preference) {
  .ec-sk-line { animation: ec-rp-shimmer 1.4s ease-in-out infinite; }
  .ec-sk-line:nth-child(2) { animation-delay: .1s; }
  .ec-sk-line:nth-child(3) { animation-delay: .2s; }
  @keyframes ec-rp-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

/* Documento imprimible */
.ec-rp-doc {
  display: grid; gap: 20px; padding: 30px;
  border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: var(--sp-radius);
  background: var(--sp-card, #fff); color: var(--sp-ink, inherit);
  max-width: 720px; margin-inline: auto; width: 100%;
  box-shadow: var(--sp-shadow-md, 0 12px 34px rgba(0,0,0,.08));
}
.ec-rp-head { display: flex; justify-content: space-between; gap: 20px; flex-wrap: wrap; padding-bottom: 18px; border-bottom: 2px solid var(--sp-ink, currentColor); }
.ec-rp-seller { display: flex; align-items: flex-start; gap: 14px; min-width: 0; }
.ec-rp-logo { width: 52px; height: 52px; object-fit: contain; border-radius: calc(var(--sp-radius) * .5); background: var(--sp-surface, rgba(0,0,0,.04)); flex: none; }
.ec-rp-seller-txt { display: grid; gap: 3px; min-width: 0; }
.ec-rp-store { font-size: 21px; font-weight: 800; letter-spacing: -.01em; }
.ec-rp-meta { margin: 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-rp-order { display: grid; gap: 3px; text-align: right; align-content: start; justify-items: end; }
.ec-rp-kind { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .12em; color: var(--sp-muted, inherit); }
.ec-rp-code { font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-rp-status { font-size: 11.5px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: color-mix(in srgb, var(--store-accent, #111) 12%, transparent); color: var(--store-accent, inherit); }
.ec-rp-order small { font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-rp-sec { display: grid; gap: 10px; }
.ec-rp-sec-title { margin: 0; font-size: 11.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; color: var(--sp-muted, inherit); }
.ec-rp-fields { display: grid; gap: 7px; margin: 0; font-size: 13.5px; }
.ec-rp-fields > div { display: flex; gap: 12px; }
.ec-rp-fields dt { min-width: 96px; flex: none; font-weight: 700; color: var(--sp-muted, inherit); }
.ec-rp-fields dd { margin: 0; }
.ec-rp-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.ec-rp-table th { text-align: left; padding: 8px 10px; border-bottom: 1.5px solid var(--sp-ink, currentColor); font-size: 11.5px; text-transform: uppercase; letter-spacing: .06em; color: var(--sp-muted, inherit); }
.ec-rp-table td { padding: 9px 10px; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.08)); vertical-align: top; }
.ec-rp-table .is-num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.ec-rp-table .is-empty { text-align: center; color: var(--sp-muted, inherit); font-size: 13px; padding: 14px 10px; }
.ec-rp-totals { display: grid; gap: 6px; margin: 0 0 0 auto; min-width: min(300px, 100%); font-size: 14px; }
.ec-rp-totals > div { display: flex; justify-content: space-between; gap: 12px; }
.ec-rp-totals dt { color: var(--sp-muted, inherit); }
.ec-rp-totals dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
.ec-rp-grand { padding-top: 8px; border-top: 1.5px solid var(--sp-ink, currentColor); font-size: 17px; }
.ec-rp-grand dd { font-weight: 800; }
.ec-rp-invoice { padding: 12px 14px; border: 1px dashed var(--sp-line, rgba(0,0,0,.2)); border-radius: calc(var(--sp-radius) * .7); }
.ec-rp-foot { display: grid; gap: 6px; padding-top: 14px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.09)); text-align: center; }
.ec-rp-legend { margin: 0; font-size: 12px; font-weight: 700; color: var(--sp-warning, #B45309); }

.ec-rp-actions .ec-btn-primary:focus-visible, .ec-rp-link:focus-visible { outline: 2px solid var(--store-accent, #111); outline-offset: 2px; }

@media (max-width: 560px) {
  .ec-receiptpg { padding-bottom: 88px; }
  .ec-rp-doc { padding: 20px 16px; }
  .ec-rp-order { text-align: left; justify-items: start; }
  .ec-rp-fields > div { flex-direction: column; gap: 1px; }
  .ec-rp-fields dt { min-width: 0; }
  .ec-rp-note { grid-template-columns: 1fr; justify-items: start; }
  .ec-rp-note-acts { grid-column: auto; }
}

@media print {
  .ec-receiptpg { display: block; }
  .ec-rp-doc {
    border: none; border-radius: 0; padding: 0; max-width: none;
    background: #fff; color: #000; box-shadow: none;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .ec-rp-meta, .ec-rp-fields dt, .ec-rp-order small, .ec-rp-table th, .ec-rp-totals dt, .ec-rp-legend, .ec-rp-kind, .ec-rp-sec-title { color: #444; }
  .ec-rp-status { border: 1px solid #999; color: #333; background: #fff; }
  .ec-rp-head, .ec-rp-grand, .ec-rp-table th { border-color: #000; }
  .ec-rp-table th, .ec-rp-table td { border-color: #bbb; }
  .ec-rp-sec { break-inside: avoid; }
  .ec-rp-doc { break-inside: avoid-page; }
}
</style>

<style>
/* Reglas de impresión sobre elementos del LAYOUT público (header, tab
   bar, footer): no pueden ser scoped — viven en otro componente. Solo
   aplican al imprimir; la página en pantalla no cambia. */
@media print {
  .no-print { display: none !important; }
  .store-page .sp-top,
  .store-page .sp-tabbar,
  .store-page .sp-foot,
  .store-page .sp-skip,
  .store-page .sp-preview-badge,
  .store-page .sp-boot { display: none !important; }
  body { background: #fff !important; }
  @page { margin: 13mm; }
}
</style>
