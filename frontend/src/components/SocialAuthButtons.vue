<script>
// Scope de módulo (corre una vez por carga de la app, no por instancia):
// login y register montan el componente — una sola llamada a /api/config/.
import { http } from '../api/http.js'

let configPromise = null
function fetchClientId() {
  if (!configPromise) {
    configPromise = http.get('/config/')
      .then(({ data }) => (data?.google_client_id || '').trim())
      .catch(() => '')
  }
  return configPromise
}
</script>

<script setup>
// Botón de login social con Google Identity Services (GIS).
// El branding lo exige Google: renderiza un iframe con la cuenta del usuario.
// La credencial se canjea en el backend (auth.socialLogin) que la verifica
// server-side — acá nunca se confía en el email del cliente.
// El client ID llega en runtime desde GET /api/config/ (env del backend —
// no se hornea en el bundle ni viaja en el build de la imagen). Como
// override de dev queda VITE_GOOGLE_CLIENT_ID en frontend/.env. Sin ID en
// ambos lados el botón no se muestra (feature apagada).
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Capacitor } from '@capacitor/core'
import { SocialLogin } from '@capgo/capacitor-social-login'
import { useAuthStore } from '../stores/auth.store.js'

const props = defineProps({
  // 'login' | 'register' — cambia el texto del botón.
  mode: { type: String, default: 'login' }
})
const emit = defineEmits(['done', 'error'])
const auth = useAuthStore()

const clientId = ref(import.meta.env.VITE_GOOGLE_CLIENT_ID || '')
const visible = ref(Boolean(clientId.value))
const isNative = Capacitor.isNativePlatform()
let nativeReady = false

const googleEl = ref(null)
const busy = ref(false)

// El SDK externo se carga una sola vez (por id) y bajo demanda.
function loadScript(src, id) {
  if (document.getElementById(id)) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src
    s.id = id
    s.async = true
    s.defer = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error(`No se pudo cargar ${src}`))
    document.head.appendChild(s)
  })
}

let resizeObs = null

function renderGoogleButton() {
  const el = googleEl.value
  if (!el) return
  el.innerHTML = ''
  // Botón oficial renderizado por Google dentro de su iframe. 'outline'
  // (blanco) es el estilo estándar para fondos claros como la auth card.
  // El ancho es un número fijo de px: se recalcula y re-renderiza al
  // redimensionar (ResizeObserver) para que nunca desborde el contenedor.
  window.google.accounts.id.renderButton(el, {
    type: 'standard',
    theme: 'outline',
    size: 'large',
    shape: 'pill',
    logo_alignment: 'left',
    text: props.mode === 'register' ? 'signup_with' : 'continue_with',
    width: Math.min(Math.max(el.clientWidth || 300, 200), 400),
  })
}

async function initGoogle() {
  try {
    await loadScript('https://accounts.google.com/gsi/client', 'gsi-client')
    window.google.accounts.id.initialize({
      client_id: clientId.value,
      callback: onGoogleCredential,
    })
    renderGoogleButton()
    // Re-render cuando cambia el ancho disponible (rotación, sidebar,
    // resize del browser): el iframe del botón tiene ancho fijo en px.
    let timer = null
    let lastW = googleEl.value?.clientWidth || 0
    resizeObs = new ResizeObserver(() => {
      const w = googleEl.value?.clientWidth || 0
      if (!w || w === lastW) return
      lastW = w
      clearTimeout(timer)
      timer = setTimeout(renderGoogleButton, 150)
    })
    resizeObs.observe(googleEl.value)
  } catch {
    emit('error', 'No pudimos cargar el ingreso con Google. Intentá de nuevo.')
  }
}

async function onGoogleCredential({ credential }) {
  if (!credential) {
    emit('error', 'No recibimos la credencial de Google.')
    return
  }
  busy.value = true
  try {
    const res = await auth.socialLogin(credential)
    if (res.ok) {
      emit('done', res)
    } else {
      emit('error', auth.lastError || 'No pudimos iniciar sesión. Intentá de nuevo.')
    }
  } finally {
    busy.value = false
  }
}

// APK (nativo): Google bloquea el OAuth dentro de WebViews (403
// disallowed_useragent), así que el sign-in corre por el plugin nativo
// (Credential Manager de Android → account picker del SO). El webClientId
// es el mismo GOOGLE_CLIENT_ID del backend: el idToken que devuelve lleva
// ese aud y lo verifica el mismo POST /api/auth/google/ de la web.
async function initNative() {
  try {
    await SocialLogin.initialize({ google: { webClientId: clientId.value } })
    nativeReady = true
    visible.value = true
  } catch {
    emit('error', 'No pudimos cargar el ingreso con Google. Intentá de nuevo.')
  }
}

async function onNativeGoogleTap() {
  if (!nativeReady || busy.value) return
  busy.value = true
  try {
    const res = await SocialLogin.login({ provider: 'google', options: {} })
    const credential = res?.result?.idToken
    if (!credential) throw new Error('no-id-token')
    const login = await auth.socialLogin(credential)
    if (login.ok) {
      emit('done', login)
    } else {
      emit('error', auth.lastError || 'No pudimos iniciar sesión. Intentá de nuevo.')
    }
  } catch (err) {
    // El usuario puede cerrar el picker de cuentas — no es un error.
    // Cualquier otra falla (OAuth client faltante en Google Cloud, sin
    // cuenta Google en el dispositivo, Play Services viejo) se muestra con
    // el detalle crudo — un "canceled" de Credential Manager también cubre
    // errores de configuración, así que solo callamos el gesto del usuario.
    const msg = String(err?.message || err || '')
    console.error('[SocialLogin] Google sign-in falló:', err?.code, msg)
    const userGesture = /user.?cancel|canceled by user|12501/i.test(msg)
    if (!userGesture) {
      emit('error', `No pudimos iniciar sesión con Google. ${msg || 'Intentá de nuevo.'}`)
    }
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  // Sin override horneado, el ID se resuelve en runtime contra el backend.
  if (!clientId.value) {
    clientId.value = await fetchClientId()
    if (!clientId.value) return // feature apagada en el backend
  }
  if (isNative) {
    initNative()
    return
  }
  visible.value = true
  // El div del botón existe recién cuando v-if se repinta.
  await nextTick()
  initGoogle()
})

onUnmounted(() => resizeObs?.disconnect())
</script>

<template>
  <div v-if="visible" class="social-auth">
    <div class="auth-divider"><span>{{ mode === 'register' ? 'o registrate con' : 'o ingresá con' }}</span></div>
    <div class="social-buttons">
      <button v-if="isNative" type="button" class="google-native-btn" :disabled="busy" @click="onNativeGoogleTap">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#4285F4" d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.64h6.46a5.52 5.52 0 0 1-2.4 3.62v3h3.87c2.27-2.09 3.57-5.17 3.57-8.81z"/><path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.94-2.92l-3.87-3c-1.07.72-2.44 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.29v3.1A12 12 0 0 0 12 24z"/><path fill="#FBBC05" d="M5.27 14.27A7.2 7.2 0 0 1 4.89 12c0-.79.14-1.55.38-2.27v-3.1H1.29a12 12 0 0 0 0 10.74l3.98-3.1z"/><path fill="#EA4335" d="M12 4.77c1.76 0 3.34.61 4.58 1.8l3.44-3.44A11.98 11.98 0 0 0 12 0 12 12 0 0 0 1.29 6.63l3.98 3.1C6.22 6.88 8.87 4.77 12 4.77z"/></svg>
        <span>{{ mode === 'register' ? 'Registrate con Google' : 'Continuar con Google' }}</span>
      </button>
      <div v-else ref="googleEl" class="google-btn" :class="{ 'is-busy': busy }"></div>
    </div>
    <p class="social-terms">
      Al continuar aceptás los <RouterLink to="/terminos" target="_blank">Términos y condiciones</RouterLink>.
    </p>
  </div>
</template>
