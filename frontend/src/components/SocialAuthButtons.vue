<script setup>
// Botón de login social con Google Identity Services (GIS).
// El branding lo exige Google: renderiza un iframe con la cuenta del usuario.
// La credencial se canjea en el backend (auth.socialLogin) que la verifica
// server-side — acá nunca se confía en el email del cliente.
// Sin VITE_GOOGLE_CLIENT_ID el botón no se muestra (feature apagada).
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.store.js'

const props = defineProps({
  // 'login' | 'register' — cambia el texto del botón.
  mode: { type: String, default: 'login' }
})
const emit = defineEmits(['done', 'error'])
const auth = useAuthStore()

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
const visible = Boolean(GOOGLE_CLIENT_ID)

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

onMounted(() => {
  if (GOOGLE_CLIENT_ID) initGoogle()
})
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
