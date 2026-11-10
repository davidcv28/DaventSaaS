import axios from 'axios'
import { env } from '../config/env.js'

// =============================================================================
// Sesión del COMPRADOR (Customer) — dominio distinto de la sesión DAVENT:
//   - El REFRESH vive en la cookie httpOnly `customer_refresh` (Path=/api/,
//     30 días, SameSite=Lax, Secure fuera de DEBUG) que setea el backend.
//   - El ACCESS JWT viaja en `Authorization: Bearer` y vive SOLO en memoria
//     del módulo (nunca localStorage — misma regla anti-XSS que http.js).
//   - La cookie CSRF legible `customer_csrf` se devuelve en el header
//     X-CSRFToken (doble-submit) en refresh/logout.
//   - El refresh rota en cada uso y el viejo queda blacklisteado: un replay
//     devuelve 401 y la sesión muere (fail-closed, como DAVENT).
//   - Los endpoints de comprador NO aceptan el JWT DAVENT ni viceversa:
//     esta instancia es exclusiva de /api/customer*/ y /api/cart/.
// =============================================================================
// Higiene: por si una versión vieja guardó tokens en localStorage.
try {
  localStorage.removeItem('customer.access')
  localStorage.removeItem('customer.refresh')
} catch { /* storage bloqueado */ }

let accessToken = null
// Logout o refresh fallido: bloquea que un refresh en vuelo "reviva" la
// sesión (misma época que http.js — sube con cada access nuevo).
let sessionEnded = false
let expiredNotified = false
let sessionEpoch = 0

export const customerTokenStorage = {
  getAccess: () => accessToken,
  set: (access) => { if (access) { accessToken = access; sessionEnded = false; expiredNotified = false; sessionEpoch++ } },
  clear: () => { accessToken = null }
}

export function customerCsrfToken() {
  const m = document.cookie.match(/(?:^|;\s*)customer_csrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}
const csrfToken = customerCsrfToken

const SESSION_HINT_COOKIES = ['customer_csrf']
function clearSessionHints() {
  for (const name of SESSION_HINT_COOKIES) {
    for (const path of ['/', '/api/']) {
      document.cookie = `${name}=; Max-Age=0; path=${path}`
    }
  }
}

// La cookie CSRF es el hint legible de que existe una sesión recuperable
// (la refresh httpOnly no se puede inspeccionar desde JS).
export function hasCustomerSessionCookie() {
  if (sessionEnded) return false
  return Boolean(csrfToken())
}

// Instancia única del dominio comprador (misma regla que http.js: nada de
// axios suelto en vistas — todo pasa por customerHttp o publicHttp).
export const customerHttp = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 30000,
  withCredentials: true, // la cookie customer_refresh viaja en refresh/logout
  headers: { 'Content-Type': 'application/json' }
})

const API_ORIGIN = new URL(env.apiBaseUrl, window.location.href).origin

customerHttp.interceptors.request.use((config) => {
  const token = customerTokenStorage.getAccess()
  if (token && !config.headers.Authorization) {
    // Anti token-leak: el Bearer del comprador solo viaja al origen de la API.
    const base = new URL(config.baseURL || '/', window.location.href)
    const target = new URL(config.url || '', base)
    if (target.origin === API_ORIGIN) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

const refreshEndpoint = `${env.apiBaseUrl.replace(/\/$/, '')}/customer-auth/refresh/`

async function refreshCall() {
  const epoch = sessionEpoch
  const res = await axios.post(refreshEndpoint, {}, {
    timeout: 30000,
    withCredentials: true,
    headers: { 'X-CSRFToken': csrfToken() }
  })
  const { access } = res.data || {}
  if (!access) throw new Error('EMPTY_REFRESH')
  // Un refresh que salió antes del logout/login nuevo se descarta al
  // aterrizar (misma protección de época que la sesión DAVENT).
  if (sessionEnded || epoch !== sessionEpoch) throw new Error('SESSION_ENDED')
  customerTokenStorage.set(access)
  return access
}

// Refresh single-flight por tab y entre tabs (Web Locks): el refresh rota
// y se blacklistea — dos pestañas refrescando a la vez con la misma cookie
// harían fallar a la segunda (token ya rotado).
let refreshPromise = null

async function tryRefresh() {
  if (!refreshPromise) {
    if (!hasCustomerSessionCookie()) return Promise.reject(new Error('NO_SESSION'))
    const job = navigator.locks?.request
      ? () => navigator.locks.request('davent:customer-refresh', refreshCall)
      : refreshCall
    refreshPromise = job()
      .catch((err) => {
        if (err?.message !== 'SESSION_ENDED') {
          customerTokenStorage.clear()
          // 401 del refresh = cookie inválida/expirada/rotada/blacklisteada:
          // se borran los hints para cortar el ciclo de reintentos.
          if (err?.response?.status === 401) clearSessionHints()
        }
        throw err
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

// Restaura la sesión del comprador al recargar (el access en memoria se
// perdió pero la cookie refresh puede seguir viva). Devuelve true si quedó
// un access válido.
export async function restoreCustomerSession() {
  if (sessionEnded) return false
  if (customerTokenStorage.getAccess()) return true
  try {
    await tryRefresh()
    return true
  } catch {
    return false
  }
}

// Logout real: blacklist del refresh en backend + limpieza de cookies.
export async function logoutCustomerSession() {
  sessionEnded = true
  sessionEpoch++
  try {
    await axios.post(
      `${env.apiBaseUrl.replace(/\/$/, '')}/customer-auth/logout/`,
      {},
      {
        timeout: 10000,
        withCredentials: true,
        headers: { 'X-CSRFToken': csrfToken() }
      }
    )
  } catch {
    // Sesión ya inválida/expirada en server: igual se limpia local.
  }
  customerTokenStorage.clear()
  clearSessionHints()
}

customerHttp.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config || {}
    const status = error.response?.status
    const url = original.url || ''

    // No reintentar los propios endpoints de sesión.
    const isAuthEndpoint = url.includes('/customer-auth/')
    if (status === 401 && !original._retried && !isAuthEndpoint) {
      original._retried = true
      if (!hasCustomerSessionCookie()) {
        if (sessionEnded) return Promise.reject(error)
        // Sin cookie no hay refresh posible: la sesión del comprador murió
        // (otra pestaña cerró sesión, cookie expirada). Aviso único para que
        // la UI vuelva al estado "invitado" sin spamear 401 en polling.
        if (!expiredNotified) {
          expiredNotified = true
          window.dispatchEvent(new CustomEvent('davent:customer-session-expired'))
        }
        return Promise.reject(error)
      }
      try {
        const access = await tryRefresh()
        original.headers = { ...(original.headers || {}), Authorization: `Bearer ${access}` }
        return customerHttp(original)
      } catch (e) {
        if (e?.message !== 'SESSION_ENDED' && !expiredNotified) {
          expiredNotified = true
          window.dispatchEvent(new CustomEvent('davent:customer-session-expired'))
        }
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

// Reexport del normalizador de errores de http.js (misma forma DRF).
export { extractApiError } from './http.js'
