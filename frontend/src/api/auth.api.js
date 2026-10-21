import { http } from './http.js'

// Contrato backend (ver ARCHITECTURE.md + users/viewset_config.py):
// POST /api/token/            {username, password} -> {access, refresh}
// POST /api/token/refresh/    {refresh}           -> {access}
// POST /api/token/verify/     {token}             -> 200
// POST /api/register/         RegisterUserSerializer -> 201 {Exito}
// GET  /api/user/me/ + /api/profile/me/           (requiere Bearer, retrieve propio)
// PUT  /api/user/me/          {email}             (UserUpdateSerializer, parcial ok)
// PUT  /api/profile/me/       UserProfileSerializer — el validate() del backend exige
//                             el set completo (tax_condition, document, province, city…)
// POST /api/password_update/  {old_password, new_password, confirm_password}

export const authApi = {
  async login({ username, password }) {
    const { data } = await http.post('/token/', { username, password })
    return data
  },

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

  // --- Recuperación: SIN backend (DaventProject no tiene endpoints) ---
  // Se dejan cableadas para cuando exista POST /password-reset/ y /password-reset/confirm/.
  // Hoy lanzan PENDING_BACKEND y las vistas muestran modo informativo (FRONTEND_RULES §3.6).
  async requestPasswordReset(_email) {
    const err = new Error(
      'La recuperación por email aún no está habilitada en la API. ' +
        'Cuando el backend exponga POST /api/password-reset/, este formulario se activará automáticamente.'
    )
    err.code = 'PENDING_BACKEND'
    throw err
  },

  async confirmPasswordReset(_payload) {
    const err = new Error(
      'El reseteo con token aún no está habilitado en la API. ' +
        'Cuando el backend exponga POST /api/password-reset/confirm/, este formulario se activará.'
    )
    err.code = 'PENDING_BACKEND'
    throw err
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
