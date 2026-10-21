import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { authApi, buildRegisterPayload } from '../api/auth.api.js'
import { http, tokenStorage, extractApiError } from '../api/http.js'

// Única fuente de sesión (FRONTEND_RULES §3).
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(tokenStorage.getAccess())
  const refreshToken = ref(tokenStorage.getRefresh())
  const user = ref(null)
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const fieldErrors = ref({})
  const usingApiFallback = ref(false)

  const isAuthenticated = computed(() => Boolean(accessToken.value))

  function applyTokens({ access, refresh }) {
    if (access) accessToken.value = access
    if (refresh) refreshToken.value = refresh
    tokenStorage.set(access, refresh)
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

  function logout() {
    tokenStorage.clear()
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    status.value = 'idle'
    lastError.value = ''
    fieldErrors.value = {}
  }

  function initFromStorage() {
    accessToken.value = tokenStorage.getAccess()
    refreshToken.value = tokenStorage.getRefresh()
    if (accessToken.value) fetchMe().catch(() => {})
    window.addEventListener('davent:session-expired', () => {
      logout()
      const here = window.location.pathname
      if (!here.includes('/login')) window.location.assign('/login?expired=1')
    })
  }

  return {
    accessToken, refreshToken, user, status, lastError, fieldErrors,
    isAuthenticated, usingApiFallback,
    login, register, fetchMe, updateAccount, updatePassword, logout, initFromStorage,
    http
  }
})
