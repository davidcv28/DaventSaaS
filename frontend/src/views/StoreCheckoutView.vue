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
const legalTo = computed(() => ({ path: storeHostSlug ? '/legal/terminos' : `/${slug.value}/legal/terminos` }))

// ---------- estado ----------
const phase = ref('loading') // loading | auth | empty | form | done
const addresses = ref([])
const payments = ref(null)
const submitting = ref(false)
const error = ref('')
const fieldErrors = ref({})
const summaryOpen = ref(false)   // resumen colapsable en mobile

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
const itemNoun = computed(() => (cart.itemCount === 1 ? 'producto' : 'productos'))

const captchaRef = ref(null)

const addressReady = computed(() => {
  if (form.value.shipping_method === 'pickup') return true
  // "Guardada" solo cuenta si hay direcciones cargadas: si la lista falló
  // o está vacía el formulario muestra el alta nueva igualmente.
  if (form.value.address_mode === 'saved' && addresses.value.length) return Boolean(form.value.address_id)
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

// Icono + descripción por método (solo presentación — el server decide
// qué métodos están habilitados vía `payments`).
const PAYMENT_UI = {
  transfer: { icon: 'building-2', hint: 'Transferí o depositá en la cuenta del comercio y después subí el comprobante.' },
  whatsapp: { icon: 'whatsapp', hint: 'El pago se coordina por WhatsApp con el comercio.' },
  cash:     { icon: 'wallet',       hint: 'Pagás en efectivo al retirar el pedido o al recibirlo.' },
  mp:       { icon: 'credit-card',  hint: 'Te llevamos a Mercado Pago para pagar; la acreditación es automática.' },
}
const payUi = computed(() => PAYMENT_UI[form.value.payment_method] || null)
const payIcon = (v) => PAYMENT_UI[v]?.icon || 'credit-card'
const payHint = (v) => PAYMENT_UI[v]?.hint || ''

// Stepper del checkout: refleja el avance REAL del formulario (entrega
// completa → pago elegido → confirmar). No es decorativo ni salta pasos.
const CO_STEPS = ['Entrega', 'Pago', 'Confirmar']
const stepIndex = computed(() => {
  if (!addressReady.value) return 0
  if (!form.value.payment_method) return 1
  return 2
})

// El captcha no entra en canSubmit: su `answer` vive en el hijo y no es
// trackeable desde este computed — se valida en submit(). Tampoco la
// entrega/pago: el botón queda habilitado para que el submit muestre los
// errores inline en vez de quedar muerto sin feedback.
const canSubmit = computed(() => (
  phase.value === 'form' && !submitting.value && cart.hasItems
))

// ---------- carga ----------
async function load() {
  phase.value = 'loading'
  error.value = ''
  if (!ordersEnabled.value) { phase.value = 'form'; return }
  const ok = await cart.ensureCustomer()
  if (!ok) {
    phase.value = 'auth'
    // Sesión de comprador requerida: preferir la ruta dedicada de auth
    // (la crea el track de StoreAuthView en paralelo); si todavía no
    // existe, abrir el modal global con la ruta de vuelta al checkout.
    goAuth()
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

// Auth del comprador: ruta dedicada 'store-auth' si existe (modo login +
// next = página actual); fallback al modal global del layout.
function goAuth() {
  const current = router.currentRoute.value
  const next = current.fullPath || current.path
  if (router.hasRoute('store-auth')) {
    router.push({ name: 'store-auth', query: { mode: 'login', next } })
  } else {
    cart.openAuth('login', { route: next })
  }
}

// Si el login vuelve sin navegar (pending.route = esta misma página), el
// watcher de sesión dispara la carga y el checkout continúa solo.
watch(() => customer.isAuthenticated, (authed) => {
  if (authed && phase.value === 'auth') load()
})

// ---------- submit ----------
function fieldErr(name) { return fieldErrors.value[name] || '' }
function clearFieldError(name) {
  if (!fieldErrors.value[name]) return
  const next = { ...fieldErrors.value }
  delete next[name]
  fieldErrors.value = next
}

// Validación cliente del checkout: envío a domicilio exige dirección
// (guardada o calle/ciudad/provincia nuevas); retiro en el local queda
// exento. El pago siempre es obligatorio. Espeja addressReady pero carga
// los mensajes inline que el QA pedía visibles.
function validateCheckout() {
  const errs = {}
  if (form.value.shipping_method === 'home') {
    if (form.value.address_mode === 'saved' && addresses.value.length) {
      if (!form.value.address_id) errs.address_id = 'Elegí una dirección guardada o cargá una nueva.'
    } else {
      const a = form.value.address
      if (!a.line1?.trim()) errs['address.line1'] = 'Ingresá la calle y el número.'
      if (!a.city?.trim()) errs['address.city'] = 'Ingresá la ciudad.'
      if (!a.province?.trim()) errs['address.province'] = 'Ingresá la provincia.'
    }
  }
  if (!form.value.payment_method) errs.payment_method = 'Elegí un medio de pago para continuar.'
  fieldErrors.value = errs
  return !Object.keys(errs).length
}

// Errores del backend: extractApiError aplana {campo:[msgs]} a strings,
// pero una dirección anidada ({address:{line1:[…]}}) llegaría como
// "[object Object]" — se relee del payload crudo y se mapea a
// address.<campo> para que caiga en el input correspondiente.
function applyServerErrors(err) {
  const parsed = extractApiError(err)
  const { nonField, status: _s, ...fields } = parsed
  const out = { ...fields }
  const rawAddr = err?.response?.data?.address
  if (rawAddr && typeof rawAddr === 'object' && !Array.isArray(rawAddr)) {
    delete out.address
    for (const [ak, av] of Object.entries(rawAddr)) {
      out[`address.${ak}`] = Array.isArray(av) ? av.join(' ') : String(av)
    }
  }
  fieldErrors.value = out
  error.value = nonField || Object.values(out)[0] || 'No pudimos crear el pedido. Revisá los datos e intentá de nuevo.'
}

async function submit() {
  if (submitting.value) return
  // Validación primero: sin request si falta entrega/pago. Los errores
  // quedan inline (aria-invalid + mensaje) y el captcha ni se consulta.
  if (!validateCheckout()) {
    error.value = ''
    return
  }
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
    applyServerErrors(err)
    const fe = fieldErrors.value
    if (fe.captcha_answer || fe.challenge_id) captchaRef.value?.refresh()
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
    <div v-if="!ordersEnabled" class="ec-co-card ec-co-note">
      <span class="ec-co-note-ico" aria-hidden="true"><AppIcon name="package" :size="22" /></span>
      <div>
        <h2 class="ec-co-h2">Esta tienda todavía no vende online</h2>
        <p class="ec-co-muted">Podés ver el catálogo y hacer tu pedido por los medios de contacto de la tienda.</p>
      </div>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ver catálogo</RouterLink>
    </div>

    <!-- Sin sesión -->
    <div v-else-if="phase === 'auth'" class="ec-co-card ec-co-note">
      <span class="ec-co-note-ico" aria-hidden="true"><AppIcon name="user" :size="22" /></span>
      <div>
        <h2 class="ec-co-h2">Iniciá sesión para comprar</h2>
        <p class="ec-co-muted">Necesitás una cuenta de comprador para finalizar el pedido y seguirlo después.</p>
      </div>
      <button type="button" class="ec-btn-primary" @click="goAuth">Ingresar o crear cuenta</button>
      <RouterLink :to="cuentaTo" class="ec-co-link">Ya tengo cuenta — ir a mi cuenta</RouterLink>
    </div>

    <!-- Carrito vacío -->
    <div v-else-if="phase === 'empty'" class="ec-co-card ec-co-note">
      <span class="ec-co-note-ico" aria-hidden="true"><AppIcon name="shopping-bag" :size="26" /></span>
      <div>
        <h2 class="ec-co-h2">Tu carrito está vacío</h2>
        <p class="ec-co-muted">Agregá productos del catálogo antes de pagar.</p>
      </div>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ir al catálogo</RouterLink>
    </div>

    <div v-else-if="phase === 'loading'" class="ec-co-card ec-co-skel" aria-busy="true" aria-label="Cargando tu pedido">
      <span class="ec-sk-line ec-sk-title"></span>
      <span class="ec-sk-line"></span>
      <span class="ec-sk-line short"></span>
      <span class="ec-sk-line ec-sk-btn"></span>
    </div>

    <!-- Pedido creado: el redirect a seguimiento es inmediato, esto es el fallback visual -->
    <div v-else-if="phase === 'done'" class="ec-co-card ec-co-done" role="status">
      <span class="ec-co-done-ico" aria-hidden="true"><AppIcon name="circle-check" :size="30" /></span>
      <h2 class="ec-co-h2">¡Pedido creado!</h2>
      <p class="ec-co-muted">Te estamos llevando al seguimiento de tu pedido…</p>
    </div>

    <!-- Formulario -->
    <template v-else>
      <!-- Stepper: refleja el avance real del formulario -->
      <ol class="ec-co-steps" aria-label="Pasos de la compra">
        <li v-for="(label, i) in CO_STEPS" :key="label" class="ec-co-step"
            :class="{ 'is-done': i < stepIndex, 'is-current': i === stepIndex }"
            :aria-current="i === stepIndex ? 'step' : undefined">
          <span class="ec-co-step-dot" aria-hidden="true">
            <AppIcon v-if="i < stepIndex" name="check" :size="13" />
            <template v-else>{{ i + 1 }}</template>
          </span>
          <span class="ec-co-step-label">{{ label }}</span>
        </li>
      </ol>

      <div class="ec-co-grid">
        <form class="ec-co-main" novalidate @submit.prevent="submit">
          <section class="ec-co-card">
            <h2 class="ec-co-h2"><span class="ec-co-stepnum" aria-hidden="true">1</span> Entrega</h2>
            <p class="ec-co-buyer">
              <AppIcon name="user" :size="14" aria-hidden="true" />
              Comprás como <strong>{{ customer.displayName || 'tu cuenta' }}</strong>
            </p>
            <div class="ec-co-ship">
              <label class="ec-co-opt" :class="{ 'is-on': form.shipping_method === 'home' }">
                <input v-model="form.shipping_method" type="radio" value="home" :disabled="submitting" />
                <span class="ec-co-opt-ico" aria-hidden="true"><AppIcon name="truck" :size="18" /></span>
                <span class="ec-co-opt-txt"><strong>Envío a domicilio</strong><small>Te lo llevamos a tu dirección</small></span>
              </label>
              <label class="ec-co-opt" :class="{ 'is-on': form.shipping_method === 'pickup' }">
                <input v-model="form.shipping_method" type="radio" value="pickup" :disabled="submitting" />
                <span class="ec-co-opt-ico" aria-hidden="true"><AppIcon name="store" :size="18" /></span>
                <span class="ec-co-opt-txt"><strong>Retiro en el local</strong><small>Pasás a buscarlo cuando esté listo</small></span>
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
                <label v-for="a in addresses" :key="a.id" class="ec-co-addr" :class="{ 'is-on': form.address_id === a.id, 'is-invalid': fieldErr('address_id') }">
                  <input v-model="form.address_id" type="radio" :value="a.id" name="addr" :disabled="submitting"
                         :aria-invalid="fieldErr('address_id') ? 'true' : undefined" @change="clearFieldError('address_id')" />
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
                  <input v-model="form.address.line1" class="sp-input" :class="{ 'is-invalid': fieldErr('address.line1') }" type="text" maxlength="160" :disabled="submitting"
                         :aria-invalid="fieldErr('address.line1') ? 'true' : undefined" @input="clearFieldError('address.line1')" />
                  <span v-if="fieldErr('address.line1')" class="sp-form-error" role="alert">{{ fieldErr('address.line1') }}</span>
                </label>
                <label class="sp-field">
                  <span class="sp-field-label">Departamento / piso / referencia</span>
                  <input v-model="form.address.line2" class="sp-input" type="text" maxlength="160" :disabled="submitting" />
                </label>
                <div class="ec-co-grid2">
                  <label class="sp-field">
                    <span class="sp-field-label">Ciudad *</span>
                    <input v-model="form.address.city" class="sp-input" :class="{ 'is-invalid': fieldErr('address.city') }" type="text" maxlength="120" :disabled="submitting"
                           :aria-invalid="fieldErr('address.city') ? 'true' : undefined" @input="clearFieldError('address.city')" />
                    <span v-if="fieldErr('address.city')" class="sp-form-error" role="alert">{{ fieldErr('address.city') }}</span>
                  </label>
                  <label class="sp-field">
                    <span class="sp-field-label">Provincia *</span>
                    <input v-model="form.address.province" class="sp-input" :class="{ 'is-invalid': fieldErr('address.province') }" type="text" maxlength="120" :disabled="submitting"
                           :aria-invalid="fieldErr('address.province') ? 'true' : undefined" @input="clearFieldError('address.province')" />
                    <span v-if="fieldErr('address.province')" class="sp-form-error" role="alert">{{ fieldErr('address.province') }}</span>
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
            <p v-else class="ec-co-pickup">
              <AppIcon name="store" :size="15" aria-hidden="true" />
              Retirás el pedido en el local de {{ shopName }}. Te avisamos cuando esté listo.
            </p>
          </section>

          <section class="ec-co-card">
            <h2 class="ec-co-h2"><span class="ec-co-stepnum" aria-hidden="true">2</span> Pago</h2>
            <div class="ec-co-pay">
              <label v-for="m in paymentMethods" :key="m.value" class="ec-co-opt" :class="{ 'is-on': form.payment_method === m.value, 'is-invalid': fieldErr('payment_method') }">
                <input v-model="form.payment_method" type="radio" :value="m.value" name="pay" :disabled="submitting"
                       :aria-invalid="fieldErr('payment_method') ? 'true' : undefined" @change="clearFieldError('payment_method')" />
                <span class="ec-co-opt-ico" aria-hidden="true"><AppIcon :name="payIcon(m.value)" :size="18" /></span>
                <span class="ec-co-opt-txt"><strong>{{ m.label }}</strong><small>{{ payHint(m.value) }}</small></span>
              </label>
              <p v-if="!paymentMethods.length" class="sp-form-error" role="alert">Esta tienda no tiene medios de pago habilitados.</p>
            </div>
            <div v-if="payUi" class="ec-co-paynote" :class="`is-${form.payment_method}`">
              <AppIcon :name="payUi.icon" :size="17" aria-hidden="true" />
              <p>{{ payUi.hint }}</p>
            </div>
            <p v-if="fieldErr('payment_method')" class="sp-form-error" role="alert">{{ fieldErr('payment_method') }}</p>

            <CaptchaField ref="captchaRef" :slug="slug" :load="orderCaptchaApi.get" />
            <p v-if="fieldErr('captcha_answer') || fieldErr('challenge_id')" class="sp-form-error" role="alert">
              {{ fieldErr('captcha_answer') || fieldErr('challenge_id') }}
            </p>
            <!-- Honeypot: invisible para humanos — si viene con valor el server lo rechaza. -->
            <input v-model="form.website" type="text" name="website" class="ec-hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
          </section>

          <p v-if="error" class="sp-form-error ec-co-error" role="alert">
            <AppIcon name="circle-alert" :size="15" aria-hidden="true" /> {{ error }}
          </p>

          <button type="submit" class="ec-btn-primary ec-co-submit" :disabled="!canSubmit">
            <span v-if="submitting" class="ec-co-spin" aria-hidden="true"></span>
            {{ submitting ? 'Creando tu pedido…' : 'Confirmar pedido' }}
          </button>

          <div class="ec-co-legal">
            <AppIcon name="file-text" :size="15" aria-hidden="true" />
            <div>
              <p>La venta se realiza entre vos y el comercio: DAVENT solo provee la plataforma. El pedido se confirma cuando el vendedor acredita el pago.</p>
              <p>Al confirmar aceptás los <RouterLink :to="legalTo" target="_blank">términos y condiciones</RouterLink> de la tienda.</p>
            </div>
          </div>
        </form>

        <!-- Resumen del carrito (server-side) — sticky en desktop,
             colapsable en mobile -->
        <aside class="ec-co-side">
          <button type="button" class="ec-co-summary-toggle" :aria-expanded="summaryOpen" @click="summaryOpen = !summaryOpen">
            <span class="ec-co-summary-toggle-main">
              <strong>Tu pedido</strong>
              <small>{{ cart.itemCount }} {{ itemNoun }}</small>
            </span>
            <strong class="ec-co-summary-toggle-total">{{ money(cart.itemsTotal) }}</strong>
            <AppIcon name="chevron-down" :size="17" class="ec-co-summary-caret" :class="{ 'is-open': summaryOpen }" aria-hidden="true" />
          </button>
          <section class="ec-co-card ec-co-summary" :class="{ 'is-open': summaryOpen }" aria-label="Resumen del pedido">
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
              <div><dt>Envío</dt><dd>{{ form.shipping_method === 'pickup' ? 'Retiro sin cargo' : 'A coordinar con la tienda' }}</dd></div>
              <div class="ec-co-grand"><dt>Total estimado</dt><dd>{{ money(cart.itemsTotal) }}</dd></div>
            </dl>
            <p class="ec-co-muted">El total final lo confirma el servidor al crear el pedido.</p>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ec-checkout { display: grid; gap: 18px; }
.ec-co-head { display: grid; gap: 4px; }
.ec-co-title { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.ec-co-sub { margin: 0; font-size: 14px; color: var(--sp-muted, inherit); }
.ec-co-h2 { margin: 0 0 12px; font-size: 16px; font-weight: 800; display: flex; align-items: center; gap: 9px; }
.ec-co-stepnum { display: grid; place-items: center; width: 23px; height: 23px; flex: none; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 12%, transparent); color: var(--store-accent, inherit); font-size: 12px; font-weight: 800; }
.ec-co-card { display: grid; gap: 14px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.ec-co-muted { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }
.ec-co-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; align-items: start; }
.ec-co-main { display: grid; gap: 16px; min-width: 0; }
.ec-co-side { position: sticky; top: 90px; min-width: 0; }

/* Stepper del checkout */
.ec-co-steps { list-style: none; margin: 0; padding: 4px 6px 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.ec-co-step { display: flex; align-items: center; gap: 9px; min-width: 0; }
.ec-co-step::before { content: ''; flex: none; width: 26px; height: 2px; border-radius: 2px; background: var(--sp-line, rgba(0,0,0,.15)); transition: background .2s; }
.ec-co-step:first-child::before { display: none; }
.ec-co-step.is-done::before, .ec-co-step.is-current::before { background: var(--sp-success, #0E7A55); }
.ec-co-step-dot { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; border: 2px solid var(--sp-line, rgba(0,0,0,.2)); font-size: 12px; font-weight: 800; color: var(--sp-muted, inherit); background: var(--sp-card, transparent); flex: none; }
.ec-co-step.is-done .ec-co-step-dot { border-color: var(--sp-success, #0E7A55); background: var(--sp-success, #0E7A55); color: #fff; }
.ec-co-step.is-current .ec-co-step-dot { border-color: var(--store-accent, #111); color: var(--store-accent, #111); box-shadow: 0 0 0 4px color-mix(in srgb, var(--store-accent, #111) 14%, transparent); }
.ec-co-step-label { font-size: 13px; font-weight: 600; color: var(--sp-muted, inherit); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ec-co-step.is-done .ec-co-step-label, .ec-co-step.is-current .ec-co-step-label { color: inherit; font-weight: 700; }

/* Opciones con icono (envío y pago) */
.ec-co-ship, .ec-co-pay { display: grid; gap: 8px; }
.ec-co-opt { display: flex; align-items: flex-start; gap: 11px; padding: 12px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: calc(var(--sp-radius) * .75); cursor: pointer; transition: border-color .15s, box-shadow .15s, background .15s; }
.ec-co-opt:hover { border-color: color-mix(in srgb, var(--store-accent, #111) 45%, var(--sp-line, transparent)); }
.ec-co-opt.is-on { border-color: var(--store-accent, #111); box-shadow: 0 0 0 1px var(--store-accent, #111) inset, 0 0 0 3px color-mix(in srgb, var(--store-accent, #111) 10%, transparent); background: color-mix(in srgb, var(--store-accent, #111) 4%, transparent); }
.ec-co-opt.is-inline { padding: 9px 12px; align-items: center; }
.ec-co-opt.is-inline > span { font-size: 14px; }
.ec-co-opt input { margin-top: 3px; accent-color: var(--store-accent, #111); flex: none; }
.ec-co-opt.is-inline input { margin-top: 0; }
.ec-co-opt-ico { display: grid; place-items: center; width: 36px; height: 36px; flex: none; border-radius: calc(var(--sp-radius) * .6); background: color-mix(in srgb, var(--store-accent, #111) 9%, transparent); color: var(--store-accent, inherit); }
.ec-co-opt.is-on .ec-co-opt-ico { background: color-mix(in srgb, var(--store-accent, #111) 16%, transparent); }
.ec-co-opt-txt { display: grid; gap: 2px; font-size: 14px; min-width: 0; }
.ec-co-opt-txt small { font-size: 12px; color: var(--sp-muted, inherit); line-height: 1.4; }
.ec-co-buyer { display: flex; align-items: center; gap: 7px; margin: -4px 0 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-co-buyer strong { color: inherit; }
.ec-co-pickup { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 13.5px; color: var(--sp-muted, inherit); }
.ec-co-paynote { display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px; border-radius: calc(var(--sp-radius) * .75); font-size: 13px; line-height: 1.5; color: var(--sp-ink, inherit); background: color-mix(in srgb, var(--store-accent, #111) 7%, transparent); }
.ec-co-paynote p { margin: 0; }
.ec-co-paynote.is-whatsapp { background: color-mix(in srgb, #25d366 13%, transparent); }
.ec-co-paynote.is-mp { background: color-mix(in srgb, #00b1ea 13%, transparent); }
.ec-co-paynote.is-whatsapp svg { color: #25d366; }
.ec-co-paynote.is-mp svg { color: #00b1ea; }
.ec-co-paynote.is-transfer, .ec-co-paynote.is-cash { color: var(--sp-warning, #B45309); }
.ec-co-addr-mode { display: grid; gap: 6px; }
.ec-co-addrs { display: grid; gap: 8px; }
.ec-co-addr { display: flex; align-items: flex-start; gap: 10px; padding: 11px 13px; border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: calc(var(--sp-radius) * .75); cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.ec-co-addr:hover { border-color: color-mix(in srgb, var(--store-accent, #111) 45%, var(--sp-line, transparent)); }
.ec-co-addr.is-on { border-color: var(--store-accent, #111); box-shadow: 0 0 0 1px var(--store-accent, #111) inset; }
.ec-co-addr input { margin-top: 3px; accent-color: var(--store-accent, #111); flex: none; }
.ec-co-addr span { display: grid; gap: 2px; min-width: 0; }
.ec-co-addr small { font-size: 12px; color: var(--sp-muted, inherit); }
.ec-co-addrform { display: grid; gap: 12px; }
.ec-co-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ec-co-save { display: flex; align-items: center; gap: 9px; font-size: 13.5px; cursor: pointer; }
/* Validación inline: borde de error en opción/dirección/input inválidos */
.ec-co-opt.is-invalid, .ec-co-addr.is-invalid { border-color: var(--sp-danger, #dc2626); }
.ec-co-opt.is-invalid { box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-danger, #dc2626) 12%, transparent); }
.sp-input.is-invalid { border-color: var(--sp-danger, #dc2626); }
.sp-input.is-invalid:focus { border-color: var(--sp-danger, #dc2626); box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-danger, #dc2626) 14%, transparent); }
.ec-co-addr.is-invalid { box-shadow: 0 0 0 1px var(--sp-danger, #dc2626) inset; }
.ec-co-items { list-style: none; margin: 0 0 12px; padding: 0; display: grid; gap: 10px; max-height: 320px; overflow-y: auto; }
.ec-co-items li { display: grid; grid-template-columns: 44px 1fr auto; gap: 10px; align-items: center; }
.ec-co-thumb { width: 44px; height: 44px; object-fit: cover; border-radius: calc(var(--sp-radius) * .55); background: var(--sp-line, rgba(0,0,0,.06)); }
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
.ec-co-submit { width: 100%; padding: 14px; border: none; border-radius: calc(var(--sp-radius) * .8); background: var(--store-accent-ink, #111); color: #fff; font-size: 15.5px; font-weight: 800; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 9px; }
.ec-co-submit:disabled { opacity: .55; cursor: default; }
.ec-co-spin { width: 15px; height: 15px; border-radius: 50%; border: 2px solid color-mix(in srgb, #fff 35%, transparent); border-top-color: #fff; animation: ec-co-rotate .7s linear infinite; }
@keyframes ec-co-rotate { to { transform: rotate(360deg); } }
.ec-co-error { display: flex; align-items: flex-start; gap: 8px; padding: 12px 14px; border-radius: calc(var(--sp-radius) * .65); background: color-mix(in srgb, var(--sp-danger, #dc2626) 9%, transparent); color: var(--sp-danger, #dc2626); }
.ec-co-error svg { flex: none; margin-top: 1px; }
.ec-co-link { font-size: 13px; font-weight: 600; color: var(--store-accent, inherit); }
.ec-co-legal { display: flex; align-items: flex-start; gap: 10px; padding: 13px 15px; border: 1px dashed var(--sp-line, rgba(0,0,0,.18)); border-radius: calc(var(--sp-radius) * .75); color: var(--sp-muted, inherit); }
.ec-co-legal svg { flex: none; margin-top: 2px; opacity: .8; }
.ec-co-legal p { margin: 0; font-size: 12px; line-height: 1.55; }
.ec-co-legal p + p { margin-top: 4px; }
.ec-co-legal a { color: inherit; font-weight: 600; }

/* Estados no-form */
.ec-co-note { grid-template-columns: auto 1fr; align-items: center; }
.ec-co-note > div { display: grid; gap: 4px; }
.ec-co-note .ec-btn-primary, .ec-co-note .ec-co-link { grid-column: 1 / -1; justify-self: start; }
.ec-co-note-ico { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--store-accent, inherit); }
.ec-co-done { justify-items: center; text-align: center; padding: 44px 18px; }
.ec-co-done-ico { display: grid; place-items: center; width: 60px; height: 60px; border-radius: 50%; background: color-mix(in srgb, var(--sp-success, #0E7A55) 13%, transparent); color: var(--sp-success, #0E7A55); }
.ec-co-skel { gap: 12px; }
.ec-sk-line { display: block; height: 12px; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.ec-sk-title { width: 38%; height: 18px; }
.ec-sk-line.short { width: 55%; }
.ec-sk-btn { width: 100%; height: 46px; border-radius: calc(var(--sp-radius) * .8); margin-top: 6px; }
@media (prefers-reduced-motion: no-preference) {
  .ec-sk-line { animation: ec-co-shimmer 1.4s ease-in-out infinite; }
  .ec-sk-line:nth-child(2) { animation-delay: .1s; }
  .ec-sk-line:nth-child(3) { animation-delay: .2s; }
  @keyframes ec-co-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

/* Resumen: colapsable solo en mobile */
.ec-co-summary-toggle { display: none; }
.ec-co-summary-caret { transition: transform .2s; }
.ec-co-summary-caret.is-open { transform: rotate(180deg); }

.ec-hp { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }

.ec-co-opt input:focus-visible, .ec-co-addr input:focus-visible, .ec-co-save input:focus-visible,
.ec-co-submit:focus-visible, .ec-co-link:focus-visible, .ec-co-legal a:focus-visible,
.ec-co-summary-toggle:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}

@media (max-width: 900px) {
  .ec-co-grid { grid-template-columns: 1fr; }
  .ec-co-side { position: static; }
  .ec-co-summary-toggle {
    display: flex; align-items: center; gap: 12px; width: 100%;
    padding: 14px 16px; border: 1px solid var(--sp-line, rgba(0,0,0,.12));
    border-radius: var(--sp-radius); background: var(--sp-card, transparent); color: inherit;
    font: inherit; text-align: left; cursor: pointer;
  }
  .ec-co-summary-toggle-main { display: grid; gap: 1px; flex: 1; min-width: 0; }
  .ec-co-summary-toggle-main strong { font-size: 15px; }
  .ec-co-summary-toggle-main small { font-size: 12px; color: var(--sp-muted, inherit); }
  .ec-co-summary-toggle-total { font-size: 17px; font-weight: 800; font-variant-numeric: tabular-nums; }
  .ec-co-summary { display: none; }
  .ec-co-summary.is-open { display: grid; }
}
@media (max-width: 560px) {
  .ec-co-grid2 { grid-template-columns: 1fr; }
  .ec-co-note { grid-template-columns: 1fr; justify-items: start; }
  .ec-co-note .ec-btn-primary, .ec-co-note .ec-co-link { grid-column: auto; }
  .ec-co-step-label { font-size: 11.5px; }
}
@media (prefers-reduced-motion: reduce) {
  .ec-co-spin { animation: none; border-top-color: var(--store-accent-ink, #111); }
  .ec-co-summary-caret { transition: none; }
}
</style>
