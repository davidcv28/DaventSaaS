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

async function copy(text, key) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = key
    setTimeout(() => { if (copied.value === key) copied.value = '' }, 2000)
  } catch { /* clipboard no disponible */ }
}

async function payMp() {
  if (!props.orderToken || paying.value) return
  paying.value = true
  payError.value = ''
  try {
    const data = await orderPublicApi.payMp(props.slug, props.orderToken)
    const url = data?.checkout_url || data?.init_point || data?.sandbox_init_point
    if (url) window.location.assign(url)
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
    <p class="ec-pay-title"><AppIcon name="credit-card" :size="16" aria-hidden="true" /> Cómo pagar tu pedido</p>

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

    <p v-if="instructions.deadline_hours" class="ec-pay-deadline">
      Tenés <strong>{{ instructions.deadline_hours }} h</strong> para completar el pago antes de que el pedido venza.
    </p>
  </div>
</template>

<style scoped>
.ec-pay { display: grid; gap: 10px; padding: 16px 18px; border: 1px solid var(--sp-line, color-mix(in srgb, currentColor 14%, transparent)); border-radius: 14px; background: color-mix(in srgb, var(--store-accent, currentColor) 5%, transparent); }
.ec-pay-title { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 14px; font-weight: 700; }
.ec-pay-text { margin: 0; font-size: 13.5px; line-height: 1.55; color: var(--sp-muted, inherit); }
.ec-pay-data { display: grid; gap: 8px; margin: 0; }
.ec-pay-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ec-pay-row dt { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--sp-muted, inherit); }
.ec-pay-row dd { margin: 0; display: flex; align-items: center; gap: 10px; }
.ec-pay-row code { font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }
.ec-pay-copy { display: inline-flex; align-items: center; gap: 5px; border: 1px solid var(--sp-line, currentColor); border-radius: 8px; padding: 5px 10px; font-size: 12px; font-weight: 600; background: transparent; color: inherit; cursor: pointer; }
.ec-pay-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 18px; border-radius: 12px; font-size: 14px; font-weight: 700; text-decoration: none; border: 1px solid transparent; cursor: pointer; }
.ec-pay-btn.is-wa { background: #25d366; color: #0b3d22; }
.ec-pay-btn.is-mp { background: #00b1ea; color: #fff; }
.ec-pay-btn:disabled { opacity: .6; cursor: default; }
.ec-pay-deadline { margin: 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
</style>
