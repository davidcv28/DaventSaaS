import { createApp } from 'vue'
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
useAuthStore().initSession()
useThemeStore().initTheme()

app.mount('#app')
