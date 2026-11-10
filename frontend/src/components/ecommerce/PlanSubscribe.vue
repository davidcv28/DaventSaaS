<script setup>
// Suscripción a un plan REAL de la tienda (StorePlan público): elige medio
// de pago manual (transferencia/whatsapp/efectivo según la config del
// vendedor) y POST /api/customer/subscriptions/<slug>/ → pending +
// instrucciones de pago. Sin sesión abre el modal de auth del layout
// (cart.store.openAuth) y reintenta al volver.
import { ref, computed } from 'vue'
import { useCartStore } from '../../stores/cart.store.js'
import { useCustomerStore } from '../../stores/customer.store.js'
import { membershipPlansApi } from '../../api/membershipPlans.api.js'
import { formatARS } from '../../api/billing.api.js'
import { extractApiError } from '../../api/http.js'
import AppIcon from '../AppIcon.vue'
import PaymentInstructions from './PaymentInstructions.vue'

const props = defineProps({
  slug: { type: String, required: true },
  plan: { type: Object, required: true },   // StorePlanPublicSerializer
  payments: { type: Object, default: null } // payments del endpoint público
})
const emit = defineEmits(['subscribed'])

const cart = useCartStore()
const customer = useCustomerStore()

// Mapa de códigos de beneficio del contrato (memberships/benefits.py).
const BENEFIT_LABELS = {
  digital_card: 'Tarjeta digital de miembro',
  free_shipping: 'Envío gratis',
  exclusive_discounts: 'Descuentos exclusivos',
  exclusive_access: 'Acceso a contenido exclusivo',
}
const benefitLabel = (code) => BENEFIT_LABELS[code] || code

const methods = computed(() => {
  const p = props.payments || {}
  const list = []
  if (p.accept_transfer !== false) list.push({ value: 'transfer', label: 'Transferencia / depósito' })
  if (p.accept_whatsapp !== false) list.push({ value: 'whatsapp', label: 'Coordinar por WhatsApp' })
  if (p.accept_cash) list.push({ value: 'cash', label: 'Efectivo / en persona' })
  return list
})
const paymentMethod = ref('')
const busy = ref(false)
const error = ref('')
const result = ref(null)      // {subscription, payment} tras el POST

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : 'Gratis')
const periodLabel = computed(() => {
  const map = { monthly: 'por mes', yearly: 'por año', custom: '' }
  return map[props.plan?.period] || ''
})

// El `payment` de la respuesta usa las flags del StorePaymentConfig — se
// traduce al shape de PaymentInstructions (mismo que payment_instructions
// de pedidos) para reutilizar el componente.
function instructionsFor(method) {
  //El payload público de planes solo trae flags — las instrucciones de
  //cobro crudas llegan recién en la respuesta autenticada del subscribe.
  const p = result.value?.payment || props.payments || {}
  if (method === 'transfer') {
    return { method: 'transfer', alias: p.transfer_alias, holder: p.transfer_holder, instructions: p.transfer_instructions, deadline_hours: p.deadline_hours }
  }
  if (method === 'whatsapp') {
    const num = String(p.whatsapp_number || '').replace(/\D/g, '')
    return { method: 'whatsapp', url: num ? `https://wa.me/${num}` : '', instructions: p.transfer_instructions, deadline_hours: p.deadline_hours }
  }
  return { method: 'cash', instructions: 'Coordiná el pago en efectivo con el comercio.', deadline_hours: p.deadline_hours }
}
const shownInstructions = computed(() => {
  const method = result.value?.subscription?.payment_method || paymentMethod.value
  return instructionsFor(method)
})

async function subscribe() {
  if (busy.value) return
  error.value = ''
  if (!(await cart.ensureCustomer())) {
    cart.openAuth('login', { action: subscribe })
    return
  }
  busy.value = true
  try {
    const method = paymentMethod.value || 'manual'
    result.value = await membershipPlansApi.subscribe(props.slug, { plan_id: props.plan.id, payment_method: method })
    emit('subscribed', result.value)
  } catch (err) {
    const status = err.response?.status
    if (status === 409) {
      error.value = 'Ya tenés una suscripción en esta tienda. Revisá su estado en tu cuenta.'
      emit('subscribed', null)
    } else {
      const parsed = extractApiError(err)
      error.value = parsed.nonField || parsed.payment_method || parsed.plan_id || 'No pudimos registrar la suscripción.'
    }
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="ec-sub">
    <template v-if="result">
      <p class="ec-sub-ok"><AppIcon name="check" :size="16" aria-hidden="true" /> ¡Listo! Tu suscripción quedó pendiente de acreditación.</p>
      <PaymentInstructions :slug="slug" :instructions="shownInstructions" :total="money(plan.price)" />
      <p class="ec-sub-note">El comercio confirma tu pago y tu membresía se activa. Podés seguirla desde tu cuenta.</p>
    </template>

    <template v-else>
      <div class="ec-sub-price">
        <strong>{{ money(plan.price) }}</strong>
        <span v-if="plan.period_days"> / {{ plan.period_days }} días{{ periodLabel ? ` (${periodLabel})` : '' }}</span>
      </div>
      <ul v-if="plan.benefits?.length || plan.discount_percent" class="ec-sub-benefits">
        <li v-for="b in plan.benefits || []" :key="b">{{ benefitLabel(b) }}</li>
        <li v-if="plan.discount_percent">{{ plan.discount_percent }}% de descuento de miembro</li>
      </ul>
      <div v-if="methods.length" class="ec-sub-methods">
        <label class="sp-field">
          <span class="sp-field-label">Medio de pago</span>
          <select v-model="paymentMethod" class="sp-input" :disabled="busy">
            <option v-for="m in methods" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </label>
        <button type="button" class="ec-btn-primary" :disabled="busy" @click="subscribe">
          {{ busy ? 'Procesando…' : customer.isAuthenticated ? 'Suscribirme' : 'Ingresar para suscribirme' }}
        </button>
        <p v-if="!customer.isAuthenticated" class="ec-sub-hint">Te vamos a pedir que ingreses o crees tu cuenta.</p>
      </div>
      <p v-else class="ec-sub-hint">Esta tienda todavía no configuró medios de pago para suscripciones.</p>
      <p v-if="error" class="sp-form-error" role="alert">{{ error }}</p>
    </template>
  </div>
</template>

<style scoped>
.ec-sub { display: grid; gap: 12px; }
.ec-sub-ok { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 14px; font-weight: 700; color: var(--sp-success); }
.ec-sub-note { margin: 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-sub-price { display: flex; align-items: baseline; gap: 4px; font-size: 15px; }
.ec-sub-price strong { font-size: 24px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-sub-price span { font-size: 13px; color: var(--sp-muted, inherit); }
.ec-sub-benefits { margin: 0; padding-left: 18px; display: grid; gap: 5px; font-size: 13px; line-height: 1.45; }
.ec-sub-methods { display: grid; gap: 10px; }
.ec-sub-hint { margin: 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 14.5px; font-weight: 700; cursor: pointer; }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }
</style>
