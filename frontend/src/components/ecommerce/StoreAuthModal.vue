<script setup>
// Modal de auth del COMPRADOR de tienda (sesión customer — distinta de la
// sesión DAVENT del dueño). La monta StorePublicLayout una sola vez y el
// cart.store la abre desde cualquier "Agregar al carrito" / "Ir a pagar" /
// "Suscribirme". Modos: login | register | forgot (recuperar contraseña).
//
// Google: el client_id sale de /api/customer-auth/google-config/<slug>/
// (BYO del dueño o el central DAVENT — nunca se hornea en el bundle). Si
// enabled=false no se renderiza el botón.
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useCustomerStore } from '../../stores/customer.store.js'
import { useCartStore } from '../../stores/cart.store.js'
import { customerPublicApi, customerApi } from '../../api/customer.api.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  slug: { type: String, required: true },
  // Título contextual: 'checkout' | 'cart' | 'subscribe' | '' (genérico).
  purpose: { type: String, default: '' }
})
const emit = defineEmits(['done', 'close'])

const customer = useCustomerStore()
const cart = useCartStore()

const mode = ref('login')
const busy = ref(false)
const notice = ref('')          // mensaje verde (verificación reenviada, reset pedido…)
const registeredPending = ref(false)  // recién se registró → aviso de verificación

const form = ref({ email: '', password: '', first_name: '', last_name: '', forgot_email: '' })

const titles = { login: 'Ingresá a tu cuenta', register: 'Creá tu cuenta', forgot: 'Recuperá tu contraseña' }
const title = computed(() => titles[mode.value] || 'Tu cuenta')
const subtitle = computed(() => {
  if (props.purpose === 'checkout') return 'Para finalizar tu compra necesitás ingresar o crear tu cuenta.'
  if (props.purpose === 'subscribe') return 'Para suscribirte necesitás ingresar o crear tu cuenta.'
  return 'Seguimiento de pedidos, suscripciones y soporte en un solo lugar.'
})

// ---------- errores del backend ----------
// fieldErrors llega como {campo: 'mensaje'} (extractApiError ya joinea
// los arrays de DRF) — tolerante a array por si cambia el formato.
const fieldError = (name) => {
  const v = customer.fieldErrors?.[name]
  return Array.isArray(v) ? (v[0] || '') : (v || '')
}
const formError = computed(() => customer.lastError || '')

watch(() => cart.authMode, (m) => { if (m) mode.value = m })
watch(() => cart.authOpen, async (open) => {
  if (!open) return
  mode.value = cart.authMode || 'login'
  customer.lastError = ''
  customer.fieldErrors = {}
  notice.value = ''
  registeredPending.value = false
  await nextTick()
  document.getElementById('ec-auth-email')?.focus()
})

function switchMode(m) {
  mode.value = m
  customer.lastError = ''
  customer.fieldErrors = {}
  notice.value = ''
}
function close() { emit('close'); cart.closeAuth() }
function onBackdrop(e) { if (e.target === e.currentTarget) close() }
function onKey(e) { if (e.key === 'Escape') close() }

// ---------- submit ----------
async function submit() {
  if (busy.value) return
  busy.value = true
  customer.lastError = ''
  customer.fieldErrors = {}
  try {
    if (mode.value === 'login') {
      const res = await customer.login({ email: form.value.email.trim(), password: form.value.password, store_slug: props.slug })
      if (res?.ok !== false) done()
    } else if (mode.value === 'register') {
      const res = await customer.register({
        email: form.value.email.trim(),
        password: form.value.password,
        first_name: form.value.first_name.trim(),
        last_name: form.value.last_name.trim(),
        store_slug: props.slug,
      })
      if (res?.ok !== false) {
        registeredPending.value = true
        notice.value = 'Te enviamos un correo para verificar tu cuenta. Mientras tanto ya podés seguir comprando.'
        // La sesión queda activa tras el registro (el backend la emite).
        done()
      }
    } else {
      await customerApi.requestPasswordReset(form.value.forgot_email.trim())
      notice.value = 'Si el correo está registrado, te va a llegar un enlace para restablecer tu contraseña.'
      mode.value = 'login'
    }
  } finally {
    busy.value = false
  }
}
function done() { emit('done'); }

async function resendVerification() {
  try { await customerApi.resendVerification() ; notice.value = 'Te reenviamos el correo de verificación.' }
  catch { notice.value = customer.lastError || 'No pudimos reenviar el correo.' }
}

// ---------- Google (GIS por tienda) ----------
const googleEnabled = ref(false)
const googleClientId = ref('')
const googleEl = ref(null)
const googleBusy = ref(false)
let resizeObs = null

function loadScript(src, id) {
  if (document.getElementById(id)) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src; s.id = id; s.async = true; s.defer = true
    s.onload = () => resolve(); s.onerror = () => reject(new Error('gsi'))
    document.head.appendChild(s)
  })
}
function renderGoogleButton() {
  const el = googleEl.value
  if (!el || !window.google?.accounts?.id) return
  el.innerHTML = ''
  window.google.accounts.id.renderButton(el, {
    type: 'standard', theme: 'outline', size: 'large', shape: 'pill',
    logo_alignment: 'left',
    text: mode.value === 'register' ? 'signup_with' : 'continue_with',
    width: Math.min(Math.max(el.clientWidth || 300, 200), 340),
  })
}
async function onGoogleCredential({ credential }) {
  if (!credential) { notice.value = 'No recibimos la credencial de Google.'; return }
  googleBusy.value = true
  try {
    const res = await customer.googleLogin({ credential, store_slug: props.slug })
    if (res?.ok !== false) done()
    else notice.value = customer.lastError || 'No pudimos iniciar sesión con Google.'
  } finally {
    googleBusy.value = false
  }
}
async function initGoogle() {
  try {
    const cfg = await customerPublicApi.googleConfig(props.slug)
    if (!cfg?.enabled || !cfg?.client_id) return
    googleEnabled.value = true
    googleClientId.value = cfg.client_id
    await loadScript('https://accounts.google.com/gsi/client', 'gsi-client')
    window.google.accounts.id.initialize({ client_id: googleClientId.value, callback: onGoogleCredential })
    await nextTick()
    renderGoogleButton()
    let timer = null; let lastW = googleEl.value?.clientWidth || 0
    resizeObs = new ResizeObserver(() => {
      const w = googleEl.value?.clientWidth || 0
      if (!w || w === lastW) return
      lastW = w; clearTimeout(timer); timer = setTimeout(renderGoogleButton, 150)
    })
    resizeObs.observe(googleEl.value)
  } catch { /* sin Google en esta tienda — el botón simplemente no aparece */ }
}
watch(() => mode.value, () => { nextTick(renderGoogleButton) })
onMounted(() => { if (props.slug) initGoogle() })
onUnmounted(() => resizeObs?.disconnect())
</script>

<template>
  <Teleport to="body">
    <div v-if="cart.authOpen" class="ec-auth-backdrop" @click="onBackdrop" @keydown="onKey">
      <div class="ec-auth-card" role="dialog" aria-modal="true" :aria-label="title">
        <button type="button" class="ec-auth-close" aria-label="Cerrar" @click="close">
          <AppIcon name="x" :size="18" />
        </button>

        <header class="ec-auth-head">
          <h2 class="ec-auth-title">{{ title }}</h2>
          <p class="ec-auth-sub">{{ subtitle }}</p>
        </header>

        <p v-if="notice" class="ec-auth-notice" role="status">{{ notice }}</p>
        <p v-else-if="formError" class="ec-auth-error" role="alert">{{ formError }}</p>

        <form class="ec-auth-form" novalidate @submit.prevent="submit">
          <template v-if="mode === 'register'">
            <div class="ec-auth-grid">
              <label class="sp-field">
                <span class="sp-field-label">Nombre</span>
                <input v-model="form.first_name" class="sp-input" type="text" autocomplete="given-name" :disabled="busy" />
              </label>
              <label class="sp-field">
                <span class="sp-field-label">Apellido</span>
                <input v-model="form.last_name" class="sp-input" type="text" autocomplete="family-name" :disabled="busy" />
              </label>
            </div>
          </template>

          <template v-if="mode === 'forgot'">
            <label class="sp-field">
              <span class="sp-field-label">Email</span>
              <input id="ec-auth-email" v-model="form.forgot_email" class="sp-input" type="email" autocomplete="email" required :disabled="busy" />
              <span v-if="fieldError('email')" class="sp-form-error">{{ fieldError('email') }}</span>
            </label>
          </template>

          <template v-else>
            <label class="sp-field">
              <span class="sp-field-label">Email</span>
              <input id="ec-auth-email" v-model="form.email" class="sp-input" type="email" autocomplete="email" required :disabled="busy" />
              <span v-if="fieldError('email')" class="sp-form-error">{{ fieldError('email') }}</span>
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Contraseña</span>
              <input v-model="form.password" class="sp-input" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required minlength="8" :disabled="busy" />
              <span v-if="fieldError('password')" class="sp-form-error">{{ fieldError('password') }}</span>
            </label>
          </template>

          <button type="submit" class="ec-auth-submit" :disabled="busy || googleBusy">
            {{ busy ? 'Un momento…' : mode === 'login' ? 'Ingresar' : mode === 'register' ? 'Crear cuenta' : 'Enviar enlace' }}
          </button>
        </form>

        <div v-if="googleEnabled && mode !== 'forgot'" class="ec-auth-google">
          <div class="ec-auth-divider"><span>o continuá con</span></div>
          <div ref="googleEl" class="ec-auth-google-btn" :class="{ 'is-busy': googleBusy }"></div>
        </div>

        <footer class="ec-auth-foot">
          <template v-if="mode === 'login'">
            <button type="button" class="ec-auth-link" @click="switchMode('forgot')">¿Olvidaste tu contraseña?</button>
            <button type="button" class="ec-auth-link" @click="switchMode('register')">¿No tenés cuenta? Registrate</button>
          </template>
          <template v-else-if="mode === 'register'">
            <button type="button" class="ec-auth-link" @click="switchMode('login')">¿Ya tenés cuenta? Ingresá</button>
            <button v-if="registeredPending" type="button" class="ec-auth-link" @click="resendVerification">Reenviar correo de verificación</button>
          </template>
          <template v-else>
            <button type="button" class="ec-auth-link" @click="switchMode('login')">Volver a ingresar</button>
          </template>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ec-auth-backdrop {
  position: fixed; inset: 0; z-index: 1200;
  display: grid; place-items: center; padding: 20px;
  background: color-mix(in srgb, #000 55%, transparent);
  backdrop-filter: blur(3px);
}
.ec-auth-card {
  position: relative; width: min(420px, 100%); max-height: min(90vh, 720px);
  overflow-y: auto; padding: 26px 24px 22px;
  border-radius: 18px; border: 1px solid var(--sp-line, rgba(255,255,255,.12));
  background: var(--sp-card, var(--ds-bg, #fff)); color: var(--sp-ink, inherit);
  box-shadow: 0 24px 60px rgba(0,0,0,.28);
}
.ec-auth-close {
  position: absolute; top: 12px; right: 12px; z-index: 2;
  display: grid; place-items: center; width: 34px; height: 34px;
  border: none; border-radius: 10px; background: transparent; color: inherit; cursor: pointer;
}
.ec-auth-head { margin-bottom: 14px; padding-right: 30px; }
.ec-auth-title { margin: 0 0 4px; font-size: 21px; font-weight: 800; letter-spacing: -.01em; }
.ec-auth-sub { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }
.ec-auth-notice { margin: 0 0 12px; padding: 10px 12px; border-radius: 10px; font-size: 13px; background: color-mix(in srgb, #16a34a 14%, transparent); }
.ec-auth-error { margin: 0 0 12px; padding: 10px 12px; border-radius: 10px; font-size: 13px; background: color-mix(in srgb, #dc2626 14%, transparent); }
.ec-auth-form { display: grid; gap: 12px; }
.ec-auth-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ec-auth-submit {
  margin-top: 4px; padding: 12px 16px; border: none; border-radius: 12px;
  background: var(--store-accent, #111); color: var(--store-accent-ink, #fff);
  font-size: 14.5px; font-weight: 700; cursor: pointer;
}
.ec-auth-submit:disabled { opacity: .55; cursor: default; }
.ec-auth-google { margin-top: 14px; }
.ec-auth-divider { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 12px; color: var(--sp-muted, inherit); }
.ec-auth-divider::before, .ec-auth-divider::after { content: ''; flex: 1; height: 1px; background: var(--sp-line, currentColor); opacity: .4; }
.ec-auth-google-btn { display: grid; place-items: center; min-height: 44px; }
.ec-auth-foot { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 16px; }
.ec-auth-link { border: none; background: none; padding: 4px 0; font-size: 13px; font-weight: 600; color: var(--store-accent, inherit); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
@media (max-width: 480px) { .ec-auth-grid { grid-template-columns: 1fr; } }
</style>
