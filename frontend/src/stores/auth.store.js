import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { authApi, buildRegisterPayload } from '../api/auth.api.js'
import { http, tokenStorage, extractApiError, restoreSession, logoutSession } from '../api/http.js'
import { resetSessionStores } from './session.js'

// Única fuente de sesión (FRONTEND_RULES §3).
// Access solo en memoria; el refresh es una cookie httpOnly que maneja http.js.
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(tokenStorage.getAccess())
  const user = ref(null)
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const fieldErrors = ref({})
  const usingApiFallback = ref(false)
  // Segundos de espera real del último 429 de login (Retry-After/retry_after):
  // la UI arma el cooldown con esto, no con un 60s fijo.
  const retryAfter = ref(0)

  const isAuthenticated = computed(() => Boolean(accessToken.value))

  // Dedup de /me (user+profile): lo piden initSession, los guards del router,
  // DashboardView y el opt-in de IA — una sola request en vuelo y cache corta.
  let mePromise = null
  let meFetchedAt = 0
  const ME_CACHE_MS = 10000

  function applyTokens({ access }) {
    if (access) {
      accessToken.value = access
      tokenStorage.set(access)
      // Sesión nueva = perfil nuevo: el cache de /me no puede heredarse.
      user.value = null
      meFetchedAt = 0
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
    const { nonField, status: _s, pendingBackend: _pb, retryAfter: _ra, non_field_errors, ...fields } = parsed
    // El banner global solo para errores generales; los de campo van inline
    // (fieldErrors). Antes el primer field-error se mostraba dos veces.
    // Fallback solo si no hay NI mensaje general NI campos (respuesta vacía).
    lastError.value = nonField || non_field_errors || (Object.keys(fields).length ? '' : 'Ocurrió un error')
    fieldErrors.value = fields
    return parsed
  }

  async function login({ username, password, remember = false }) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    retryAfter.value = 0
    try {
      const data = await authApi.login({ username: username.trim(), password, remember })
      // Cuenta nueva = estado limpio: nada de la sesión anterior (tienda, plan, pagos).
      resetSessionStores()
      applyTokens(data)
      status.value = 'success'
      await fetchMe().catch(() => {})
      return true
    } catch (err) {
      status.value = 'error'
      const parsed = setApiError(err)
      if (err.response?.status === 429) {
        // Cooldown con la espera REAL del backend (lockout 5/min), no un 60s
        // fijo que podía quedar corto o larguísimo de más.
        retryAfter.value = parsed.retryAfter || 60
      }
      return false
    }
  }

  // Login social (Google): la credencial del provider se canjea en el backend
  // (que la verifica server-side) y vuelve la misma sesión del login por
  // contraseña. Devuelve {ok, isNew, requiresPhone} para decidir la ruta.
  async function socialLogin(credential, remember = true) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    retryAfter.value = 0
    try {
      const data = await authApi.googleLogin(credential, remember)
      // Cuenta nueva = estado limpio: nada de la sesión anterior.
      resetSessionStores()
      applyTokens(data)
      status.value = 'success'
      await fetchMe().catch(() => {})
      return { ok: true, isNew: Boolean(data?.is_new), requiresPhone: Boolean(data?.requires_phone) }
    } catch (err) {
      status.value = 'error'
      const parsed = setApiError(err)
      if (err.response?.status === 429) retryAfter.value = parsed.retryAfter || 60
      return { ok: false }
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
      return { ok: true, message: data?.Exito || 'Usuario creado correctamente', coupon: data?.coupon || null }
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

  async function fetchMe({ force = false } = {}) {
    if (!accessToken.value) return null
    // Cache corta: /me lo piden initSession + guards + DashboardView por cada
    // navegación — sin esto eran 3-4 requests idénticos por carga.
    if (!force && user.value && Date.now() - meFetchedAt < ME_CACHE_MS) return user.value
    if (mePromise) return mePromise
    const token = accessToken.value
    mePromise = (async () => {
      try {
        const data = await authApi.fetchMe()
        // La sesión pudo cambiar mientras volaba el request (login/logout):
        // no pisar el user de la cuenta nueva con el de la anterior.
        if (accessToken.value !== token) return null
        // /profile/ devuelve objeto; /user/ puede devolver lista paginada.
        user.value = data?.results ? data.results[0] : data
        usingApiFallback.value = false
        meFetchedAt = Date.now()
        return user.value
      } catch (err) {
        if (err.response?.status === 404) usingApiFallback.value = true
        return null
      } finally {
        mePromise = null
      }
    })()
    return mePromise
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
      const { nonField, status: _s, pendingBackend: _p, retryAfter: _ra, ...fields } = extractApiError(r.reason)
      if (nonField && !lastError.value) lastError.value = nonField
      Object.assign(errors, fields)
    }
    fieldErrors.value = errors
    status.value = failed ? 'error' : 'success'
    if (failed) {
      if (!lastError.value) lastError.value = 'Algunos datos no se pudieron guardar. Revisá los campos marcados.'
      return { ok: false }
    }
    await fetchMe({ force: true }).catch(() => {})
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
    // El estado local se limpia ANTES del request: mientras el POST viaja,
    // ningún guard de navegación debe seguir viendo la sesión como activa
    // (si no, el push a /login rebota al usuario de vuelta al panel).
    accessToken.value = null
    user.value = null
    status.value = 'idle'
    lastError.value = ''
    fieldErrors.value = {}
    retryAfter.value = 0
    tokenStorage.clear()
    // Un reset que rompiera no debe frenar el cierre: si logoutSession no
    // corre, la cookie de refresh queda viva y la sesión reviviría sola.
    try { resetSessionStores() } catch { /* limpieza best-effort */ }
    await logoutSession() // blacklist del refresh + borra cookies en backend
  }

  function initSession() {
    window.addEventListener('davent:session-expired', () => {
      accessToken.value = null
      user.value = null
      const here = window.location.pathname
      if (!here.includes('/login')) window.location.assign('/login?expired=1')
    })
    // Refresh 429 persistente: throttle, no sesión muerta. La cookie puede
    // seguir viva — aviso visible en /login en vez de redirect silencioso.
    window.addEventListener('davent:session-throttled', () => {
      lastError.value = 'No pudimos renovar tu sesión. Reintentá en unos segundos.'
      const here = window.location.pathname
      if (!here.includes('/login')) window.location.assign('/login?throttled=1')
    })
    // Recupera la sesión desde la cookie si el tab se recargó.
    ensureSession().then((ok) => { if (ok) fetchMe().catch(() => {}) })
  }

  return {
    accessToken, user, status, lastError, fieldErrors,
    isAuthenticated, usingApiFallback, retryAfter,
    login, socialLogin, register, fetchMe, updateAccount, updatePassword, logout, initSession, ensureSession,
    http
  }
})
