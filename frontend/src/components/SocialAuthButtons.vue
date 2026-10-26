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
import { useAuthStore } from '../stores/auth.store.js'

const props = defineProps({
  // 'login' | 'register' — cambia el texto del botón.
  mode: { type: String, default: 'login' }
})
const emit = defineEmits(['done', 'error'])
const auth = useAuthStore()

const clientId = ref(import.meta.env.VITE_GOOGLE_CLIENT_ID || '')
const visible = ref(Boolean(clientId.value))

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

onMounted(async () => {
  // Sin override horneado, el ID se resuelve en runtime contra el backend.
  if (!clientId.value) {
    clientId.value = await fetchClientId()
    if (!clientId.value) return // feature apagada en el backend
    visible.value = true
    // El div del botón existe recién cuando v-if se repinta.
    await nextTick()
  }
  initGoogle()
})

onUnmounted(() => resizeObs?.disconnect())
</script>

<template>
  <div v-if="visible" class="social-auth">
    <div class="auth-divider"><span>{{ mode === 'register' ? 'o registrate con' : 'o ingresá con' }}</span></div>
    <div class="social-buttons">
      <div ref="googleEl" class="google-btn" :class="{ 'is-busy': busy }"></div>
    </div>
    <p class="social-terms">
      Al continuar aceptás los <RouterLink to="/terminos" target="_blank">Términos y condiciones</RouterLink>.
    </p>
  </div>
</template>
