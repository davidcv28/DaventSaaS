<script setup>
// Instrucciones de pago de un pedido/suscripción pendiente, armadas por el
// servidor (payment_instructions del payload — nunca hardcodear alias ni
// montos). Cubre los 4 métodos: transfer (alias/holder + copiar), whatsapp
// (botón wa.me), cash (texto) y mp (botón que pide la preferencia y
// redirige a Mercado Pago — solo si llega `orderToken`).
import { ref, computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import { orderPublicApi } from '../../api/storeorders.api.js'
import { extractApiError } from '../../api/http.js'

const props = defineProps({
  slug: { type: String, required: true },
  instructions: { type: Object, default: null },
  // tracking_token del pedido — habilita el botón "Pagar con Mercado Pago".
  orderToken: { type: String, default: '' },
  total: { type: String, default: '' }
})

const copied = ref('')
const paying = ref(false)
const payError = ref('')

const method = computed(() => props.instructions?.method || '')
const METHOD_ICON = { transfer: 'building-2', whatsapp: 'whatsapp', cash: 'wallet', mp: 'credit-card' }
const methodIcon = computed(() => METHOD_ICON[method.value] || 'credit-card')

async function copy(text, key) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = key
    setTimeout(() => { if (copied.value === key) copied.value = '' }, 2000)
  } catch { /* clipboard no disponible */ }
}

// La URL de checkout viene del backend (preferencia de MP), pero se
// revalida acá: solo hosts oficiales de Mercado Pago pueden recibir el
// redirect — defensa en profundidad ante un upstream comprometido.
const MP_HOST_RE = /(^|\.)(mercadopago|mercadolibre)\.[a-z.]+$|(^|\.)mpago\.la$/
function isMpCheckoutUrl(url) {
  try {
    const u = new URL(url)
    return u.protocol === 'https:' && MP_HOST_RE.test(u.hostname.toLowerCase())
  } catch {
    return false
  }
}

async function payMp() {
  if (!props.orderToken || paying.value) return
  paying.value = true
  payError.value = ''
  try {
    const data = await orderPublicApi.payMp(props.slug, props.orderToken)
    const url = data?.checkout_url || data?.init_point || data?.sandbox_init_point
    if (url && isMpCheckoutUrl(url)) window.location.assign(url)
    else if (url) payError.value = 'Enlace de pago no válido.'
    else payError.value = 'No pudimos iniciar el pago. Intentá de nuevo.'
  } catch (err) {
    payError.value = extractApiError(err).nonField || 'No pudimos iniciar el pago con Mercado Pago.'
  } finally {
    paying.value = false
  }
}
</script>

<template>
  <div v-if="instructions" class="ec-pay">
    <p class="ec-pay-title"><span class="ec-pay-ico" aria-hidden="true"><AppIcon :name="methodIcon" :size="16" /></span> Cómo pagar tu pedido</p>

    <!-- Transferencia / depósito -->
    <template v-if="method === 'transfer'">
      <p class="ec-pay-text">Transferí o depositá el total en la cuenta del comercio y después subí el comprobante.</p>
      <dl v-if="instructions.alias || instructions.holder" class="ec-pay-data">
        <div v-if="instructions.alias" class="ec-pay-row">
          <dt>Alias</dt>
          <dd>
            <code>{{ instructions.alias }}</code>
            <button type="button" class="ec-pay-copy" @click="copy(instructions.alias, 'alias')">
              <AppIcon :name="copied === 'alias' ? 'check' : 'copy'" :size="14" />
              {{ copied === 'alias' ? 'Copiado' : 'Copiar' }}
            </button>
          </dd>
        </div>
        <div v-if="instructions.holder" class="ec-pay-row">
          <dt>Titular</dt>
          <dd>{{ instructions.holder }}</dd>
        </div>
      </dl>
      <p v-if="instructions.instructions" class="ec-pay-text">{{ instructions.instructions }}</p>
    </template>

    <!-- Coordinar por WhatsApp -->
    <template v-else-if="method === 'whatsapp'">
      <p class="ec-pay-text">El pago se coordina por WhatsApp con el comercio.</p>
      <a v-if="instructions.url" class="ec-pay-btn is-wa" :href="instructions.url" target="_blank" rel="noopener">
        <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Escribir por WhatsApp
      </a>
      <p v-if="instructions.instructions" class="ec-pay-text">{{ instructions.instructions }}</p>
    </template>

    <!-- Efectivo / en persona -->
    <template v-else-if="method === 'cash'">
      <p class="ec-pay-text">{{ instructions.instructions || 'Coordiná el pago en efectivo con el comercio.' }}</p>
    </template>

    <!-- Mercado Pago -->
    <template v-else-if="method === 'mp'">
      <p class="ec-pay-text">Pagá con Mercado Pago: el acreditación es automática.</p>
      <button v-if="orderToken" type="button" class="ec-pay-btn is-mp" :disabled="paying" @click="payMp">
        <AppIcon name="credit-card" :size="17" aria-hidden="true" /> {{ paying ? 'Abriendo Mercado Pago…' : 'Pagar con Mercado Pago' }}
      </button>
      <p v-else class="ec-pay-text">{{ instructions.instructions }}</p>
      <p v-if="payError" class="sp-form-error" role="alert">{{ payError }}</p>
    </template>

    <p v-if="total" class="ec-pay-total"><span>Total a pagar</span><strong>{{ total }}</strong></p>
    <p v-if="instructions.deadline_hours" class="ec-pay-deadline">
      <AppIcon name="clock" :size="13" aria-hidden="true" />
      Tenés <strong>{{ instructions.deadline_hours }} h</strong> para completar el pago antes de que el pedido venza.
    </p>
  </div>
</template>

<style scoped>
.ec-pay { display: grid; gap: 12px; padding: 16px 18px; border: 1px solid var(--sp-line, color-mix(in srgb, currentColor 14%, transparent)); border-left: 3px solid var(--store-accent, currentColor); border-radius: calc(var(--sp-radius) * .85); background: color-mix(in srgb, var(--store-accent, currentColor) 5%, transparent); }
.ec-pay-title { display: flex; align-items: center; gap: 9px; margin: 0; font-size: 14px; font-weight: 800; }
.ec-pay-ico { display: grid; place-items: center; width: 30px; height: 30px; border-radius: calc(var(--sp-radius) * .55); background: color-mix(in srgb, var(--store-accent, currentColor) 13%, transparent); color: var(--store-accent, inherit); flex: none; }
.ec-pay-text { margin: 0; font-size: 13.5px; line-height: 1.55; color: var(--sp-muted, inherit); }
.ec-pay-data { display: grid; gap: 8px; margin: 0; }
.ec-pay-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; padding: 9px 12px; border: 1px solid var(--sp-line, color-mix(in srgb, currentColor 12%, transparent)); border-radius: calc(var(--sp-radius) * .6); background: color-mix(in srgb, var(--sp-card, #fff) 55%, transparent); }
.ec-pay-row dt { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--sp-muted, inherit); }
.ec-pay-row dd { margin: 0; display: flex; align-items: center; gap: 10px; }
.ec-pay-row code { font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }
.ec-pay-copy { display: inline-flex; align-items: center; gap: 5px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .5); padding: 5px 10px; font-size: 12px; font-weight: 600; background: transparent; color: inherit; cursor: pointer; transition: background .15s, border-color .15s; }
.ec-pay-copy:hover { background: color-mix(in srgb, currentColor 8%, transparent); border-color: var(--store-accent, currentColor); }
.ec-pay-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 18px; border-radius: calc(var(--sp-radius) * .75); font-size: 14px; font-weight: 700; text-decoration: none; border: 1px solid transparent; cursor: pointer; transition: filter .15s; }
.ec-pay-btn:hover { filter: brightness(1.06); }
.ec-pay-btn.is-wa { background: #25d366; color: #0b3d22; }
.ec-pay-btn.is-mp { background: #00b1ea; color: #fff; }
.ec-pay-btn:disabled { opacity: .6; cursor: default; }
.ec-pay-total { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin: 0; padding: 10px 2px 0; border-top: 1px dashed var(--sp-line, color-mix(in srgb, currentColor 16%, transparent)); font-size: 13px; color: var(--sp-muted, inherit); }
.ec-pay-total strong { font-size: 17px; font-weight: 800; font-variant-numeric: tabular-nums; color: var(--sp-ink, inherit); }
.ec-pay-deadline { display: flex; align-items: center; gap: 7px; margin: 0; padding: 9px 12px; border-radius: calc(var(--sp-radius) * .6); font-size: 12.5px; color: var(--sp-warning, #B45309); background: color-mix(in srgb, var(--sp-warning, #B45309) 10%, transparent); }
.ec-pay-copy:focus-visible, .ec-pay-btn:focus-visible { outline: 2px solid var(--store-accent, #111); outline-offset: 2px; }
</style>
