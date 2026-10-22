import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { authApi, buildRegisterPayload } from '../api/auth.api.js'
import { http, tokenStorage, extractApiError, restoreSession, logoutSession } from '../api/http.js'

// Única fuente de sesión (FRONTEND_RULES §3).
// Access solo en memoria; el refresh es una cookie httpOnly que maneja http.js.
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(tokenStorage.getAccess())
  const user = ref(null)
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const fieldErrors = ref({})
  const usingApiFallback = ref(false)

  const isAuthenticated = computed(() => Boolean(accessToken.value))

  function applyTokens({ access }) {
    if (access) {
      accessToken.value = access
      tokenStorage.set(access)
    }
  }

  // Al recargar el tab el access en memoria se pierde: intenta renovarlo con
  // la cookie httpOnly (restoreSession no-ops si no hay cookie de sesión).
  async function ensureSession() {
    if (accessToken.value) return true
    const ok = await restoreSession()
    if (ok) accessToken.value = tokenStorage.getAccess()
    return ok
  }

  function setApiError(err) {
    const parsed = extractApiError(err)
    const { nonField, status: _s, pendingBackend, ...fields } = parsed
    lastError.value = nonField || Object.values(fields)[0] || 'Ocurrió un error'
    fieldErrors.value = fields
    return parsed
  }

  async function login({ username, password }) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    try {
      const data = await authApi.login({ username: username.trim(), password })
      applyTokens(data)
      status.value = 'success'
      await fetchMe().catch(() => {})
      return true
    } catch (err) {
      status.value = 'error'
      setApiError(err)
      if (err.response?.status === 429) {
        lastError.value = 'Demasiados intentos. Espera 60 segundos (protección anti fuerza bruta 5/min).'
      }
      return false
    }
  }

  async function register(form) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    try {
      const payload = buildRegisterPayload(form)
      const data = await authApi.register(payload)
      status.value = 'success'
      return { ok: true, message: data?.Exito || 'Usuario creado correctamente' }
    } catch (err) {
      status.value = 'error'
      const parsed = setApiError(err)
      if (err.response?.status === 404) {
        lastError.value =
          'La API aún no expone POST /api/register/ (falta incluir users.urls en DaventProject/urls.py). ' +
          'Avisá al backend para montar el router.'
      }
      return { ok: false, parsed }
    }
  }

  async function fetchMe() {
    if (!accessToken.value) return null
    try {
      const data = await authApi.fetchMe()
      // /profile/ devuelve objeto; /user/ puede devolver lista paginada.
      user.value = data?.results ? data.results[0] : data
      usingApiFallback.value = false
      return user.value
    } catch (err) {
      if (err.response?.status === 404) usingApiFallback.value = true
      return null
    }
  }

  // Correo (/user/me/) + perfil fiscal (/profile/me/) van a endpoints distintos.
  // Se disparan en paralelo y se consolidan los errores por campo.
  async function updateAccount({ email, profile }) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    const results = await Promise.allSettled([
      authApi.updateUser({ email }),
      authApi.updateProfile(profile)
    ])
    const errors = {}
    let failed = false
    for (const r of results) {
      if (r.status !== 'rejected') continue
      failed = true
      const { nonField, status: _s, pendingBackend: _p, ...fields } = extractApiError(r.reason)
      if (nonField && !lastError.value) lastError.value = nonField
      Object.assign(errors, fields)
    }
    fieldErrors.value = errors
    status.value = failed ? 'error' : 'success'
    if (failed) {
      if (!lastError.value) lastError.value = 'Algunos datos no se pudieron guardar. Revisá los campos marcados.'
      return { ok: false }
    }
    await fetchMe().catch(() => {})
    return { ok: true, message: 'Tus datos se actualizaron correctamente' }
  }

  async function updatePassword(payload) {
    status.value = 'loading'
    try {
      const data = await authApi.updatePassword(payload)
      status.value = 'success'
      return { ok: true, message: data?.Exito || 'Contraseña actualizada correctamente' }
    } catch (err) {
      status.value = 'error'
      const parsed = setApiError(err)
      return { ok: false, parsed }
    }
  }

  async function logout() {
    await logoutSession() // blacklist del refresh + borra cookies en backend
    accessToken.value = null
    user.value = null
    status.value = 'idle'
    lastError.value = ''
    fieldErrors.value = {}
  }

  function initSession() {
    window.addEventListener('davent:session-expired', () => {
      accessToken.value = null
      user.value = null
      const here = window.location.pathname
      if (!here.includes('/login')) window.location.assign('/login?expired=1')
    })
    // Recupera la sesión desde la cookie si el tab se recargó.
    ensureSession().then((ok) => { if (ok) fetchMe().catch(() => {}) })
  }

  return {
    accessToken, user, status, lastError, fieldErrors,
    isAuthenticated, usingApiFallback,
    login, register, fetchMe, updateAccount, updatePassword, logout, initSession, ensureSession,
    http
  }
})
