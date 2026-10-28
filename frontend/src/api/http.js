import axios from 'axios'
import { env } from '../config/env.js'

// =============================================================================
// Sesión JWT — modelo cookie-refresh (anti robo por XSS):
//   - El REFRESH vive en una cookie httpOnly/Secure/SameSite=Lax scopeada a
//     /api/token/ que setea el backend: el JS del frontend JAMÁS lo lee.
//   - El ACCESS vive solo en memoria del módulo (nunca en localStorage):
//     al recargar la pestaña se pierde y se renueva vía cookie (silent).
//   - Los endpoints que consumen la cookie exigen doble-submit CSRF:
//     cookie 'davent_csrf' (legible) == header X-CSRFToken.
// =============================================================================
const CSRF_COOKIE = 'davent_csrf'

// Higiene: tokens que hayan quedado en localStorage de versiones anteriores
// (pre cookie-refresh) se borran — un XSS no debería encontrar credenciales.
try {
  localStorage.removeItem('davent.access')
  localStorage.removeItem('davent.refresh')
} catch { /* storage bloqueado */ }

let accessToken = null
// Una vez iniciado el logout la cookie de refresh puede seguir viva unos ms
// (request en vuelo): bloquea cualquier intento de refresh que "reviviría"
// la sesión. Se libera al setear un access nuevo (login).
let sessionEnded = false
// El aviso de sesión expirada se emite UNA sola vez: con varias requests en
// vuelo cada 401 disparaba su propio evento y la redirección a /login.
let expiredNotified = false
// Generación de la sesión: sube con cada access nuevo (login) y con el
// logout. Un refresh que salió en la generación anterior se descarta al
// aterrizar — evita que el token de la cuenta vieja pise el de la nueva.
let sessionEpoch = 0

export const tokenStorage = {
  getAccess: () => accessToken,
  set: (access) => { if (access) { accessToken = access; sessionEnded = false; expiredNotified = false; sessionEpoch++ } },
  clear: () => { accessToken = null }
}

function csrfToken() {
  const m = document.cookie.match(/(?:^|;\s*)davent_csrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

// Hints de sesión legibles por JS (el refresh httpOnly no se puede tocar).
// Al morir la sesión hay que borrarlos: si sobrevive el CSRF, hasSessionCookie()
// sigue true y cada carga reintenta un refresh que ya sabemos que da 401.
const SESSION_HINT_COOKIES = ['davent_csrf', 'davent_remember']
function clearSessionHints() {
  for (const name of SESSION_HINT_COOKIES) {
    for (const path of ['/', '/api/token/']) {
      document.cookie = `${name}=; Max-Age=0; path=${path}`
    }
  }
}


// La cookie CSRF se setea junto al refresh httpOnly: su presencia es el hint
// de que existe una sesión recuperable (la propia cookie refresh es ilegible).
export function hasSessionCookie() {
  if (sessionEnded) return false
  return Boolean(csrfToken())
}

// Instancia única (FRONTEND_RULES §0: prohibido axios suelto en vistas)
export const http = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 30000,   // 15s era corto para el cold start del dyno gratis de Render (~30-60s)
  withCredentials: true, // la cookie de sesión viaja en refresh/logout
  headers: { 'Content-Type': 'application/json' }
})

// Cliente de lecturas públicas (web de tienda, catálogo, captcha, contacto,
// reseñas): sin interceptor de sesión ni cookies. Un access vencido en
// memoria no debe viajar acá — el backend ya no autentica estas acciones,
// pero el header sobra y arrastraba 401 cuando el token estaba rancio.
export const publicHttp = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// Origen al que apunta la API: '/api' (mismo origen) o URL absoluta (dev).
const API_ORIGIN = new URL(env.apiBaseUrl, window.location.href).origin

http.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess()
  if (token && !config.headers.Authorization) {
    // Anti token-leak: el Bearer solo viaja al origen de la API. Una URL
    // absoluta a otro dominio pasada por error no lleva credenciales.
    const base = new URL(config.baseURL || '/', window.location.href)
    const target = new URL(config.url || '', base)
    if (target.origin === API_ORIGIN) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

const tokenEndpoint = (path) => `${env.apiBaseUrl.replace(/\/$/, '')}/token/${path}`

async function refreshCall() {
  const epoch = sessionEpoch
  const res = await axios.post(tokenEndpoint('refresh/'), {}, {
    timeout: 30000,   // 15s era corto para el cold start del dyno gratis de Render (~30-60s)
    withCredentials: true,
    headers: { 'X-CSRFToken': csrfToken() }
  })
  const { access } = res.data || {}
  if (!access) throw new Error('EMPTY_REFRESH')
  // Un refresh que salió ANTES del logout o de un login nuevo puede aterrizar
  // DESPUÉS: sin este corte, tokenStorage.set deja un access zombie en memoria
  // — ensureSession() lo revive en /login y el guard rebota al panel ("logout
  // no redirecciona"), o peor: el token de la cuenta vieja pisa el de la que
  // acaba de entrar. Se descarta aunque sea válido.
  if (sessionEnded || epoch !== sessionEpoch) throw new Error('SESSION_ENDED')
  tokenStorage.set(access)
  return access
}

// Refresh single-flight POR TAB y entre tabs (Web Locks): con refresh
// rotation+blacklist, dos tabs refrescando a la vez con la misma cookie harían
// fallar a la segunda (token ya rotado) — el lock serializa y la segunda
// petición sale ya con la cookie nueva.
let refreshPromise = null

async function tryRefresh() {
  if (!refreshPromise) {
    if (!hasSessionCookie()) return Promise.reject(new Error('NO_SESSION'))
    const job = navigator.locks?.request
      ? () => navigator.locks.request('davent:refresh', refreshCall)
      : refreshCall
    refreshPromise = job()
      .catch((err) => {
        // SESSION_ENDED = refresh descartado por época (logout o login nuevo):
        // no tocar el storage — clear() borraría el access de la sesión nueva.
        if (err?.message !== 'SESSION_ENDED') {
          tokenStorage.clear()
          // 401 del refresh = cookie httpOnly inválida, expirada, rotada por
          // otra pestaña o blacklisteada (cambio de clave). Los hints se
          // borran para cortar el ciclo: hasSessionCookie() pasa a false y no
          // se reintenta el refresh en cada carga ni en otras pestañas.
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

// Restaura la sesión al recargar el tab (el access en memoria se perdió).
// Devuelve true si quedó un access válido.
export async function restoreSession() {
  // Sesión cerrada en este tab: no revivirla aunque quede algo en memoria
  // (segunda capa tras el corte de refreshCall — cubre cualquier set que
  // haya aterrizado entre el clear() del logout y sessionEnded=true).
  if (sessionEnded) return false
  if (tokenStorage.getAccess()) return true
  try {
    await tryRefresh()
    return true
  } catch {
    return false
  }
}

// Cierre real: blacklist del refresh en backend + borrado de cookies, y limpia
// el access en memoria. Falla silenciosamente si la cookie ya expiró.
export async function logoutSession() {
  sessionEnded = true // ningún refresh puede resucitar la sesión saliente
  sessionEpoch++     // los refresh en vuelo se descartan aunque respondan OK
  try {
    await axios.post(tokenEndpoint('logout/'), {}, {
      timeout: 10000,
      withCredentials: true,
      headers: { 'X-CSRFToken': csrfToken() }
    })
  } catch {
    // Sesión ya inválida/expirada en server: igual se limpia local.
  }
  tokenStorage.clear()
  clearSessionHints()
}

http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config || {}
    const status = error.response?.status
    const url = original.url || ''

    // No reintentar los propios endpoints de token.
    const isAuthEndpoint =
      url.includes('/token/refresh/') ||
      url.includes('/token/verify/') ||
      url.includes('/token/logout/')
    if (status === 401 && !original._retried && !isAuthEndpoint && hasSessionCookie()) {
      original._retried = true
      try {
        const access = await tryRefresh()
        original.headers = { ...(original.headers || {}), Authorization: `Bearer ${access}` }
        return http(original)
      } catch (e) {
        // Refresh fallido -> sesión expirada. El store redirige a /login?expired=1.
        // SESSION_ENDED no se reporta: el usuario está saliendo o ya entró otra
        // cuenta — el evento haría location.assign y pisaría esa navegación.
        if (e?.message !== 'SESSION_ENDED' && !expiredNotified) {
          expiredNotified = true
          window.dispatchEvent(new CustomEvent('davent:session-expired'))
        }
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

export function extractApiError(error) {
  // Normaliza errores DRF: {field: [msgs]} | {detail} | string
  if (!error) return { nonField: 'Error desconocido' }
  const data = error.response?.data
  const status = error.response?.status
  if (error.code === 'PENDING_BACKEND') return { nonField: error.message, pendingBackend: true }
  if (!error.response) return { nonField: 'No se pudo conectar con la API. Verifica que Django corra en 127.0.0.1:8000.' }
  if (typeof data === 'string') {
    // Django a veces responde páginas HTML (500/404 fuera de DRF): nunca volcarlas crudas a la UI.
    const clean = data.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
    const looksLikeHtml = /<(!doctype|html|head|body|div|p|title)[\s>]/i.test(data)
    if (looksLikeHtml || clean.length > 280) {
      return { nonField: `El servidor respondió con un error (${status || 'desconocido'}). Intentá de nuevo en unos minutos.`, status }
    }
    return { nonField: clean || `Error ${status || ''}`.trim(), status }
  }
  if (data?.detail) return { nonField: String(data.detail), status }
  if (data && typeof data === 'object') {
    const out = { status }
    for (const [key, value] of Object.entries(data)) {
      out[key] = Array.isArray(value) ? value.join(' ') : String(value)
    }
    return out
  }
  return { nonField: `Error ${status || ''}`.trim() }
}
