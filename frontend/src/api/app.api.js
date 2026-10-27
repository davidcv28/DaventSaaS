import { http } from './http.js'
import { env } from '../config/env.js'

// ---------------------------------------------------------------------------
// App Android (APK por distribución web directa).
// La metadata de la versión publicada viaja en el bloque 'app' de
// GET /api/config/ (env APP_APK_* del backend); el link de descarga tiene
// cadena de fallback: server publicado > VITE_APP_APK_URL > URL estable.
// ---------------------------------------------------------------------------

let appInfoPromise = null

// Info de la APK publicada ({version_name, version_code, apk_url,
// min_supported?}) — se pide una sola vez por carga de la app. null si el
// server todavía no publica binario o el endpoint falla.
export function fetchAppInfo() {
  if (!appInfoPromise) {
    appInfoPromise = http.get('/config/')
      .then(({ data }) => data?.app || null)
      .catch(() => null)
  }
  return appInfoPromise
}

// URL final de descarga: la que publica el server, si no la de la env.
export async function resolveApkUrl() {
  const info = await fetchAppInfo()
  return info?.apk_url || env.appApkUrl
}

// Dispositivo Android (teléfono o tablet) por User-Agent: la promoción de la
// app solo se muestra donde puede instalarse.
export function isAndroidDevice() {
  return /android/i.test(navigator.userAgent || '')
}
