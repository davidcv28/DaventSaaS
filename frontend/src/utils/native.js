// Adaptación del SPA al WebView de Capacitor (APK Android).
// El WebView no tiene pestañas: window.open() y el patrón
// window.open('about:blank') + tab.location.href = url (checkout de MP,
// débito automático, links de compartir) se traducen a Browser.open, que
// lanza Chrome Custom Tab / el navegador del sistema. Se instala una sola
// vez desde main.js y SOLO en plataforma nativa: en el browser común queda
// el comportamiento original intacto.
import { Capacitor } from '@capacitor/core'
import { Browser } from '@capacitor/browser'
import { App } from '@capacitor/app'

function openExternal(url) {
  try {
    Browser.open({ url: new URL(url, window.location.href).href })
  } catch { /* noop */ }
}

// Botón back de Android: prioridad de lo que se cierra antes de navegar.
// Todos estos overlays ya escuchan Escape (chat de soporte, ventanas del
// admin, buscador global, lightboxes de galería, drawer de la tienda,
// menú de la landing); el <details> suelto se cierra por DOM y, como
// último recurso, se clickea un botón de cierre convencional.
const OVERLAY_SEL = [
  '.chat-overlay', '.chat-modal', '.chat-win', '.chat-dock-box',
  '.gs-overlay', '.lock-overlay', '.tour', '.sheet-scrim',
  '.sp-lightbox', '.sp-modal-overlay', '.sp-drawer.open', '.sp-overlay.open',
  '.lp-menu.open', '.modal', '[role="dialog"]',
].join(',')

const CLOSE_SEL = '[aria-label*="cerrar" i], [aria-label*="close" i], .sp-modal-close, .chat-x, .gs-x'

function dismissTopOverlay() {
  const details = document.querySelector('details[open]')
  const overlay = document.querySelector(OVERLAY_SEL)
  if (!details && !overlay) return false
  if (details) details.open = false
  // bubbles: alcanza los listeners de window Y de document.
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
  // Si Escape no lo cerró (Vue re-renderiza en microtask), toca el cierre
  // explícito: botón con "Cerrar" en su nombre accesible o el scrim mismo.
  setTimeout(() => {
    const still = document.querySelector(OVERLAY_SEL)
    if (!still) return
    const btn = still.matches(CLOSE_SEL) ? still : still.querySelector(CLOSE_SEL)
    if (btn) btn.click()
    else if (still.classList.contains('sp-overlay') || still.classList.contains('sheet-scrim') || still.classList.contains('gs-overlay')) {
      still.click()
    }
  }, 0)
  return true
}

function installBackButtonHandler() {
  App.addListener('backButton', ({ canGoBack }) => {
    // 1. Un overlay abierto se cierra y el back no navega.
    if (dismissTopOverlay()) return
    // 2. Con historial propio, back = página anterior del router.
    if (canGoBack) { window.history.back(); return }
    // 3. En la raíz: minimizar conserva sesión y estado (mejor que exitApp).
    App.minimizeApp()
  })
}

export function installNativeShims() {
  if (!Capacitor.isNativePlatform()) return
  installBackButtonHandler()
  // Pseudo-tab para los call sites existentes: asignar .location.href abre
  // el browser externo; close()/focus() son no-op. about:blank no navega
  // (el caller la usa como placeholder antes de setear la URL real).
  window.open = (url) => {
    const stub = { closed: false, close() {}, focus() {}, location: {} }
    if (url && url !== 'about:blank') openExternal(url)
    Object.defineProperty(stub.location, 'href', {
      set(v) { openExternal(v) },
      get() { return '' }
    })
    return stub
  }
}
