// Update checker de la APK (distribución web directa — no hay Play Store
// que avise). Al boot en plataforma nativa compara el versionCode instalado
// (App.getInfo) con el publicado por GET /api/config/ y expone el estado en
// `appUpdate` para que AppUpdateBanner lo pinte:
//   - versionCode publicado > instalado  -> aviso descartable; el "ahora no"
//     se snoozea POR versión (vuelve a avisar cuando salga una más nueva).
//   - min_supported > instalado          -> aviso BLOQUEANTE, sin descarte.
// "Actualizar" abre la URL del APK en el browser del sistema: Android la
// descarga e instala encima de la app (mismo keystore — ver AGENTS.md).
import { reactive } from 'vue'
import { Capacitor } from '@capacitor/core'
import { App } from '@capacitor/app'
import { Browser } from '@capacitor/browser'
import { fetchAppInfo } from '../api/app.api.js'

const SNOOZE_KEY = 'davent:apk-update-snooze'

export const appUpdate = reactive({
  // Metadata publicada cuando hay update ({version_name, version_code,
  // apk_url, min_supported?}); null = al día, sin app o check no corrido.
  available: null,
  // Update obligatorio (min_supported por encima de lo instalado).
  required: false,
})

export async function checkAppUpdate() {
  if (!Capacitor.isNativePlatform()) return
  try {
    const [info, self] = await Promise.all([fetchAppInfo(), App.getInfo()])
    if (!info?.apk_url || !info?.version_code) return
    const installedCode = parseInt(self.build, 10) || 0
    if (info.min_supported && installedCode < info.min_supported) {
      appUpdate.required = true
      appUpdate.available = info
      return
    }
    if (info.version_code > installedCode) {
      // Snooze por versión: si el usuario dijo "ahora no" para ESTA
      // version_code no se repite el aviso hasta la próxima publicación.
      let snoozed = ''
      try { snoozed = localStorage.getItem(SNOOZE_KEY) || '' } catch { /* noop */ }
      if (snoozed === String(info.version_code)) return
      appUpdate.available = info
    }
  } catch { /* sin red o endpoint caído: el boot sigue normal */ }
}

export function dismissAppUpdate() {
  if (appUpdate.available?.version_code) {
    try { localStorage.setItem(SNOOZE_KEY, String(appUpdate.available.version_code)) } catch { /* noop */ }
  }
  appUpdate.available = null
}

export function openAppUpdate() {
  const url = appUpdate.available?.apk_url
  if (url) Browser.open({ url })
}
