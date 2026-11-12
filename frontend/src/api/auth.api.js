import { http, persistNativeLogin } from './http.js'

// Contrato backend (ver ARCHITECTURE.md + users/viewset_config.py):
// POST /api/token/            {username, password} -> {access} (+cookie refresh httpOnly)
// POST /api/token/refresh/    {} (cookie)          -> {access} — lo llama http.js, no las vistas
// POST /api/token/logout/     {} (cookie + CSRF)   -> 200 — lo llama http.js (logoutSession)
// POST /api/token/verify/     {token}              -> 200
// POST /api/register/         RegisterUserSerializer -> 201 {Exito} — alta minimal:
//                             solo cuenta + celular + TyC; los datos fiscales se
//                             completan recién al pagar (gate billing_required).
// GET  /api/user/me/ + /api/profile/me/           (requiere Bearer, retrieve propio)
// PUT  /api/user/me/          {email}             (UserUpdateSerializer, parcial ok)
// PUT  /api/profile/me/       UserProfileSerializer — PATCH parcial: los datos
//                             fiscales son opcionales hasta el primer pago.
// POST /api/password_update/  {old_password, new_password, confirm_password}
// POST /api/password-reset/   {email} -> 200 genérico (anti-enumeración)
// POST /api/password-reset/confirm/ {uid, token, new_password, confirm_password}
// GET  /api/verify-email/     ?uid&token -> backend marca y redirige al frontend
// POST /api/verify-email/resend/ (Bearer) -> 200

// Diagnóstico APK: dentro del WebView de Capacitor una request a /api/* que no
// sale a la red puede devolver el index.html del servidor local de assets
// (sin server.url el WebView intercepta el hostname). Se distingue ese caso de
// un 5xx real y se muestran URL efectiva y Content-Type — nunca el HTML crudo.
// Y un timeout propio cubre el caso en que la capa nativa (CapacitorHttp)
// ignora el timeout de axios.
function expectJson(res, op) {
  const data = res?.data
  if (!data || typeof data !== 'object') {
    const contentType = String(res?.headers?.['content-type'] || 'desconocido')
    const url = res?.config ? `${res.config.baseURL || ''}${res.config.url || ''}` : 'desconocida'
    const isHtml = contentType.includes('text/html') || (typeof data === 'string' && /<(!doctype|html)[\s>]/i.test(data))
    const detail = isHtml
      ? `Diagnóstico: respuesta HTML del servidor local de la app en vez de JSON (${op}). URL: ${url} · Content-Type: ${contentType}. Reportá este mensaje.`
      : `Diagnóstico: el servidor devolvió una respuesta no-JSON (${op}). URL: ${url} · Content-Type: ${contentType}. Reportá este mensaje.`
    const err = new Error('non-json response')
    err.response = { status: res?.status || 500, data: { detail } }
    throw err
  }
  return data
}

function withDiag(promise, op, ms = 45000) {
  const timeout = new Promise((_, reject) => setTimeout(() => {
    const err = new Error('diag timeout')
    err.response = { status: 408, data: { detail: `Diagnóstico: el servidor no respondió en 45s (${op}). Reportá este mensaje.` } }
    reject(err)
  }, ms))
  return Promise.race([promise, timeout])
}

export const authApi = {
  async login({ username, password, remember = false }) {
    // remember=true -> refresh de 30 días + cookie persistente ("mantener
    // sesión iniciada"); false -> cookie de sesión del navegador.
    const data = expectJson(await withDiag(http.post('/token/', { username, password, remember }), 'token'), 'token')
    persistNativeLogin(data)
    return data
  },

  // El refresh real viaja por cookie y lo ejecuta http.js (tryRefresh);
  // este método queda para clientes API con refresh explícito en body.
  async refresh(refresh) {
    const { data } = await http.post('/token/refresh/', { refresh })
    return data
  },

  async verify(token) {
    const { data } = await http.post('/token/verify/', { token })
    return data
  },

  async register(payload) {
    // DRF router `register` -> POST /register/ (con o sin trailing slash según APPEND_SLASH).
    // Probamos con slash (canónico DRF) y hacemos fallback sin slash.
    try {
      const { data } = await http.post('/register/', payload)
      return data
    } catch (e) {
      if (e.response?.status === 404) {
        const { data } = await http.post('/register', payload)
        return data
      }
      throw e
    }
  },

  async fetchMe() {
    // Los retrieve de user/profile ignoran el pk y devuelven lo propio
    // (ver UserBaseViewSet.retrieve y UserProfileBaseVieSet.retrieve).
    // Combinamos cuenta + perfil comercial para el dashboard. Van en
    // paralelo: son independientes y eran el primer cuello de botella.
    const optional = async (path, assign) => {
      try {
        const { data } = await http.get(path)
        assign(data)
        return true
      } catch (e) {
        if (![404, 403].includes(e.response?.status)) throw e
        return false
      }
    }
    const out = {}
    const [userOk, profileOk] = await Promise.all([
      optional('/user/me/', (data) => Object.assign(out, data?.results ? data.results[0] : data)),
      optional('/profile/me/', (data) => { out.profile = data }),
    ])
    if (!userOk && !profileOk) {
      const err = new Error('Perfil no disponible')
      err.response = { status: 404, data: { detail: 'Perfil no disponible' } }
      throw err
    }
    return out
  },

  async updateUser(payload) {
    const { data } = await http.put('/user/me/', payload)
    return data
  },

  async updateProfile(payload) {
    const { data } = await http.put('/profile/me/', payload)
    return data
  },

  async updatePassword({ old_password, new_password, confirm_password }) {
    const { data } = await http.post('/password_update/', {
      old_password,
      new_password,
      confirm_password
    })
    return data
  },

  // --- Recuperación por correo (backend real desde users/auth_views.py) ---
  // La respuesta de /password-reset/ es siempre genérica: no revela si el
  // correo existe (anti-enumeración). El link llega como
  // {FRONTEND_URL}/reset-password?uid=...&token=...
  async requestPasswordReset(email) {
    const { data } = await http.post('/password-reset/', { email })
    return data
  },

  async confirmPasswordReset({ uid, token, new_password, confirm_password }) {
    const { data } = await http.post('/password-reset/confirm/', {
      uid,
      token,
      new_password,
      confirm_password
    })
    return data
  },

  // Reenvío del correo de verificación (usuario autenticado; throttled 5/hour).
  async resendVerificationEmail() {
    const { data } = await http.post('/verify-email/resend/')
    return data
  },

  // --- Login social (token exchange: el backend verifica contra el provider) ---
  // POST /api/auth/google/ {credential} -> {access, is_new, requires_phone} + cookies
  // El celular no viaja en los datos del provider: si falta, la respuesta trae
  // requires_phone y el router fuerza /completar-celular antes del panel.
  async googleLogin(credential, remember = true) {
    const data = expectJson(await withDiag(http.post('/auth/google/', { credential, remember }), 'google'), 'google')
    persistNativeLogin(data)
    return data
  }
}

// Arma el payload exacto de RegisterUserSerializer — alta minimal:
// cuenta + celular (ancla anti-abuso) + TyC. Los datos fiscales/de facturación
// (nombre, documento, condición fiscal, provincia/ciudad) se completan en el
// perfil recién cuando el usuario inicia un pago (billing_required).
export function buildRegisterPayload(form) {
  return {
    username: form.username?.trim(),
    email: form.email?.trim(),
    password: form.password,
    confirm_password: form.confirm_password,
    phone: form.phone?.trim() || null,
    accept_terms: form.accept_terms === true,
    //Cupón promocional opcional (QR/folletos): el backend lo canjea en el
    //alta y crea la suscripción con el plan del cupón por sus días.
    coupon: form.coupon?.trim() || ''
  }
}
