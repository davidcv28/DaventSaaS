<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { invoicesApi, formatDate } from '../api/invoices.api.js'
import { formatARS } from '../api/billing.api.js'
import { formatDateTime } from '../api/payments.api.js'
import { extractApiError } from '../api/http.js'
import BrandLogo from '../components/BrandLogo.vue'
import AppIcon from '../components/AppIcon.vue'
import AlertMessage from '../components/AlertMessage.vue'

// Datos fiscales del emisor (DAVENT). Completar CUIT/domicilio cuando estén definidos.
const ISSUER = {
  name: 'DAVENT',
  tagline: 'Plataforma de catálogos digitales',
  cuit: '',
  address: '',
  email: ''
}

const route = useRoute()
const invoice = ref(null)
const status = ref('loading') // loading | ready | error
const error = ref('')

const docTitle = computed(() =>
  invoice.value ? `${invoice.value.type_display} ${invoice.value.comprobante}` : 'Factura'
)

onMounted(async () => {
  try {
    invoice.value = await invoicesApi.getInvoice(route.params.id)
    status.value = 'ready'
    document.title = `DAVENT · ${docTitle.value}`
    await nextTick()
    // Abre el diálogo de impresión una vez renderizado el comprobante.
    setTimeout(() => window.print(), 450)
  } catch (e) {
    status.value = 'error'
    error.value = extractApiError(e).status === 404
      ? 'La factura no existe o no pertenece a tu cuenta.'
      : extractApiError(e).nonField || 'No se pudo cargar la factura.'
  }
})

function print() {
  window.print()
}

function closeTab() {
  window.close()
}
</script>

<template>
  <div class="print-page">
    <div class="print-bar">
      <span class="print-bar-text">Comprobante listo para imprimir o guardar como PDF</span>
      <div class="print-bar-actions">
        <button class="btn btn-auto" type="button" :disabled="status !== 'ready'" @click="print">
          <AppIcon name="printer" :size="16" /> Imprimir / PDF
        </button>
        <button class="btn ghost btn-auto" type="button" @click="closeTab">Cerrar pestaña</button>
      </div>
    </div>

    <div v-if="status === 'loading'" class="print-status">
      <span class="spinner spinner-brand"></span>
      <p>Cargando el comprobante…</p>
    </div>

    <div v-else-if="status === 'error'" class="print-status">
      <AlertMessage kind="error" :message="error" />
    </div>

    <article v-else class="inv-doc">
      <header class="inv-head">
        <div class="inv-brand">
          <BrandLogo :size="46" />
          <div class="inv-brand-text">
            <strong>{{ ISSUER.name }}</strong>
            <span>{{ ISSUER.tagline }}</span>
          </div>
        </div>

        <div class="inv-letter" aria-hidden="true">
          <strong>{{ invoice.type }}</strong>
          <span>ORIGINAL</span>
        </div>

        <div class="inv-meta">
          <strong>{{ invoice.type_display }}</strong>
          <span>Comprobante N° {{ invoice.comprobante }}</span>
          <span>Fecha de emisión: {{ formatDate(invoice.issued_at) }}</span>
          <span v-if="invoice.paid_at">Pago acreditado: {{ formatDateTime(invoice.paid_at) }}</span>
        </div>
      </header>

      <section class="inv-parties">
        <div class="inv-party">
          <h4>Emisor</h4>
          <strong>{{ ISSUER.name }}</strong>
          <span v-if="ISSUER.cuit">CUIT: {{ ISSUER.cuit }}</span>
          <span v-if="ISSUER.address">{{ ISSUER.address }}</span>
          <span v-if="ISSUER.email">{{ ISSUER.email }}</span>
        </div>
        <div class="inv-party">
          <h4>Facturar a</h4>
          <strong>{{ invoice.customer_name }}</strong>
          <span>{{ invoice.type_document }}: {{ invoice.document }}</span>
          <span>Condición fiscal: {{ invoice.tax_condition_display }}</span>
          <span v-if="invoice.address">{{ invoice.address }}<template v-if="invoice.city_name">, {{ invoice.city_name }}</template><template v-if="invoice.province_name"> ({{ invoice.province_name }})</template></span>
        </div>
      </section>

      <table class="inv-items">
        <thead>
          <tr>
            <th>Descripción</th>
            <th class="num">Cantidad</th>
            <th class="num">Precio unitario</th>
            <th class="num">Importe</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Suscripción mensual — {{ invoice.plan_name || 'Plan DAVENT' }}</td>
            <td class="num">1</td>
            <td class="num">{{ formatARS(invoice.total) }}</td>
            <td class="num">{{ formatARS(invoice.total) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="inv-totals">
        <div class="inv-total-row">
          <span>Total</span>
          <strong>{{ formatARS(invoice.total) }}</strong>
        </div>
      </div>

      <footer class="inv-foot">
        <span>Comprobante emitido digitalmente por {{ ISSUER.name }}.</span>
        <span v-if="invoice.currency">Moneda: {{ invoice.currency }}</span>
      </footer>
    </article>
  </div>
</template>

<style scoped>
.print-page { min-height: 100vh; background: var(--bg); padding: 24px 16px 48px; }

.print-bar {
  max-width: 820px; margin: 0 auto 18px; display: flex; align-items: center;
  justify-content: space-between; gap: 14px; flex-wrap: wrap;
}
.print-bar-text { color: var(--muted); font-size: 13.5px; }
.print-bar-actions { display: flex; gap: 10px; }

.print-status {
  max-width: 820px; margin: 60px auto 0; display: grid; justify-items: center;
  gap: 12px; color: var(--muted);
}

/* Documento: siempre claro, es papel impreso aunque el tema sea nocturno. */
.inv-doc {
  max-width: 820px; margin: 0 auto; background: #fff; color: #1e293b;
  border: 1px solid #e2e8f0; border-radius: 14px; padding: 40px 44px;
  box-shadow: 0 12px 32px -16px rgba(15, 23, 42, .25);
}

.inv-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 20px; padding-bottom: 22px; border-bottom: 2px solid #1e293b;
}
.inv-brand { display: flex; align-items: center; gap: 14px; }
.inv-brand-text { display: grid; }
.inv-brand-text strong { font-size: 22px; letter-spacing: .04em; }
.inv-brand-text span { color: #64748b; font-size: 13px; }

.inv-letter {
  width: 64px; flex: none; text-align: center; border: 2px solid #1e293b;
  border-radius: 10px; padding: 8px 0 6px;
}
.inv-letter strong { display: block; font-size: 26px; line-height: 1.1; }
.inv-letter span { font-size: 9.5px; letter-spacing: .08em; color: #64748b; }

.inv-meta { display: grid; justify-items: end; gap: 3px; font-size: 13.5px; }
.inv-meta strong { font-size: 17px; }
.inv-meta span { color: #475569; }

.inv-parties {
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
  padding: 20px 0; border-bottom: 1px solid #e2e8f0;
}
.inv-party { display: grid; gap: 3px; font-size: 13.5px; color: #475569; }
.inv-party h4 {
  margin: 0 0 4px; font-size: 11px; letter-spacing: .07em; text-transform: uppercase;
  color: #94a3b8; font-weight: 600;
}
.inv-party strong { color: #1e293b; font-size: 14.5px; }

.inv-items { width: 100%; border-collapse: collapse; margin: 24px 0 8px; font-size: 13.5px; }
.inv-items th {
  text-align: left; font-size: 11px; letter-spacing: .07em; text-transform: uppercase;
  color: #64748b; font-weight: 600; padding: 9px 12px; border-bottom: 1.5px solid #cbd5e1;
}
.inv-items td { padding: 12px; border-bottom: 1px solid #e2e8f0; }
.inv-items .num { text-align: right; white-space: nowrap; }

.inv-totals { display: flex; justify-content: flex-end; margin-top: 6px; }
.inv-total-row {
  display: flex; justify-content: space-between; gap: 40px; min-width: 260px;
  padding: 12px 14px; border-top: 2px solid #1e293b; font-size: 15px;
}
.inv-total-row strong { font-size: 18px; }

.inv-foot {
  margin-top: 34px; padding-top: 14px; border-top: 1px solid #e2e8f0;
  display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  color: #94a3b8; font-size: 12px;
}

@media (max-width: 640px) {
  .inv-doc { padding: 26px 20px; }
  .inv-parties { grid-template-columns: 1fr; }
  .inv-head { flex-wrap: wrap; }
  .inv-meta { justify-items: start; }
}

@page { size: A4; margin: 14mm; }
@media print {
  .print-page { background: #fff; padding: 0; }
  .print-bar, .print-status { display: none; }
  .inv-doc { border: none; box-shadow: none; border-radius: 0; max-width: none; margin: 0; }
}
</style>
