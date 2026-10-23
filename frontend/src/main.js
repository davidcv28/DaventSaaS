import { createApp, watch } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router/index.js'
import { useAuthStore } from './stores/auth.store.js'
import { useThemeStore } from './stores/theme.store.js'
import './assets/styles.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

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
