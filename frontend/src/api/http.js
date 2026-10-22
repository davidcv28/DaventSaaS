import axios from 'axios'
import { env } from '../config/env.js'

const ACCESS_KEY = 'davent.access'
const REFRESH_KEY = 'davent.refresh'

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access, refresh) => {
    if (access) localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }
}

// Instancia única (FRONTEND_RULES §0: prohibido axios suelto en vistas)
export const http = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 15000,
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

// Refresh single-flight: una sola petición de refresh aunque fallen N llamadas 401.
let refreshPromise = null

async function tryRefresh() {
  if (!refreshPromise) {
    const refresh = tokenStorage.getRefresh()
    if (!refresh) return Promise.reject(new Error('NO_REFRESH'))
    refreshPromise = axios
      .post(`${env.apiBaseUrl.replace(/\/$/, '')}/token/refresh/`, { refresh }, { timeout: 15000 })
      .then((res) => {
        const { access, refresh: rotated } = res.data || {}
        if (!access) throw new Error('EMPTY_REFRESH')
        tokenStorage.set(access, rotated || refresh)
        return access
      })
      .catch((err) => {
        tokenStorage.clear()
        throw err
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config || {}
    const status = error.response?.status
    const url = original.url || ''

    // No reintentar el propio refresh ni login.
    const isAuthEndpoint = url.includes('/token/refresh/') || url.includes('/token/verify/')
    if (status === 401 && !original._retried && !isAuthEndpoint && tokenStorage.getRefresh()) {
      original._retried = true
      try {
        const access = await tryRefresh()
        original.headers = { ...(original.headers || {}), Authorization: `Bearer ${access}` }
        return http(original)
      } catch (e) {
        // Refresh fallido -> sesión expirada. El store redirige a /login?expired=1
        window.dispatchEvent(new CustomEvent('davent:session-expired'))
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
