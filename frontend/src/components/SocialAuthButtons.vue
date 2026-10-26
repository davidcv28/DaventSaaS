<script setup>
// Botones de login social (Google + Facebook).
// Google: botón OFICIAL de Google Identity Services (GIS) — el branding lo
// exige Google; renderiza un iframe con la cuenta del usuario. Facebook:
// botón propio que abre FB.login() del SDK de Meta.
// Ambos canjean su credencial en el backend (auth.socialLogin) que la
// verifica server-side — acá nunca se confía en el email del cliente.
// Sin VITE_GOOGLE_CLIENT_ID / VITE_FACEBOOK_APP_ID el provider no se muestra.
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.store.js'

const props = defineProps({
  // 'login' | 'register' — cambia el texto de los botones.
  mode: { type: String, default: 'login' }
})
const emit = defineEmits(['done', 'error'])
const auth = useAuthStore()

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
const FACEBOOK_APP_ID = import.meta.env.VITE_FACEBOOK_APP_ID || ''
const visible = computed(() => Boolean(GOOGLE_CLIENT_ID || FACEBOOK_APP_ID))

const googleEl = ref(null)
const busy = ref('') // '' | 'google' | 'facebook'

// Los SDKs externos se cargan una sola vez (por id) y bajo demanda.
const loadedScripts = new Set()
function loadScript(src, id) {
  if (loadedScripts.has(id) || document.getElementById(id)) {
    loadedScripts.add(id)
    return Promise.resolve()
  }
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src
    s.id = id
    s.async = true
    s.defer = true
    s.onload = () => { loadedScripts.add(id); resolve() }
    s.onerror = () => reject(new Error(`No se pudo cargar ${src}`))
    document.head.appendChild(s)
  })
}

// ---- Google Identity Services ----
async function initGoogle() {
  try {
    await loadScript('https://accounts.google.com/gsi/client', 'gsi-client')
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: onGoogleCredential,
    })
    // Botón oficial renderizado por Google dentro de su iframe. 'outline'
    // (blanco) es el estilo estándar para fondos claros como la auth card.
    window.google.accounts.id.renderButton(googleEl.value, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      shape: 'pill',
      logo_alignment: 'left',
      text: props.mode === 'register' ? 'signup_with' : 'continue_with',
      width: Math.min(Math.max(googleEl.value?.clientWidth || 300, 240), 400),
    })
  } catch {
    emit('error', 'No pudimos cargar el ingreso con Google. Intentá de nuevo.')
  }
}

async function onGoogleCredential({ credential }) {
  if (!credential) {
    emit('error', 'No recibimos la credencial de Google.')
    return
  }
  busy.value = 'google'
  try {
    await finish('google', credential)
  } finally {
    busy.value = ''
  }
}

// ---- Facebook Login (SDK de Meta) ----
let fbReadyPromise = null
function ensureFacebook() {
  // fbAsyncInit es el hook canónico: el SDK llama a esta función cuando
  // termina de cargar — ahí recién existe window.FB para inicializar.
  // Si el script ya cargó en un mount anterior (window.FB existe) el hook
  // no vuelve a correr: resolvemos directo para no colgar la promise.
  if (!fbReadyPromise) {
    fbReadyPromise = new Promise((resolve, reject) => {
      if (window.FB) { resolve(); return }
      window.fbAsyncInit = () => {
        window.FB.init({ appId: FACEBOOK_APP_ID, version: 'v21.0', cookie: false, xfbml: false })
        resolve()
      }
      loadScript('https://connect.facebook.net/es_LA/sdk.js', 'facebook-jssdk').catch(reject)
    })
  }
  return fbReadyPromise
}

async function onFacebook() {
  busy.value = 'facebook'
  try {
    await ensureFacebook()
    const resp = await new Promise((resolve) => {
      // auth_type:'rerequest' — si el usuario alguna vez rechazó el permiso
      // de email, Meta se lo vuelve a pedir (sin email el backend da 400).
      window.FB.login(resolve, { scope: 'email,public_profile', auth_type: 'rerequest' })
    })
    const token = resp?.authResponse?.accessToken
    if (!token) {
      emit('error', 'Cancelaste el inicio de sesión con Facebook.')
      return
    }
    await finish('facebook', token)
  } catch {
    emit('error', 'No pudimos cargar Facebook. Intentá de nuevo.')
  } finally {
    busy.value = ''
  }
}

async function finish(provider, token) {
  const res = await auth.socialLogin(provider, token)
  if (res.ok) {
    emit('done', res)
  } else {
    emit('error', auth.lastError || 'No pudimos iniciar sesión. Intentá de nuevo.')
  }
}

onMounted(() => {
  if (GOOGLE_CLIENT_ID) initGoogle()
})
</script>

<template>
  <div v-if="visible" class="social-auth">
    <div class="auth-divider"><span>{{ mode === 'register' ? 'o registrate con' : 'o ingresá con' }}</span></div>
    <div class="social-buttons">
      <div v-if="GOOGLE_CLIENT_ID" ref="googleEl" class="google-btn" :class="{ 'is-busy': busy === 'google' }"></div>
      <button
        v-if="FACEBOOK_APP_ID"
        type="button"
        class="btn-social btn-facebook"
        :disabled="busy !== ''"
        @click="onFacebook"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#1877F2" d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047v-2.66c0-3.025 1.792-4.697 4.533-4.697 1.313 0 2.686.236 2.686.236v2.971H15.83c-1.491 0-1.956.93-1.956 1.886v2.264h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>
        <span>{{ busy === 'facebook' ? 'Conectando…' : (mode === 'register' ? 'Registrate con Facebook' : 'Continuar con Facebook') }}</span>
      </button>
    </div>
    <p class="social-terms">
      Al continuar aceptás los <RouterLink to="/terminos" target="_blank">Términos y condiciones</RouterLink>.
    </p>
  </div>
</template>
