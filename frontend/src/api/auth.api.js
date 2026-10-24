import { http } from './http.js'

// Contrato backend (ver ARCHITECTURE.md + users/viewset_config.py):
// POST /api/token/            {username, password} -> {access} (+cookie refresh httpOnly)
// POST /api/token/refresh/    {} (cookie)          -> {access} — lo llama http.js, no las vistas
// POST /api/token/logout/     {} (cookie + CSRF)   -> 200 — lo llama http.js (logoutSession)
// POST /api/token/verify/     {token}              -> 200
// POST /api/register/         RegisterUserSerializer -> 201 {Exito}
// GET  /api/user/me/ + /api/profile/me/           (requiere Bearer, retrieve propio)
// PUT  /api/user/me/          {email}             (UserUpdateSerializer, parcial ok)
// PUT  /api/profile/me/       UserProfileSerializer — el validate() del backend exige
//                             el set completo (tax_condition, document, province, city…)
// POST /api/password_update/  {old_password, new_password, confirm_password}
// POST /api/password-reset/   {email} -> 200 genérico (anti-enumeración)
// POST /api/password-reset/confirm/ {uid, token, new_password, confirm_password}
// GET  /api/verify-email/     ?uid&token -> backend marca y redirige al frontend
// POST /api/verify-email/resend/ (Bearer) -> 200

export const authApi = {
  async login({ username, password, remember = false }) {
    // remember=true -> refresh de 30 días + cookie persistente ("mantener
    // sesión iniciada"); false -> cookie de sesión del navegador.
    const { data } = await http.post('/token/', { username, password, remember })
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
    // Combinamos cuenta + perfil comercial para el dashboard.
    const out = {}
    let ok = false
    try {
      const { data } = await http.get('/user/me/')
      Object.assign(out, data?.results ? data.results[0] : data)
      ok = true
    } catch (e) {
      if (![404, 403].includes(e.response?.status)) throw e
    }
    try {
      const { data } = await http.get('/profile/me/')
      out.profile = data
      ok = true
    } catch (e) {
      if (![404, 403].includes(e.response?.status)) throw e
    }
    if (!ok) {
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

  // --- Verificación de celular por WhatsApp (gratis: service messages) ---
  // POST /api/verify-phone/ -> {code, whatsapp_url, expires_in}: el usuario
  // abre el link, le manda el código al número business y el webhook marca.
  async startPhoneVerification() {
    const { data } = await http.post('/verify-phone/')
    return data
  },

  // GET /api/verify-phone/status/ -> {phone_verified} (polling mientras espera)
  async fetchPhoneStatus() {
    const { data } = await http.get('/verify-phone/status/')
    return data
  }
}

// Arma el payload exacto de RegisterUserSerializer.
// type_document es read_only en backend y se deriva de tax_condition (operations.py).
export function buildRegisterPayload(form) {
  const tax = (form.tax_condition || 'CF').toUpperCase()
  return {
    username: form.username?.trim(),
    email: form.email?.trim(),
    password: form.password,
    confirm_password: form.confirm_password,
    first_name: form.first_name?.trim(),
    last_name: form.last_name?.trim(),
    tax_condition: tax,
    business_name: form.business_name?.trim() || null,
    type_document: tax === 'CF' ? 'DNI' : 'CUIT',
    document: form.document?.trim(),
    province: Number(form.province),
    city: Number(form.city),
    address: form.address?.trim() || null,
    phone: form.phone?.trim() || null,
    accept_terms: form.accept_terms === true
  }
}
