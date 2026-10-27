// Adaptación del SPA al WebView de Capacitor (APK Android).
// El WebView no tiene pestañas: window.open() y el patrón
// window.open('about:blank') + tab.location.href = url (checkout de MP,
// débito automático, links de compartir) se traducen a Browser.open, que
// lanza Chrome Custom Tab / el navegador del sistema. Se instala una sola
// vez desde main.js y SOLO en plataforma nativa: en el browser común queda
// el comportamiento original intacto.
import { Capacitor } from '@capacitor/core'
import { Browser } from '@capacitor/browser'

function openExternal(url) {
  try {
    Browser.open({ url: new URL(url, window.location.href).href })
  } catch { /* noop */ }
}

export function installNativeShims() {
  if (!Capacitor.isNativePlatform()) return
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
