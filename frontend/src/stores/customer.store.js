import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { customerApi } from '../api/customer.api.js'
import {
  customerTokenStorage,
  hasCustomerSessionCookie,
  restoreCustomerSession,
} from '../api/customer.http.js'
import { extractApiError } from '../api/http.js'

// =============================================================================
// Sesión del COMPRADOR (Customer) — fuente única del lado de la tienda
// pública. Es INDEPENDIENTE de auth.store.js (sesión DAVENT del dueño):
// un dueño puede tener su sesión DAVENT y, en otra pestaña de su propia
// tienda, comprar como cliente sin que una pise a la otra (cookies y
// Bearer distintos: customer_* vs davent_*).
//
// accessToken: solo memoria (nunca localStorage). refresh: cookie
// httpOnly `customer_refresh` + CSRF `customer_csrf` (customer.http.js).
// =============================================================================
export const useCustomerStore = defineStore('customer', () => {
  const accessToken = ref(customerTokenStorage.getAccess())
  const customer = ref(null)
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const fieldErrors = ref({})

  const isAuthenticated = computed(() => Boolean(accessToken.value))
  const displayName = computed(() => {
    const c = customer.value
    if (!c) return ''
    return [c.first_name, c.last_name].filter(Boolean).join(' ') || c.email || ''
  })

  function applySession(data) {
    // Login/register/google devuelven {access, customer} — el refresh
    // viaja solo en cookie httpOnly (nunca en el body web).
    if (data?.access) {
      accessToken.value = data.access
      customerTokenStorage.set(data.access)
    }
    if (data?.customer) customer.value = data.customer
  }

  async function ensureSession() {
    if (accessToken.value) return true
    const ok = await restoreCustomerSession()
    if (ok) {
      accessToken.value = customerTokenStorage.getAccess()
      if (!customer.value) await fetchMe().catch(() => {})
    }
    return ok
  }

  function setError(err) {
    const parsed = extractApiError(err)
    const { nonField, status: _s, ...fields } = parsed
    lastError.value = nonField || Object.values(fields)[0] || 'Ocurrió un error'
    fieldErrors.value = fields
    return parsed
  }

  async function fetchMe() {
    const data = await customerApi.fetchMe()
    customer.value = data
    return data
  }

  async function register(payload) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    try {
      const data = await customerApi.register(payload)
      applySession(data)
      status.value = 'success'
      return { ok: true, isNew: true }
    } catch (err) {
      status.value = 'error'
      setError(err)
      return { ok: false }
    }
  }

  async function login(payload) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    try {
      const data = await customerApi.login(payload)
      applySession(data)
      status.value = 'success'
      return { ok: true }
    } catch (err) {
      status.value = 'error'
      setError(err)
      if (err.response?.status === 429) {
        lastError.value = 'Demasiados intentos. Esperá un minuto y probá de nuevo.'
      }
      return { ok: false }
    }
  }

  async function googleLogin(payload) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    try {
      const data = await customerApi.googleLogin(payload)
      applySession(data)
      status.value = 'success'
      return { ok: true, isNew: Boolean(data?.is_new) }
    } catch (err) {
      status.value = 'error'
      setError(err)
      return { ok: false }
    }
  }

  async function logout() {
    try { await customerApi.logout() } catch { /* sesión ya inválida */ }
    accessToken.value = null
    customerTokenStorage.clear()
    customer.value = null
    status.value = 'idle'
    lastError.value = ''
    fieldErrors.value = {}
  }

  // Evento de sesión expirada (customer.http.js lo emite una sola vez):
  // el caller (layout/vista de cuenta) decide qué mostrar — el store solo
  // limpia el estado local.
  function handleSessionExpired() {
    accessToken.value = null
    customerTokenStorage.clear()
    customer.value = null
    status.value = 'idle'
  }

  return {
    accessToken, customer, status, lastError, fieldErrors,
    isAuthenticated, displayName,
    applySession, ensureSession, fetchMe, register, login, googleLogin,
    logout, handleSessionExpired,
    hasSessionCookie: hasCustomerSessionCookie,
  }
})
