import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { Capacitor } from '@capacitor/core'

const STORAGE_KEY = 'davent:theme'
const META_COLOR = { light: '#4f46e5', dark: '#0d1220' }

// En nativo la status bar acompaña al tema activo (ambos fondos piden iconos
// claros). El import dinámico evita cargar el plugin en el bundle web.
function syncNativeBars(theme) {
  if (!Capacitor.isNativePlatform()) return
  import('@capacitor/status-bar').then(({ StatusBar, Style }) => {
    StatusBar.setBackgroundColor({ color: META_COLOR[theme] }).catch(() => {})
    StatusBar.setStyle({ style: Style.Light }).catch(() => {})
  }).catch(() => {})
}

function systemTheme() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function savedTheme() {
  try {
    const t = localStorage.getItem(STORAGE_KEY)
    return t === 'dark' || t === 'light' ? t : null
  } catch {
    return null
  }
}

// Tema claro/oscuro de la UI: se aplica como data-theme en <html> y se
// persiste en localStorage. Sin elección previa, sigue al sistema operativo.
export const useThemeStore = defineStore('theme', () => {
  const theme = ref('light')
  const isDark = computed(() => theme.value === 'dark')

  function apply() {
    document.documentElement.dataset.theme = theme.value
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', META_COLOR[theme.value])
    syncNativeBars(theme.value)
  }

  function setTheme(next) {
    if (next !== 'dark' && next !== 'light') return
    theme.value = next
    try { localStorage.setItem(STORAGE_KEY, next) } catch { /* storage bloqueado */ }
    apply()
  }

  function toggleTheme() {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  // Override temporal sin persistir (el panel de administración es siempre
  // oscuro). Al entrar guarda el tema vigente; al salir lo restaura sin
  // tocar localStorage.
  let forcedPrev = null
  function forceDark() {
    if (forcedPrev === null) forcedPrev = theme.value
    theme.value = 'dark'
    apply()
  }
  function releaseTheme() {
    if (forcedPrev === null) return
    theme.value = forcedPrev
    forcedPrev = null
    apply()
  }

  // Llamar una vez desde main.js (index.html ya setea data-theme para evitar FOUC).
  function initTheme() {
    // /admin es siempre oscuro (misma regla que theme-init.js), así el store
    // no pisa lo aplicado antes del primer paint.
    const isAdmin = /^\/admin(\/|$)/.test(location.pathname)
    theme.value = isAdmin ? 'dark' : savedTheme() || systemTheme()
    apply()
    window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', (e) => {
      // Mientras el usuario no elija a mano, el tema acompaña al SO.
      // Con el override forzado (admin) no se aplica.
      if (!isAdmin && !savedTheme() && forcedPrev === null) {
        theme.value = e.matches ? 'dark' : 'light'
        apply()
      }
    })
  }

  return { theme, isDark, setTheme, toggleTheme, forceDark, releaseTheme, initTheme }
})
