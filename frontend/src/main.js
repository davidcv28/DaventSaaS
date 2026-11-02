import { createApp, watch } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router/index.js'
import { useAuthStore } from './stores/auth.store.js'
import { useThemeStore } from './stores/theme.store.js'
import { installNativeShims } from './utils/native.js'
import { checkAppUpdate } from './utils/appUpdate.js'
import './assets/styles.css'
import './assets/template-thumbs.css'

// Deploy con HTML viejo en caché: un chunk lazy pedido ya no existe en el
// servidor y el import falla. Recargar una vez trae el index.html nuevo.
window.addEventListener('vite:preloadError', (e) => {
  e.preventDefault()
  if (!sessionStorage.getItem('spa:chunk-reload')) {
    sessionStorage.setItem('spa:chunk-reload', '1')
    window.location.reload()
  }
})

installNativeShims()
// En la APK nativa: chequeo de versión publicada contra /api/config/
// (no-op en el browser — ver utils/appUpdate.js).
checkAppUpdate()

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Observabilidad: Sentry solo se activa con VITE_SENTRY_DSN en el build
// (vacío en dev no cambia nada). Import dinámico para no inflar el bundle
// inicial cuando no hay DSN.
if (import.meta.env.VITE_SENTRY_DSN) {
  import('@sentry/vue').then((Sentry) => {
    Sentry.init({
      app,
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.MODE,
    })
  }).catch(() => {})
}

// Restaura sesión desde la cookie httpOnly antes del primer render (FRONTEND_RULES §3).
const auth = useAuthStore()
auth.initSession()
useThemeStore().initTheme()

// Si la sesión cae estando dentro de una ruta protegida (logout o limpieza
// sin navegación), el guard no re-corre solo: forzar la salida al login.
watch(
  () => auth.isAuthenticated,
  (authed) => {
    if (!authed && router.currentRoute.value.meta?.requiresAuth) {
      router.push({ name: 'login' })
    }
  }
)

app.mount('#app')
