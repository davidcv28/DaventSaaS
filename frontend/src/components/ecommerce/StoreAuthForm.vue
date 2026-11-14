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
import { storeHostSlug } from '../../config/env.js'
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

const form = ref({ email: '', password: '', password2: '', first_name: '', last_name: '', forgot_email: '' })
const busy = ref(false)
const resendBusy = ref(false)     // guard del "Reenviar verificación" (anti doble-click)
const notice = ref('')               // mensaje verde (reset pedido, verificación…)
const registeredPending = ref(false) // recién se registró → aviso de verificación
const showPassword = ref(false)
const showPassword2 = ref(false)
// Mismatch local de confirmación: el backend no recibe password2 — la
// coincidencia se valida en cliente antes de llamar a la API.
const mismatch = ref('')

const emailInput = ref(null)
const passwordInput = ref(null)
const firstNameInput = ref(null)
const lastNameInput = ref(null)
const forgotInput = ref(null)
const confirmInput = ref(null)
// Consentimiento legal del comprador: el registro exige aceptar los
// términos/privacidad DE LA TIENDA (no son opcionales para el comercio).
const acceptTerms = ref(false)
const termsError = ref('')
const termsInput = ref(null)
const legalTo = (kind) => storeHostSlug ? `/legal/${kind}` : `/${props.slug}/legal/${kind}`
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
  confirm: { bad: false, fixed: false },
})
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const emailOk = (v) => EMAIL_RE.test(String(v || '').trim())
function markInvalid(name, bad) {
  if (fieldFlags.value[name]) fieldFlags.value[name].bad = bad
}
function resetInvalid() {
  fieldFlags.value = { email: { bad: false, fixed: false }, password: { bad: false, fixed: false }, confirm: { bad: false, fixed: false } }
  mismatch.value = ''
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
  termsError.value = ''
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
  // Confirmación solo en registro: es chequeo local — no viaja al backend.
  if (props.mode === 'register') {
    const bad = !form.value.password2 || form.value.password2 !== form.value.password
    markInvalid('confirm', bad)
    if (bad) {
      mismatch.value = 'Las contraseñas no coinciden.'
      busy.value = false
      await nextTick()
      confirmInput.value?.focus()
      return
    }
    if (!acceptTerms.value) {
      termsError.value = 'Tenés que aceptar los términos y la política de privacidad para crear tu cuenta.'
      busy.value = false
      await nextTick()
      termsInput.value?.focus()
      return
    }
  }
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

    <p v-if="notice" id="ec-auth-notice" ref="msgRef" class="ecaf-notice" role="status" tabindex="-1">
      <AppIcon name="circle-check" :size="15" class="ecaf-msg-ico" aria-hidden="true" /><span>{{ notice }}</span>
    </p>
    <p v-else-if="formError" id="ec-auth-error" ref="msgRef" class="ecaf-error" role="alert" tabindex="-1">
      <AppIcon name="circle-alert" :size="15" class="ecaf-msg-ico" aria-hidden="true" /><span>{{ formError }}</span>
    </p>

    <form class="ecaf-form" novalidate :aria-busy="busy ? 'true' : undefined" @submit.prevent="submit">
      <template v-if="mode === 'register'">
        <div class="ecaf-grid">
          <label class="sp-field">
            <span class="ecaf-ico" aria-hidden="true"><AppIcon name="user" :size="16" /></span>
            <span id="ec-auth-first-name-label" class="sp-field-label">Nombre</span>
            <input
              ref="firstNameInput" v-model="form.first_name" name="first_name" class="sp-input"
              type="text" autocomplete="given-name" placeholder="María" enterkeyhint="next" :disabled="busy"
              aria-labelledby="ec-auth-first-name-label"
              :aria-invalid="fieldError('first_name') ? 'true' : undefined"
              :aria-describedby="describedBy('first_name')"
            />
            <span v-if="fieldError('first_name')" :id="fieldErrorId('first_name')" class="sp-form-error">{{ fieldError('first_name') }}</span>
          </label>
          <label class="sp-field">
            <span class="ecaf-ico" aria-hidden="true"><AppIcon name="user" :size="16" /></span>
            <span id="ec-auth-last-name-label" class="sp-field-label">Apellido</span>
            <input
              ref="lastNameInput" v-model="form.last_name" name="last_name" class="sp-input"
              type="text" autocomplete="family-name" placeholder="Pérez" enterkeyhint="next" :disabled="busy"
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
          <span class="ecaf-ico" aria-hidden="true"><AppIcon name="mail" :size="16" /></span>
          <span id="ec-auth-forgot-email-label" class="sp-field-label">Email</span>
          <input
            ref="forgotInput" v-model="form.forgot_email" name="email" class="sp-input"
            type="email" autocomplete="email" inputmode="email" required :disabled="busy"
            placeholder="nombre@correo.com"
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
          <span class="ecaf-ico" aria-hidden="true"><AppIcon name="mail" :size="16" /></span>
          <span id="ec-auth-email-label" class="sp-field-label">Email</span>
          <input
            ref="emailInput" id="ec-auth-email" v-model="form.email" name="email" class="sp-input"
            type="email" autocomplete="email" inputmode="email" required :disabled="busy"
            placeholder="nombre@correo.com"
            autocapitalize="none" autocorrect="off" spellcheck="false" enterkeyhint="next"
            aria-labelledby="ec-auth-email-label"
            :aria-invalid="isInvalid('email') ? 'true' : undefined"
            :aria-describedby="describedBy('email')"
            @input="onFieldInput('email')"
          />
          <span v-if="fieldError('email')" :id="fieldErrorId('email')" class="sp-form-error">{{ fieldError('email') }}</span>
        </label>
        <label class="sp-field">
          <span class="ecaf-labelrow">
            <span id="ec-auth-password-label" class="sp-field-label">Contraseña</span>
            <button
              v-if="mode === 'login'" type="button" class="ecaf-minilink" :disabled="busy"
              @click="switchMode('forgot')"
            >¿Olvidaste tu contraseña?</button>
          </span>
          <span class="ecaf-pass">
            <span class="ecaf-ico" aria-hidden="true"><AppIcon name="lock" :size="16" /></span>
            <input
              ref="passwordInput" id="ec-auth-password" v-model="form.password" name="password" class="sp-input"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Mínimo 8 caracteres"
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
        <label v-if="mode === 'register'" class="sp-field">
          <span id="ec-auth-confirm-label" class="sp-field-label">Repetir contraseña</span>
          <span class="ecaf-pass">
            <span class="ecaf-ico" aria-hidden="true"><AppIcon name="lock" :size="16" /></span>
            <input
              ref="confirmInput" id="ec-auth-confirm" v-model="form.password2" name="password2" class="sp-input"
              :type="showPassword2 ? 'text' : 'password'"
              placeholder="Repetí tu contraseña"
              autocomplete="new-password"
              required minlength="8" :disabled="busy"
              spellcheck="false" autocapitalize="none"
              enterkeyhint="done"
              aria-labelledby="ec-auth-confirm-label"
              :aria-invalid="isInvalid('confirm') || mismatch ? 'true' : undefined"
              :aria-describedby="describedBy('confirm')"
              @input="onFieldInput('confirm'); mismatch = ''"
            />
            <button
              type="button" class="ecaf-pass-toggle" :disabled="busy"
              :aria-label="showPassword2 ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              :aria-pressed="showPassword2"
              @click="showPassword2 = !showPassword2"
            >
              <AppIcon :name="showPassword2 ? 'eye-off' : 'eye'" :size="17" />
            </button>
          </span>
          <span v-if="mismatch" id="ec-auth-confirm-error" class="sp-form-error">{{ mismatch }}</span>
        </label>
        <template v-if="mode === 'register'">
          <label class="ecaf-terms">
            <input
              ref="termsInput" v-model="acceptTerms" type="checkbox" :disabled="busy"
              :aria-invalid="termsError ? 'true' : undefined"
              :aria-describedby="termsError ? 'ec-auth-terms-error' : undefined"
              @change="termsError = ''"
            />
            <span class="ecaf-terms-text">
              Acepto los
              <RouterLink :to="legalTo('terms')" target="_blank" rel="noopener" @click.stop>Términos y condiciones</RouterLink>
              y la
              <RouterLink :to="legalTo('privacy')" target="_blank" rel="noopener" @click.stop>Política de privacidad</RouterLink>
              de la tienda.
            </span>
          </label>
          <span v-if="termsError" id="ec-auth-terms-error" class="sp-form-error" role="alert">{{ termsError }}</span>
        </template>
      </template>

      <button type="submit" class="ecaf-submit" :disabled="busy || googleBusy">
        <AppIcon v-if="busy" name="loader" :size="16" class="ecaf-spin" aria-hidden="true" />
        {{ busy ? 'Un momento…' : mode === 'login' ? 'Ingresar' : mode === 'register' ? 'Crear cuenta' : 'Enviar enlace' }}
      </button>
    </form>

    <div v-if="googleEnabled && mode !== 'forgot'" class="ecaf-google">
      <div class="ecaf-divider"><span>o continuá con</span></div>
      <div ref="googleEl" class="ecaf-google-btn" :class="{ 'is-busy': googleBusy }"></div>
      <p v-if="mode === 'register'" class="ecaf-terms-note">
        Al continuar con Google también aceptás los
        <RouterLink :to="legalTo('terms')" target="_blank" rel="noopener">Términos</RouterLink> y la
        <RouterLink :to="legalTo('privacy')" target="_blank" rel="noopener">Política de privacidad</RouterLink>.
      </p>
    </div>

    <footer class="ecaf-foot">
      <template v-if="mode === 'login'">
        <span class="ecaf-foot-text">¿No tenés cuenta?</span>
        <button type="button" class="ecaf-link" @click="switchMode('register')">Registrate</button>
      </template>
      <template v-else-if="mode === 'register'">
        <span class="ecaf-foot-text">¿Ya tenés cuenta?</span>
        <button type="button" class="ecaf-link" @click="switchMode('login')">Ingresá</button>
        <button v-if="registeredPending" type="button" class="ecaf-link ecaf-link-resend" :disabled="resendBusy" @click="resendVerification">Reenviar correo de verificación</button>
      </template>
      <template v-else>
        <button type="button" class="ecaf-link" @click="switchMode('login')">
          <AppIcon name="arrow-left" :size="13" aria-hidden="true" /> Volver a ingresar
        </button>
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
  box-shadow: 0 6px 14px -8px color-mix(in srgb, var(--store-accent-ink, #111) 70%, transparent);
  transform: translate3d(calc(var(--ecaf-switch-i, 0) * 100%), 0, 0);
  transition: transform .3s ease;
  pointer-events: none;
}
.ecaf-switch-btn {
  position: relative; z-index: 1;
  min-height: 40px; padding: 8px 4px;
  border: 0; border-radius: 999px; background: none;
  font: inherit; font-size: 13px; font-weight: 600; letter-spacing: .01em;
  color: var(--sp-ink-2, var(--sp-muted, #5b6678));
  cursor: pointer;
  transition: color .2s ease;
}
.ecaf-switch-btn.is-on { color: var(--sp-on-band, #fff); font-weight: 700; }
.ecaf-switch-btn:hover:not(.is-on) { color: var(--sp-ink, #0f172a); }
.ecaf-switch-btn:focus-visible {
  outline: 2px solid var(--sp-accent-text, var(--store-accent-ink, #111));
  outline-offset: 2px;
}
.ecaf { display: grid; gap: 16px; }
/* Mensajes de estado: icono + texto en un solo plano (el <p> sigue siendo
   el contenedor para que role/tabindex no cambien). */
.ecaf-notice, .ecaf-error {
  display: flex; align-items: flex-start; gap: 9px;
  margin: 0; padding: 11px 14px; border-radius: 12px;
  font-size: 13.5px; line-height: 1.45;
}
.ecaf-msg-ico { flex: none; margin-top: 2px; }
.ecaf-notice {
  background: color-mix(in srgb, var(--sp-success, #0E7A55) 13%, transparent);
  border: 1px solid color-mix(in srgb, var(--sp-success, #0E7A55) 32%, transparent);
  color: var(--sp-ink-2, inherit);
}
.ecaf-notice .ecaf-msg-ico { color: var(--sp-success, #0E7A55); }
.ecaf-error {
  background: color-mix(in srgb, var(--sp-danger, #B42318) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--sp-danger, #B42318) 30%, transparent);
  color: var(--sp-ink-2, inherit);
}
.ecaf-error .ecaf-msg-ico { color: var(--sp-danger, #B42318); }
.ecaf-form { display: grid; gap: 14px; }
/* Campos (fallback neutro minimalista): las hojas store-design-*.css
   redefinen .sp-field-label/.sp-input/.sp-form-error bajo selectores
   [data-design] con más especificidad — esto solo gobierna la base. */
.ecaf .sp-field { gap: 7px; }
.ecaf .sp-field-label {
  font-size: 12.5px; font-weight: 650; letter-spacing: .01em;
  text-transform: none;
  color: var(--sp-ink-2, var(--sp-ink, #0f172a));
  transition: color .18s ease;
}
.ecaf .sp-field:focus-within .sp-field-label {
  color: var(--sp-accent-text, var(--store-accent-ink, #111));
}
.ecaf-labelrow { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ecaf-minilink {
  border: none; background: none; padding: 2px 0;
  font: inherit; font-size: 12px; font-weight: 600;
  color: var(--sp-muted, #5b6678); cursor: pointer;
}
.ecaf-minilink:hover { color: var(--sp-accent-text, var(--store-accent-ink, #111)); text-decoration: underline; text-underline-offset: 2px; }
.ecaf-minilink:disabled { opacity: .55; cursor: default; }
.ecaf .sp-input {
  min-height: 46px; padding: 11px 14px;
  border: 1px solid var(--sp-line, rgba(127, 127, 127, .32));
  border-radius: calc(var(--sp-radius, 16px) * .75);
  background: var(--sp-card-solid, var(--sp-card, #fff));
  color: var(--sp-ink, #0f172a); font-size: 15px;
  transition: border-color .16s, box-shadow .16s, background-color .16s;
}
.ecaf .sp-input:hover:not(:disabled):not(:focus) {
  border-color: color-mix(in srgb, var(--sp-ink, #0f172a) 34%, var(--sp-line, rgba(127, 127, 127, .32)));
}
.ecaf .sp-input:focus {
  outline: none;
  border-color: var(--store-accent, #4f46e5);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--store-accent, #4f46e5) 16%, transparent);
}
.ecaf .sp-input:disabled { opacity: .6; }
.ecaf .sp-input::placeholder { color: var(--sp-muted, #5b6678); opacity: .75; }
.ecaf .sp-input[aria-invalid='true'] { border-color: var(--sp-danger, #B42318); }
.ecaf .sp-input[aria-invalid='true']:focus {
  border-color: var(--sp-danger, #B42318);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-danger, #B42318) 16%, transparent);
}
.ecaf .sp-form-error {
  display: flex; align-items: flex-start;
  margin: -3px 0 0; font-size: 12.5px; font-weight: 550; line-height: 1.4;
  color: var(--sp-danger, #B42318);
}
.ecaf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ecaf-pass { position: relative; display: block; }
/* Icono líder del campo: el markup nace oculto (convención .ecaf-switch)
   y cada hoja de diseño lo enciende (p. ej. portico lo posiciona
   absolute sobre el input con su padding). */
.ecaf-ico { display: none; }
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
  margin-top: 4px; min-height: 48px; padding: 13px 18px;
  border: none; border-radius: calc(var(--sp-radius, 16px) * .75);
  background: var(--store-accent-ink, #111); color: var(--sp-on-band, #fff);
  font-size: 14.5px; font-weight: 700; letter-spacing: .01em; cursor: pointer;
  box-shadow: 0 12px 24px -14px color-mix(in srgb, var(--store-accent-ink, #111) 72%, transparent);
  transition: filter .15s, transform .12s, box-shadow .2s;
}
.ecaf-submit:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-1px); }
.ecaf-submit:active:not(:disabled) { transform: translateY(0); }
.ecaf-submit:disabled { opacity: .55; cursor: default; box-shadow: none; }
.ecaf-submit:focus-visible,
.ecaf-link:focus-visible,
.ecaf-minilink:focus-visible {
  outline: 2px solid var(--sp-accent-text, var(--store-accent-ink, #111));
  outline-offset: 2px;
  border-radius: 4px;
}
.ecaf-submit:focus-visible { border-radius: calc(var(--sp-radius, 16px) * .75); }
.ecaf-spin { animation: ecaf-rotate 1s linear infinite; }
@keyframes ecaf-rotate { to { transform: rotate(360deg); } }
.ecaf-google { margin-top: 2px; }
/* Consentimiento legal: checkbox + enlaces a las páginas legales de la
   tienda (rutas públicas /<slug>/legal/* o /legal/* en host de tienda). */
.ecaf-terms {
  display: flex; align-items: flex-start; gap: 9px;
  font-size: 13px; line-height: 1.45;
  color: var(--sp-ink-2, var(--sp-ink, #0f172a));
  cursor: pointer;
}
.ecaf-terms input[type='checkbox'] {
  flex: none; width: 16px; height: 16px; margin: 2px 0 0;
  accent-color: var(--store-accent, #4f46e5); cursor: pointer;
}
.ecaf-terms-text a {
  color: var(--sp-accent-text, var(--store-accent-ink, #111));
  font-weight: 600; text-decoration: underline; text-underline-offset: 2px;
}
.ecaf-terms-note {
  margin: 10px 0 0; font-size: 11.5px; line-height: 1.5; text-align: center;
  color: var(--sp-muted, #5b6678);
}
.ecaf-terms-note a { color: inherit; font-weight: 600; text-decoration: underline; text-underline-offset: 2px; }
.ecaf-divider {
  display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
  font-size: 11.5px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
  color: var(--sp-muted, #5b6678);
}
.ecaf-divider::before, .ecaf-divider::after { content: ''; flex: 1; height: 1px; background: var(--sp-line, currentColor); opacity: .5; }
.ecaf-google-btn { display: grid; place-items: center; min-height: 46px; }
.ecaf-google-btn.is-busy { opacity: .6; }
/* Pie: pregunta muted + acción en acento, centrado bajo el CTA. */
.ecaf-foot {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: center;
  gap: 4px 8px; padding-top: 2px;
}
.ecaf-foot-text { font-size: 13px; color: var(--sp-muted, #5b6678); }
.ecaf-link {
  display: inline-flex; align-items: center; gap: 5px;
  border: none; background: none; padding: 4px 2px;
  font-size: 13px; font-weight: 650; cursor: pointer;
  color: var(--sp-accent-text, var(--store-accent-ink, #111));
  text-decoration: none;
}
.ecaf-link:hover { text-decoration: underline; text-underline-offset: 3px; }
.ecaf-link:disabled { opacity: .55; cursor: default; }
@media (prefers-reduced-motion: reduce) {
  .ecaf-spin,
  .ecaf-switch-pill { animation: none; transition: none; }
}
@media (max-width: 480px) { .ecaf-grid { grid-template-columns: 1fr; } }
</style>
