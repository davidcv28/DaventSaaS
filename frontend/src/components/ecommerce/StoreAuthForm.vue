<script setup>
// Formulario de auth del COMPRADOR (sesión customer — nunca la DAVENT del
// dueño). Lo comparten la página /ingresar (StoreAuthView) y el modal
// global (StoreAuthModal): mismos campos, validaciones, errores por campo
// (customer.fieldErrors + customer.lastError) y Google BYO por tienda.
//
// El padre controla `mode` ('login' | 'register' | 'forgot') y decide la
// continuación cuando se emite 'done' (navegar a ?next=, correr la acción
// pendiente del carrito, etc.). 'mode' se emite cuando el usuario cambia
// de formulario desde los links del pie.
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useCustomerStore } from '../../stores/customer.store.js'
import { useCartStore } from '../../stores/cart.store.js'
import { customerPublicApi, customerApi } from '../../api/customer.api.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  slug: { type: String, required: true },
  mode: { type: String, default: 'login' },
  // Enfoca el primer campo al montar y al cambiar de modo.
  autofocus: { type: Boolean, default: true }
})
const emit = defineEmits(['done', 'mode'])

const customer = useCustomerStore()
const cart = useCartStore()

const form = ref({ email: '', password: '', first_name: '', last_name: '', forgot_email: '' })
const busy = ref(false)
const resendBusy = ref(false)     // guard del "Reenviar verificación" (anti doble-click)
const notice = ref('')               // mensaje verde (reset pedido, verificación…)
const registeredPending = ref(false) // recién se registró → aviso de verificación
const showPassword = ref(false)

const emailInput = ref(null)
const passwordInput = ref(null)
const firstNameInput = ref(null)
const lastNameInput = ref(null)
const forgotInput = ref(null)
// Aviso/error del formulario: recibe el foco cuando el envío falla y el
// problema no es de un campo concreto.
const msgRef = ref(null)

// ---------- errores del backend ----------
// fieldErrors llega como {campo: 'mensaje'} (extractApiError ya joinea
// los arrays de DRF) — tolerante a array por si cambia el formato.
const fieldError = (name) => {
  const v = customer.fieldErrors?.[name]
  return Array.isArray(v) ? (v[0] || '') : (v || '')
}
const formError = computed(() => customer.lastError || '')

// ---------- aria-invalid / aria-describedby ----------
// `bad` lo marca el submit (validación local o fieldErrors del backend) y
// `fixed` lo limpia el primer tecleo: el mensaje visible no se borra, pero
// el campo deja de anunciarse como inválido en cuanto el usuario lo corrige.
const fieldFlags = ref({
  email: { bad: false, fixed: false },
  password: { bad: false, fixed: false },
})
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const emailOk = (v) => EMAIL_RE.test(String(v || '').trim())
function markInvalid(name, bad) {
  if (fieldFlags.value[name]) fieldFlags.value[name].bad = bad
}
function resetInvalid() {
  fieldFlags.value = { email: { bad: false, fixed: false }, password: { bad: false, fixed: false } }
}
function onFieldInput(name) {
  if (fieldFlags.value[name]) fieldFlags.value[name].fixed = true
}
function isInvalid(name) {
  const f = fieldFlags.value[name]
  if (!f) return false
  return Boolean((f.bad || fieldError(name)) && !f.fixed)
}
// Id estable del mensaje de campo: login y forgot comparten el del email
// porque solo se renderiza uno por vez.
const fieldErrorId = (name) => `ec-auth-${name.replace(/_/g, '-')}-error`
// Descripción del campo = su propio error + el aviso/error del formulario.
// Los <span> de error no son live regions: se leen al enfocar, no se
// re-anuncian en cada tecla.
function describedBy(name) {
  const ids = []
  if (fieldError(name)) ids.push(fieldErrorId(name))
  if (notice.value) ids.push('ec-auth-notice')
  else if (formError.value) ids.push('ec-auth-error')
  return ids.length ? ids.join(' ') : undefined
}

function clearErrors() {
  customer.lastError = ''
  customer.fieldErrors = {}
}
function switchMode(m) {
  if (m === props.mode) return
  clearErrors()
  notice.value = ''
  registeredPending.value = false
  emit('mode', m)
}
function focusFirst() {
  if (!props.autofocus) return
  const el = props.mode === 'forgot' ? forgotInput.value : emailInput.value
  el?.focus()
}

// Primer campo inválido en orden de DOM; null si el fallo no es de un campo.
function firstInvalidEl() {
  if (props.mode === 'register') {
    if (fieldError('first_name')) return firstNameInput.value
    if (fieldError('last_name')) return lastNameInput.value
  }
  if (isInvalid('email')) return props.mode === 'forgot' ? forgotInput.value : emailInput.value
  if (props.mode !== 'forgot' && isInvalid('password')) return passwordInput.value
  return null
}
// Solo en fallo: el foco va al primer campo inválido o al bloque de error.
// En éxito no se toca el foco (el padre navega o cierra el modal).
async function focusAfterError() {
  await nextTick()
  const target = firstInvalidEl() || (formError.value ? msgRef.value : null)
  target?.focus()
}

// ---------- control segmentado (solo piel esencial) ----------
// Mismo switchMode que los links del pie: no navega ni recarga, solo emite
// 'mode' al padre. El markup nace OCULTO (ver <style scoped>) y la piel
// esencial lo enciende; el resto de los diseños no lo ve.
const SWITCH_MODES = [
  { mode: 'login', label: 'Ingresar' },
  { mode: 'register', label: 'Crear cuenta' },
  { mode: 'forgot', label: 'Recuperar' },
]
const switchIndex = computed(() => Math.max(0, SWITCH_MODES.findIndex((m) => m.mode === props.mode)))
// Cambio de modo vindo del padre (link del pie, ?mode= de la URL, authMode
// del store): limpia errores y reenfoca. `notice` NO se limpia acá — el
// aviso de "te enviamos el enlace" sobrevive al salto forgot → login.
watch(() => props.mode, () => {
  clearErrors()
  resetInvalid()
  registeredPending.value = false
  focusFirst()
})
onMounted(() => { clearErrors(); focusFirst() })

// ---------- submit ----------
async function submit() {
  if (busy.value) return
  busy.value = true
  clearErrors()
  resetInvalid()
  // Validación local mínima (el form va novalidate): sirve para marcar
  // aria-invalid y saber a qué campo llevar el foco. No bloquea el envío:
  // el backend sigue siendo la fuente de verdad.
  const emailVal = props.mode === 'forgot' ? form.value.forgot_email : form.value.email
  markInvalid('email', !emailOk(emailVal))
  if (props.mode !== 'forgot') markInvalid('password', form.value.password.length < 8)
  try {
    if (props.mode === 'login') {
      const res = await customer.login({ email: form.value.email.trim(), password: form.value.password, store_slug: props.slug })
      if (res?.ok !== false) done()
    } else if (props.mode === 'register') {
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
        // La sesión queda activa tras el registro (el backend la emite):
        // el toast del layout conserva el aviso cuando el padre cierra
        // el modal o navega a ?next=.
        cart.flash('ok', notice.value, 6000)
        done()
      }
    } else {
      try {
        await customerApi.requestPasswordReset(form.value.forgot_email.trim(), props.slug)
        notice.value = 'Si el correo está registrado, te va a llegar un enlace para restablecer tu contraseña.'
        // Salto a login SIN switchMode: el aviso de éxito no se limpia y
        // el correo ya cargado pasa al campo de login (no se retipa).
        form.value.email = form.value.forgot_email.trim()
        emit('mode', 'login')
      } catch {
        notice.value = 'No pudimos enviar el enlace. Revisá el correo y probá de nuevo.'
      }
    }
  } finally {
    busy.value = false
  }
  // fieldErrors del backend también cuentan como campo inválido.
  const failed = formError.value || fieldError('email') || fieldError('password')
    || fieldError('first_name') || fieldError('last_name')
  if (failed) focusAfterError()
}
function done() { emit('done') }

async function resendVerification() {
  if (resendBusy.value) return
  resendBusy.value = true
  try {
    await customerApi.resendVerification()
    notice.value = 'Te reenviamos el correo de verificación.'
  } catch {
    notice.value = customer.lastError || 'No pudimos reenviar el correo.'
  } finally {
    resendBusy.value = false
  }
}

// ---------- Google (GIS por tienda) ----------
// El client_id sale de /api/customer-auth/google-config/<slug>/ (BYO del
// dueño o el central DAVENT — nunca se hornea en el bundle). Si
// enabled=false no se renderiza el botón.
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
    text: props.mode === 'register' ? 'signup_with' : 'continue_with',
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
watch(() => props.mode, () => { nextTick(renderGoogleButton) })
onMounted(() => { if (props.slug) initGoogle() })
onUnmounted(() => resizeObs?.disconnect())
</script>

<template>
  <!-- data-mode: hook neutro para que las pieles hagan selectores por modo
       (p.ej. .ecaf[data-mode='register'] …) sin JS ni cambiar el markup. -->
  <div class="ecaf" :data-mode="mode">
    <!-- Control segmentado del modo (indicador deslizante). Solo piel
         esencial: en el resto de los diseños queda display:none. -->
    <div
      class="ecaf-switch" role="group" aria-label="Tipo de acceso"
      :style="{ '--ecaf-switch-i': switchIndex }"
    >
      <span class="ecaf-switch-pill" aria-hidden="true"></span>
      <button
        v-for="m in SWITCH_MODES" :key="m.mode" type="button"
        class="ecaf-switch-btn" :class="{ 'is-on': mode === m.mode }"
        :aria-pressed="mode === m.mode"
        @click="switchMode(m.mode)"
      >{{ m.label }}</button>
    </div>

    <p v-if="notice" id="ec-auth-notice" ref="msgRef" class="ecaf-notice" role="status" tabindex="-1">{{ notice }}</p>
    <p v-else-if="formError" id="ec-auth-error" ref="msgRef" class="ecaf-error" role="alert" tabindex="-1">{{ formError }}</p>

    <form class="ecaf-form" novalidate :aria-busy="busy ? 'true' : undefined" @submit.prevent="submit">
      <template v-if="mode === 'register'">
        <div class="ecaf-grid">
          <label class="sp-field">
            <span id="ec-auth-first-name-label" class="sp-field-label">Nombre</span>
            <input
              ref="firstNameInput" v-model="form.first_name" name="first_name" class="sp-input"
              type="text" autocomplete="given-name" enterkeyhint="next" :disabled="busy"
              aria-labelledby="ec-auth-first-name-label"
              :aria-invalid="fieldError('first_name') ? 'true' : undefined"
              :aria-describedby="describedBy('first_name')"
            />
            <span v-if="fieldError('first_name')" :id="fieldErrorId('first_name')" class="sp-form-error">{{ fieldError('first_name') }}</span>
          </label>
          <label class="sp-field">
            <span id="ec-auth-last-name-label" class="sp-field-label">Apellido</span>
            <input
              ref="lastNameInput" v-model="form.last_name" name="last_name" class="sp-input"
              type="text" autocomplete="family-name" enterkeyhint="next" :disabled="busy"
              aria-labelledby="ec-auth-last-name-label"
              :aria-invalid="fieldError('last_name') ? 'true' : undefined"
              :aria-describedby="describedBy('last_name')"
            />
            <span v-if="fieldError('last_name')" :id="fieldErrorId('last_name')" class="sp-form-error">{{ fieldError('last_name') }}</span>
          </label>
        </div>
      </template>

      <template v-if="mode === 'forgot'">
        <label class="sp-field">
          <span id="ec-auth-forgot-email-label" class="sp-field-label">Email</span>
          <input
            ref="forgotInput" v-model="form.forgot_email" name="email" class="sp-input"
            type="email" autocomplete="email" inputmode="email" required :disabled="busy"
            placeholder="Correo electrónico"
            autocapitalize="none" autocorrect="off" spellcheck="false" enterkeyhint="go"
            aria-labelledby="ec-auth-forgot-email-label"
            :aria-invalid="isInvalid('email') ? 'true' : undefined"
            :aria-describedby="describedBy('email')"
            @input="onFieldInput('email')"
          />
          <span v-if="fieldError('email')" :id="fieldErrorId('email')" class="sp-form-error">{{ fieldError('email') }}</span>
        </label>
      </template>

      <template v-else>
        <label class="sp-field">
          <span id="ec-auth-email-label" class="sp-field-label">Email</span>
          <input
            ref="emailInput" id="ec-auth-email" v-model="form.email" name="email" class="sp-input"
            type="email" autocomplete="email" inputmode="email" required :disabled="busy"
            placeholder="Correo electrónico"
            autocapitalize="none" autocorrect="off" spellcheck="false" enterkeyhint="next"
            aria-labelledby="ec-auth-email-label"
            :aria-invalid="isInvalid('email') ? 'true' : undefined"
            :aria-describedby="describedBy('email')"
            @input="onFieldInput('email')"
          />
          <span v-if="fieldError('email')" :id="fieldErrorId('email')" class="sp-form-error">{{ fieldError('email') }}</span>
        </label>
        <label class="sp-field">
          <span id="ec-auth-password-label" class="sp-field-label">Contraseña</span>
          <span class="ecaf-pass">
            <input
              ref="passwordInput" id="ec-auth-password" v-model="form.password" name="password" class="sp-input"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Contraseña"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              required minlength="8" :disabled="busy"
              spellcheck="false" autocapitalize="none"
              :enterkeyhint="mode === 'login' ? 'go' : 'done'"
              aria-labelledby="ec-auth-password-label"
              :aria-invalid="isInvalid('password') ? 'true' : undefined"
              :aria-describedby="describedBy('password')"
              @input="onFieldInput('password')"
            />
            <button
              type="button" class="ecaf-pass-toggle" :disabled="busy"
              :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              <AppIcon :name="showPassword ? 'eye-off' : 'eye'" :size="17" />
            </button>
          </span>
          <span v-if="fieldError('password')" :id="fieldErrorId('password')" class="sp-form-error">{{ fieldError('password') }}</span>
        </label>
      </template>

      <button type="submit" class="ecaf-submit" :disabled="busy || googleBusy">
        <AppIcon v-if="busy" name="loader" :size="16" class="ecaf-spin" aria-hidden="true" />
        {{ busy ? 'Un momento…' : mode === 'login' ? 'Ingresar' : mode === 'register' ? 'Crear cuenta' : 'Enviar enlace' }}
      </button>
    </form>

    <div v-if="googleEnabled && mode !== 'forgot'" class="ecaf-google">
      <div class="ecaf-divider"><span>o continuá con</span></div>
      <div ref="googleEl" class="ecaf-google-btn" :class="{ 'is-busy': googleBusy }"></div>
    </div>

    <footer class="ecaf-foot">
      <template v-if="mode === 'login'">
        <button type="button" class="ecaf-link" @click="switchMode('forgot')">¿Olvidaste tu contraseña?</button>
        <button type="button" class="ecaf-link" @click="switchMode('register')">¿No tenés cuenta? Registrate</button>
      </template>
      <template v-else-if="mode === 'register'">
        <button type="button" class="ecaf-link" @click="switchMode('login')">¿Ya tenés cuenta? Ingresá</button>
        <button v-if="registeredPending" type="button" class="ecaf-link ecaf-link-resend" :disabled="resendBusy" @click="resendVerification">Reenviar correo de verificación</button>
      </template>
      <template v-else>
        <button type="button" class="ecaf-link" @click="switchMode('login')">Volver a ingresar</button>
      </template>
    </footer>
  </div>
</template>

<style scoped>
/* Control segmentado del modo (ingresar/registro/recuperar): visible en la
   base minimalista — es el selector de modo accesible (grupo con
   aria-pressed por botón, un solo CTA primario abajo). Las pieles que ya
   lo estilizan (esencial, aurum, calzado, impacto, moderntec) lo
   redefinen con más especificidad; el resto hereda esta versión neutra. */
.ecaf-switch {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  position: relative; isolation: isolate;
  padding: 4px;
  border: 1px solid var(--sp-line, rgba(127, 127, 127, .28));
  border-radius: 999px;
  background: var(--sp-soft, rgba(127, 127, 127, .12));
}
.ecaf-switch-pill {
  position: absolute; z-index: 0;
  top: 4px; bottom: 4px; left: 4px;
  width: calc((100% - 8px) / 3);
  border-radius: 999px;
  background: var(--store-accent-ink, #111);
  transform: translate3d(calc(var(--ecaf-switch-i, 0) * 100%), 0, 0);
  transition: transform .3s ease;
  pointer-events: none;
}
.ecaf-switch-btn {
  position: relative; z-index: 1;
  min-height: 42px; padding: 8px 4px;
  border: 0; border-radius: 999px; background: none;
  font: inherit; font-size: 13px; font-weight: 600; letter-spacing: .01em;
  color: var(--sp-ink-2, var(--sp-muted, #5b6678));
  cursor: pointer;
  transition: color .2s ease;
}
.ecaf-switch-btn.is-on { color: var(--sp-on-band, #fff); }
.ecaf-switch-btn:hover:not(.is-on) { color: var(--sp-ink, #0f172a); }
.ecaf-switch-btn:focus-visible {
  outline: 2px solid var(--sp-accent-text, var(--store-accent-ink, #111));
  outline-offset: 2px;
}
.ecaf { display: grid; gap: 14px; }
.ecaf-notice {
  margin: 0; padding: 11px 14px; border-radius: 12px; font-size: 13.5px; line-height: 1.45;
  background: color-mix(in srgb, var(--sp-success, #0E7A55) 13%, transparent);
  border: 1px solid color-mix(in srgb, var(--sp-success, #0E7A55) 32%, transparent);
  color: var(--sp-ink-2, inherit);
}
.ecaf-error {
  margin: 0; padding: 11px 14px; border-radius: 12px; font-size: 13.5px; line-height: 1.45;
  background: color-mix(in srgb, var(--sp-danger, #B42318) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--sp-danger, #B42318) 30%, transparent);
  color: var(--sp-ink-2, inherit);
}
.ecaf-form { display: grid; gap: 13px; }
.ecaf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ecaf-pass { position: relative; display: block; }
.ecaf-pass .sp-input { padding-right: 46px; }
.ecaf-pass-toggle {
  position: absolute; right: 5px; top: 50%; transform: translateY(-50%);
  display: grid; place-items: center; width: 36px; height: 36px;
  border: none; border-radius: 9px; background: transparent;
  color: var(--sp-muted, #5b6678); cursor: pointer;
}
.ecaf-pass-toggle:hover { color: var(--sp-accent-text, var(--store-accent-ink, #111)); background: var(--sp-soft, rgba(127, 127, 127, .12)); }
.ecaf-pass-toggle:focus-visible {
  outline: 2px solid var(--sp-accent-text, var(--store-accent-ink, #111));
  outline-offset: 2px;
}
.ecaf-submit {
  display: inline-flex; align-items: center; justify-content: center; gap: 9px;
  margin-top: 4px; padding: 13px 18px; border: none; border-radius: 12px;
  background: var(--store-accent-ink, #111); color: var(--sp-on-band, #fff);
  font-size: 14.5px; font-weight: 700; cursor: pointer;
  transition: filter .15s, transform .12s;
}
.ecaf-submit:hover:not(:disabled) { filter: brightness(1.1); }
.ecaf-submit:active:not(:disabled) { transform: translateY(1px); }
.ecaf-submit:disabled { opacity: .55; cursor: default; }
.ecaf-submit:focus-visible,
.ecaf-link:focus-visible {
  outline: 2px solid var(--sp-accent-text, var(--store-accent-ink, #111));
  outline-offset: 2px;
}
.ecaf-spin { animation: ecaf-rotate 1s linear infinite; }
@keyframes ecaf-rotate { to { transform: rotate(360deg); } }
.ecaf-google { margin-top: 4px; }
.ecaf-divider {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
  font-size: 12px; color: var(--sp-muted, #5b6678);
}
.ecaf-divider::before, .ecaf-divider::after { content: ''; flex: 1; height: 1px; background: var(--sp-line, currentColor); opacity: .45; }
.ecaf-google-btn { display: grid; place-items: center; min-height: 46px; }
.ecaf-google-btn.is-busy { opacity: .6; }
.ecaf-foot { display: flex; flex-wrap: wrap; gap: 6px 16px; }
.ecaf-link {
  border: none; background: none; padding: 4px 0;
  font-size: 13px; font-weight: 600; cursor: pointer;
  color: var(--sp-accent-text, var(--store-accent-ink, #111));
  text-decoration: underline; text-underline-offset: 2px;
}
.ecaf-link:hover { text-decoration-thickness: 2px; }
.ecaf-link:disabled { opacity: .55; cursor: default; }
@media (prefers-reduced-motion: reduce) {
  .ecaf-spin,
  .ecaf-switch-pill { animation: none; transition: none; }
}
@media (max-width: 480px) { .ecaf-grid { grid-template-columns: 1fr; } }
</style>
