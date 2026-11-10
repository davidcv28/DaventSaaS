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
const SHIP_LABELS = { home: 'Envío a domicilio', pickup: 'Retiro en el local' }

// invoice_ref puede ser un código/número de factura o una URL a un
// archivo que subió el vendedor — si es URL la mostramos como descarga.
const invoiceUrl = computed(() => {
  const v = String(receipt.value?.invoice_ref || '')
  return /^https?:\/\//i.test(v) ? v : ''
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
      <button v-if="phase === 'ready'" type="button" class="ec-btn-primary" @click="print">
        <AppIcon name="printer" :size="16" aria-hidden="true" /> Imprimir
      </button>
    </div>

    <div v-if="phase === 'loading'" class="ec-rp-card">Cargando el comprobante…</div>

    <div v-else-if="phase === 'error'" class="ec-rp-card">
      <p class="ec-rp-error" role="alert">{{ error }}</p>
      <button type="button" class="ec-btn-primary" @click="load">Reintentar</button>
      <RouterLink :to="catalogoTo" class="ec-rp-link">Volver al catálogo</RouterLink>
    </div>

    <article v-else-if="receipt" class="ec-rp-doc">
      <!-- Encabezado del comercio -->
      <header class="ec-rp-head">
        <div class="ec-rp-seller">
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
        <div class="ec-rp-order">
          <span class="ec-rp-kind">Comprobante</span>
          <strong class="ec-rp-code">{{ receipt.order?.code }}</strong>
          <small>{{ fmtDate(receipt.order?.created_at) }}</small>
          <small v-if="receipt.order?.status">{{ STATUS_LABELS[receipt.order.status] || receipt.order.status }}</small>
        </div>
      </header>

      <!-- Datos del pedido -->
      <section class="ec-rp-sec">
        <dl class="ec-rp-fields">
          <div><dt>Comprador</dt><dd>{{ receipt.customer?.first_name || '—' }}</dd></div>
          <div><dt>Entrega</dt><dd>{{ SHIP_LABELS[receipt.order?.shipping_method] || receipt.order?.shipping_method || '—' }}</dd></div>
          <div v-if="receipt.order?.shipping_method === 'home' && addressLine(receipt.shipping_address)">
            <dt>Dirección</dt><dd>{{ addressLine(receipt.shipping_address) }}</dd>
          </div>
        </dl>
      </section>

      <!-- Ítems -->
      <section class="ec-rp-sec">
        <table class="ec-rp-table">
          <thead>
            <tr><th>Producto</th><th class="is-num">Cant.</th><th class="is-num">Precio</th><th class="is-num">Subtotal</th></tr>
          </thead>
          <tbody>
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
          <div><dt>{{ receipt.order?.shipping_method === 'home' ? 'Envío' : 'Retiro' }}</dt><dd>{{ receipt.order?.shipping_method === 'home' ? money(receipt.totals?.shipping_cost) : 'Sin cargo' }}</dd></div>
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
.ec-rp-link { display: inline-flex; align-items: center; gap: 6px; color: var(--store-accent, inherit); font-weight: 700; font-size: 14px; text-decoration: underline; }
.ec-rp-card { display: grid; gap: 12px; padding: 24px 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.ec-rp-error { margin: 0; color: var(--sp-danger); }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 18px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent, #111); color: var(--store-accent-ink, #fff); font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }

/* Documento imprimible */
.ec-rp-doc {
  display: grid; gap: 18px; padding: 28px;
  border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: var(--sp-radius);
  background: var(--sp-card, #fff); color: var(--sp-ink, inherit);
  max-width: 720px; margin-inline: auto; width: 100%;
}
.ec-rp-head { display: flex; justify-content: space-between; gap: 18px; flex-wrap: wrap; padding-bottom: 16px; border-bottom: 2px solid var(--sp-ink, currentColor); }
.ec-rp-seller { display: grid; gap: 3px; }
.ec-rp-store { font-size: 20px; font-weight: 800; letter-spacing: -.01em; }
.ec-rp-meta { margin: 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-rp-order { display: grid; gap: 2px; text-align: right; align-content: start; }
.ec-rp-kind { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .12em; color: var(--sp-muted, inherit); }
.ec-rp-code { font-size: 17px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-rp-order small { font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-rp-sec { display: grid; gap: 10px; }
.ec-rp-fields { display: grid; gap: 6px; margin: 0; font-size: 13.5px; }
.ec-rp-fields > div { display: flex; gap: 10px; }
.ec-rp-fields dt { min-width: 90px; font-weight: 700; color: var(--sp-muted, inherit); }
.ec-rp-fields dd { margin: 0; }
.ec-rp-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.ec-rp-table th { text-align: left; padding: 8px 10px; border-bottom: 1.5px solid var(--sp-line, rgba(0,0,0,.15)); font-size: 11.5px; text-transform: uppercase; letter-spacing: .06em; color: var(--sp-muted, inherit); }
.ec-rp-table td { padding: 9px 10px; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.07)); vertical-align: top; }
.ec-rp-table .is-num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.ec-rp-totals { display: grid; gap: 6px; margin: 0 0 0 auto; min-width: min(300px, 100%); font-size: 14px; }
.ec-rp-totals > div { display: flex; justify-content: space-between; gap: 12px; }
.ec-rp-totals dt { color: var(--sp-muted, inherit); }
.ec-rp-totals dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
.ec-rp-grand { padding-top: 8px; border-top: 1.5px solid var(--sp-ink, currentColor); font-size: 17px; }
.ec-rp-grand dd { font-weight: 800; }
.ec-rp-invoice { padding: 12px 14px; border: 1px dashed var(--sp-line, rgba(0,0,0,.2)); border-radius: calc(var(--sp-radius) * .7); }
.ec-rp-foot { display: grid; gap: 6px; padding-top: 14px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.09)); text-align: center; }
.ec-rp-legend { margin: 0; font-size: 12px; font-weight: 700; color: var(--sp-muted, inherit); }

@media print {
  .no-print { display: none !important; }
  .ec-receiptpg { display: block; }
  .ec-rp-doc {
    border: none; border-radius: 0; padding: 0; max-width: none;
    background: #fff; color: #000;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .ec-rp-meta, .ec-rp-fields dt, .ec-rp-order small, .ec-rp-table th, .ec-rp-totals dt, .ec-rp-legend, .ec-rp-kind { color: #444; }
  .ec-rp-head, .ec-rp-grand { border-color: #000; }
  .ec-rp-table th, .ec-rp-table td { border-color: #bbb; }
  .ec-rp-sec { break-inside: avoid; }
  .ec-rp-doc { break-inside: avoid-page; }
}
</style>
