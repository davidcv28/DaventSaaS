<script setup>
// Checkout del comprador: /<slug>/checkout (o /checkout en subdominio).
// Requiere sesión de cliente (customer JWT — NO la DAVENT del dueño).
// Precios SIEMPRE del server: el resumen muestra el carrito server-side
// (cartApi) y el total final lo fija create_order — el front no recalcula.
//
// Flujo: ensureSession → carrito + direcciones + métodos de pago →
// captcha firmado → POST orders con idempotency_key por intento →
// redirect a seguimiento con ?token= (el tracking_token es la credencial).
import { ref, computed, inject, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '../stores/cart.store.js'
import { useCustomerStore } from '../stores/customer.store.js'
import { customerApi } from '../api/customer.api.js'
import { orderCaptchaApi } from '../api/cart.api.js'
import { orderPublicApi } from '../api/storeorders.api.js'
import { membershipPlansApi } from '../api/membershipPlans.api.js'
import { formatARS } from '../api/billing.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import CaptchaField from '../components/ecommerce/CaptchaField.vue'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const ordersEnabled = computed(() => Boolean(ctx?.ordersEnabled?.value ?? ctx?.ordersEnabled))
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')

const router = useRouter()
const cart = useCartStore()
const customer = useCustomerStore()

const seguimientoTo = computed(() => (token) => ({
  path: storeHostSlug ? '/seguimiento' : `/${slug.value}/seguimiento`,
  query: { token }
}))
const cuentaTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta` }))
const catalogoTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))

// ---------- estado ----------
const phase = ref('loading') // loading | auth | empty | form | done
const addresses = ref([])
const payments = ref(null)
const submitting = ref(false)
const error = ref('')
const fieldErrors = ref({})

const form = ref({
  shipping_method: 'home',
  address_mode: 'saved',     // 'saved' | 'new'
  address_id: null,
  address: { label: '', line1: '', line2: '', city: '', province: '', postal_code: '', country: 'AR' },
  save_address: false,
  payment_method: '',
  website: ''                // honeypot — NUNCA se llena desde la UI
})

// Idempotency key por intento de checkout: se genera al entrar y se
// regenera tras un pedido creado o si cambia el carrito (evita que un
// retry devuelva un pedido viejo con otro contenido).
const idemKey = ref('')
function newIdemKey() { idemKey.value = (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`) }

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')

const captchaRef = ref(null)

const addressReady = computed(() => {
  if (form.value.shipping_method === 'pickup') return true
  if (form.value.address_mode === 'saved') return Boolean(form.value.address_id)
  const a = form.value.address
  return Boolean(a.line1?.trim() && a.city?.trim() && a.province?.trim())
})

const paymentMethods = computed(() => {
  const p = payments.value || {}
  const list = []
  if (p.accept_transfer !== false) list.push({ value: 'transfer', label: 'Transferencia / depósito' })
  if (p.accept_whatsapp !== false) list.push({ value: 'whatsapp', label: 'Coordinar por WhatsApp' })
  if (p.accept_cash) list.push({ value: 'cash', label: 'Efectivo / en persona' })
  if (p.mp_connected) list.push({ value: 'mp', label: 'Mercado Pago' })
  return list
})

// El captcha no entra en canSubmit: su `answer` vive en el hijo y no es
// trackeable desde este computed — se valida en submit().
const canSubmit = computed(() => (
  phase.value === 'form' && !submitting.value && cart.hasItems &&
  addressReady.value && form.value.payment_method
))

// ---------- carga ----------
async function load() {
  phase.value = 'loading'
  error.value = ''
  if (!ordersEnabled.value) { phase.value = 'form'; return }
  const ok = await cart.ensureCustomer()
  if (!ok) {
    phase.value = 'auth'
    // El modal global se abre solo si el usuario toca "Ingresar"; acá
    // dejamos el prompt visible con botón (menos invasivo que auto-abrir).
    return
  }
  await Promise.all([loadCart(), loadAddresses(), loadPayments()])
  if (cart.hasItems) {
    newIdemKey()
    phase.value = 'form'
  } else {
    phase.value = 'empty'
  }
}

async function loadCart() {
  await cart.refresh()
}
async function loadAddresses() {
  try {
    const data = await customerApi.listAddresses()
    addresses.value = Array.isArray(data) ? data : (data?.results || [])
    const def = addresses.value.find((a) => a.is_default) || addresses.value[0]
    form.value.address_id = def?.id || null
    form.value.address_mode = def ? 'saved' : 'new'
  } catch { addresses.value = [] }
}
async function loadPayments() {
  try {
    const data = await membershipPlansApi.publicPlans(slug.value)
    payments.value = data?.payments || null
    const methods = paymentMethods.value
    form.value.payment_method = methods[0]?.value || ''
  } catch { payments.value = null }
}

function openAuth() {
  cart.openAuth('login', { route: cuentaTo.value })
}

// ---------- submit ----------
function fieldErr(name) { return fieldErrors.value[name] || '' }

async function submit() {
  if (submitting.value || !canSubmit.value) return
  const captcha = captchaRef.value?.payload?.()
  if (!captcha) {
    error.value = 'Completá la verificación para continuar.'
    return
  }
  submitting.value = true
  error.value = ''
  fieldErrors.value = {}
  try {
    const payload = {
      use_cart: true,
      shipping_method: form.value.shipping_method,
      payment_method: form.value.payment_method,
      idempotency_key: idemKey.value,
      ...captcha,
      website: form.value.website || '',
    }
    // "Guardar dirección": se persiste ANTES de crear el pedido y se
    // referencia por address_id (así el pedido guarda el snapshot).
    if (form.value.shipping_method === 'home' && form.value.address_mode === 'new' && form.value.save_address) {
      const a = form.value.address
      const saved = await customerApi.createAddress({
        label: a.label || '', line1: a.line1, line2: a.line2 || '',
        city: a.city, province: a.province, postal_code: a.postal_code || '',
        country: a.country || 'AR',
      }).catch(() => null)
      if (saved?.id) payload.address_id = saved.id
      else payload.address = { ...a }
    } else if (form.value.shipping_method === 'home' || form.value.address_mode === 'saved') {
      if (form.value.address_mode === 'saved' && form.value.address_id) {
        payload.address_id = form.value.address_id
      } else {
        payload.address = { ...form.value.address }
      }
    }
    const res = await orderPublicApi.create(slug.value, payload)
    const token = res?.tracking_token
    // El server ya vació el carrito — refrescar para reflejarlo.
    cart.cart = null
    cart.status = 'idle'
    phase.value = 'done'
    if (token) router.push(seguimientoTo.value(token))
  } catch (err) {
    const parsed = extractApiError(err)
    const { nonField, status: _s, ...fields } = parsed
    fieldErrors.value = fields
    error.value = nonField || Object.values(fields)[0] || 'No pudimos crear el pedido. Revisá los datos e intentá de nuevo.'
    if (fields.captcha_answer || fields.challenge_id) captchaRef.value?.refresh()
    // Si el server rechazó por carrito vacío/sesión, recargar estado.
    if (err.response?.status === 401 || err.response?.status === 403) load()
  } finally {
    submitting.value = false
  }
}

// Si el carrito queda vacío mientras el usuario está en el form (otra
// pestaña compró), el submit fallará — el watcher lleva a 'empty'.
watch(() => cart.hasItems, (has) => {
  if (phase.value === 'form' && !has) phase.value = 'empty'
})

onMounted(load)
</script>

<template>
  <div class="sp-page-root ec-checkout">
    <header class="ec-co-head">
      <h1 class="ec-co-title">Finalizar compra</h1>
      <p class="ec-co-sub">{{ shopName }} · revisá tu pedido y elegí cómo pagar</p>
    </header>

    <!-- Tienda sin venta online -->
    <div v-if="!ordersEnabled" class="ec-co-card">
      <p><AppIcon name="package" :size="22" aria-hidden="true" /> Esta tienda todavía no vende online.</p>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ver catálogo</RouterLink>
    </div>

    <!-- Sin sesión -->
    <div v-else-if="phase === 'auth'" class="ec-co-card">
      <h2 class="ec-co-h2">Iniciá sesión para comprar</h2>
      <p class="ec-co-muted">Necesitás una cuenta de comprador para finalizar el pedido y seguirlo después.</p>
      <button type="button" class="ec-btn-primary" @click="openAuth">Ingresar o crear cuenta</button>
      <RouterLink :to="cuentaTo" class="ec-co-link">Ya tengo cuenta — ir a mi cuenta</RouterLink>
    </div>

    <!-- Carrito vacío -->
    <div v-else-if="phase === 'empty'" class="ec-co-card">
      <h2 class="ec-co-h2">Tu carrito está vacío</h2>
      <p class="ec-co-muted">Agregá productos del catálogo antes de pagar.</p>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ir al catálogo</RouterLink>
    </div>

    <div v-else-if="phase === 'loading'" class="ec-co-card ec-co-loading">Cargando tu pedido…</div>

    <!-- Formulario -->
    <div v-else class="ec-co-grid">
      <form class="ec-co-main" novalidate @submit.prevent="submit">
        <section class="ec-co-card">
          <h2 class="ec-co-h2">Entrega</h2>
          <div class="ec-co-ship">
            <label class="ec-co-opt" :class="{ 'is-on': form.shipping_method === 'home' }">
              <input v-model="form.shipping_method" type="radio" value="home" :disabled="submitting" />
              <span><strong>Envío a domicilio</strong><small>Te lo llevamos a tu dirección</small></span>
            </label>
            <label class="ec-co-opt" :class="{ 'is-on': form.shipping_method === 'pickup' }">
              <input v-model="form.shipping_method" type="radio" value="pickup" :disabled="submitting" />
              <span><strong>Retiro en el local</strong><small>Pasás a buscarlo cuando esté listo</small></span>
            </label>
          </div>

          <template v-if="form.shipping_method === 'home'">
            <div v-if="addresses.length" class="ec-co-addr-mode">
              <label class="ec-co-opt is-inline" :class="{ 'is-on': form.address_mode === 'saved' }">
                <input v-model="form.address_mode" type="radio" value="saved" :disabled="submitting" />
                <span>Usar una dirección guardada</span>
              </label>
              <label class="ec-co-opt is-inline" :class="{ 'is-on': form.address_mode === 'new' }">
                <input v-model="form.address_mode" type="radio" value="new" :disabled="submitting" />
                <span>Cargar otra dirección</span>
              </label>
            </div>

            <div v-if="form.address_mode === 'saved' && addresses.length" class="ec-co-addrs">
              <label v-for="a in addresses" :key="a.id" class="ec-co-addr" :class="{ 'is-on': form.address_id === a.id }">
                <input v-model="form.address_id" type="radio" :value="a.id" name="addr" :disabled="submitting" />
                <span>
                  <strong>{{ a.label || 'Dirección' }}{{ a.is_default ? ' · principal' : '' }}</strong>
                  <small>{{ [a.line1, a.line2, a.city, a.province, a.postal_code].filter(Boolean).join(', ') }}</small>
                </span>
              </label>
              <p v-if="fieldErr('address_id')" class="sp-form-error" role="alert">{{ fieldErr('address_id') }}</p>
            </div>

            <div v-else class="ec-co-addrform">
              <label class="sp-field">
                <span class="sp-field-label">Calle y número *</span>
                <input v-model="form.address.line1" class="sp-input" type="text" maxlength="160" :disabled="submitting" />
              </label>
              <label class="sp-field">
                <span class="sp-field-label">Departamento / piso / referencia</span>
                <input v-model="form.address.line2" class="sp-input" type="text" maxlength="160" :disabled="submitting" />
              </label>
              <div class="ec-co-grid2">
                <label class="sp-field">
                  <span class="sp-field-label">Ciudad *</span>
                  <input v-model="form.address.city" class="sp-input" type="text" maxlength="120" :disabled="submitting" />
                </label>
                <label class="sp-field">
                  <span class="sp-field-label">Provincia *</span>
                  <input v-model="form.address.province" class="sp-input" type="text" maxlength="120" :disabled="submitting" />
                </label>
              </div>
              <div class="ec-co-grid2">
                <label class="sp-field">
                  <span class="sp-field-label">Código postal</span>
                  <input v-model="form.address.postal_code" class="sp-input" type="text" maxlength="20" :disabled="submitting" />
                </label>
                <label class="sp-field">
                  <span class="sp-field-label">Nombre del lugar (opcional)</span>
                  <input v-model="form.address.label" class="sp-input" type="text" maxlength="40" placeholder="Ej: Casa, Oficina" :disabled="submitting" />
                </label>
              </div>
              <label class="ec-co-save">
                <input v-model="form.save_address" type="checkbox" :disabled="submitting" />
                <span>Guardar esta dirección en mi cuenta</span>
              </label>
              <p v-if="fieldErr('address')" class="sp-form-error" role="alert">{{ fieldErr('address') }}</p>
            </div>
          </template>
          <p v-else class="ec-co-muted">Retirás el pedido en el local de {{ shopName }}. Te avisamos cuando esté listo.</p>
        </section>

        <section class="ec-co-card">
          <h2 class="ec-co-h2">Pago</h2>
          <div class="ec-co-pay">
            <label v-for="m in paymentMethods" :key="m.value" class="ec-co-opt" :class="{ 'is-on': form.payment_method === m.value }">
              <input v-model="form.payment_method" type="radio" :value="m.value" name="pay" :disabled="submitting" />
              <span>{{ m.label }}</span>
            </label>
            <p v-if="!paymentMethods.length" class="sp-form-error" role="alert">Esta tienda no tiene medios de pago habilitados.</p>
          </div>
          <p v-if="form.payment_method === 'mp'" class="ec-co-muted">Te llevamos a Mercado Pago para pagar; la acreditación es automática.</p>
          <p v-else-if="form.payment_method" class="ec-co-muted">Te mostramos las instrucciones para pagar una vez creado el pedido.</p>
          <p v-if="fieldErr('payment_method')" class="sp-form-error" role="alert">{{ fieldErr('payment_method') }}</p>

          <CaptchaField ref="captchaRef" :slug="slug" :load="orderCaptchaApi.get" />
          <p v-if="fieldErr('captcha_answer') || fieldErr('challenge_id')" class="sp-form-error" role="alert">
            {{ fieldErr('captcha_answer') || fieldErr('challenge_id') }}
          </p>
          <!-- Honeypot: invisible para humanos — si viene con valor el server lo rechaza. -->
          <input v-model="form.website" type="text" name="website" class="ec-hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
        </section>

        <p v-if="error" class="sp-form-error ec-co-error" role="alert">{{ error }}</p>

        <button type="submit" class="ec-btn-primary ec-co-submit" :disabled="!canSubmit">
          {{ submitting ? 'Creando tu pedido…' : 'Confirmar pedido' }}
        </button>
        <p class="ec-co-muted ec-co-fine">Al confirmar aceptás los <RouterLink :to="{ path: storeHostSlug ? '/legal/terminos' : `/${slug}/legal/terminos` }" target="_blank">términos y condiciones</RouterLink> de la tienda.</p>
      </form>

      <!-- Resumen del carrito (server-side) -->
      <aside class="ec-co-side">
        <section class="ec-co-card">
          <h2 class="ec-co-h2">Tu pedido</h2>
          <ul class="ec-co-items">
            <li v-for="item in cart.items" :key="item.id">
              <img v-if="item.image" :src="item.image" :alt="item.name" class="ec-co-thumb" loading="lazy" />
              <div v-else class="ec-co-thumb is-empty" aria-hidden="true"><AppIcon name="package" :size="16" /></div>
              <div class="ec-co-item-info">
                <span class="ec-co-item-name">{{ item.name }}</span>
                <small>{{ item.qty }} × {{ money(item.unit_price) }}</small>
              </div>
              <strong class="ec-co-item-total">{{ money(item.line_total) }}</strong>
            </li>
          </ul>
          <dl class="ec-co-totals">
            <div><dt>Subtotal</dt><dd>{{ money(cart.itemsTotal) }}</dd></div>
            <div v-if="cart.memberDiscount"><dt>Descuento de miembro</dt><dd>−{{ cart.memberDiscount }}%</dd></div>
            <div><dt>Envío</dt><dd>{{ form.shipping_method === 'pickup' ? 'Retiro sin cargo' : 'A coordinar' }}</dd></div>
            <div class="ec-co-grand"><dt>Total estimado</dt><dd>{{ money(cart.itemsTotal) }}</dd></div>
          </dl>
          <p class="ec-co-muted">El total final lo confirma el servidor al crear el pedido.</p>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.ec-checkout { display: grid; gap: 18px; }
.ec-co-head { display: grid; gap: 4px; }
.ec-co-title { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.ec-co-sub { margin: 0; font-size: 14px; color: var(--sp-muted, inherit); }
.ec-co-h2 { margin: 0 0 12px; font-size: 16px; font-weight: 800; }
.ec-co-card { display: grid; gap: 14px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: 16px; background: var(--sp-card, transparent); }
.ec-co-muted { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }
.ec-co-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; align-items: start; }
.ec-co-main { display: grid; gap: 16px; min-width: 0; }
.ec-co-side { position: sticky; top: 90px; }
.ec-co-ship, .ec-co-pay { display: grid; gap: 8px; }
.ec-co-opt { display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: 12px; cursor: pointer; }
.ec-co-opt.is-on { border-color: var(--store-accent, #111); box-shadow: 0 0 0 1px var(--store-accent, #111) inset; }
.ec-co-opt.is-inline { padding: 9px 12px; }
.ec-co-opt input { margin-top: 3px; accent-color: var(--store-accent, #111); }
.ec-co-opt span { display: grid; gap: 2px; font-size: 14px; }
.ec-co-opt small { font-size: 12px; color: var(--sp-muted, inherit); }
.ec-co-addr-mode { display: grid; gap: 6px; }
.ec-co-addrs { display: grid; gap: 8px; }
.ec-co-addr { display: flex; align-items: flex-start; gap: 10px; padding: 11px 13px; border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: 12px; cursor: pointer; }
.ec-co-addr.is-on { border-color: var(--store-accent, #111); }
.ec-co-addr input { margin-top: 3px; accent-color: var(--store-accent, #111); }
.ec-co-addr span { display: grid; gap: 2px; }
.ec-co-addr small { font-size: 12px; color: var(--sp-muted, inherit); }
.ec-co-addrform { display: grid; gap: 12px; }
.ec-co-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ec-co-save { display: flex; align-items: center; gap: 9px; font-size: 13.5px; cursor: pointer; }
.ec-co-items { list-style: none; margin: 0 0 12px; padding: 0; display: grid; gap: 10px; max-height: 320px; overflow-y: auto; }
.ec-co-items li { display: grid; grid-template-columns: 44px 1fr auto; gap: 10px; align-items: center; }
.ec-co-thumb { width: 44px; height: 44px; object-fit: cover; border-radius: 9px; background: var(--sp-line, rgba(0,0,0,.06)); }
.ec-co-thumb.is-empty { display: grid; place-items: center; color: var(--sp-muted, inherit); }
.ec-co-item-info { display: grid; gap: 2px; min-width: 0; }
.ec-co-item-name { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ec-co-item-info small { font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-co-item-total { font-size: 13px; font-variant-numeric: tabular-nums; }
.ec-co-totals { margin: 0; display: grid; gap: 6px; }
.ec-co-totals div { display: flex; justify-content: space-between; font-size: 13.5px; }
.ec-co-totals dt { color: var(--sp-muted, inherit); }
.ec-co-totals dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
.ec-co-grand { padding-top: 8px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.1)); font-size: 15px !important; }
.ec-co-grand dt { font-weight: 700; color: inherit !important; }
.ec-co-grand dd { font-size: 18px; font-weight: 800; }
.ec-co-submit { width: 100%; padding: 14px; border: none; border-radius: 13px; background: var(--store-accent, #111); color: var(--store-accent-ink, #fff); font-size: 15.5px; font-weight: 800; cursor: pointer; }
.ec-co-submit:disabled { opacity: .5; cursor: default; }
.ec-co-error { padding: 10px 12px; border-radius: 10px; }
.ec-co-link { font-size: 13px; font-weight: 600; color: var(--store-accent, inherit); }
.ec-co-loading { padding: 40px; text-align: center; color: var(--sp-muted, inherit); }
.ec-co-fine { text-align: center; }
.ec-hp { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }
@media (max-width: 900px) { .ec-co-grid { grid-template-columns: 1fr; } .ec-co-side { position: static; } }
@media (max-width: 560px) { .ec-co-grid2 { grid-template-columns: 1fr; } }
</style>
