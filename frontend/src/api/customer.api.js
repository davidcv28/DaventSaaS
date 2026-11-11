import { customerHttp, customerCsrfToken } from './customer.http.js'

// =============================================================================
// Cuenta del COMPRADOR (dominio customers — NO es la sesión DAVENT).
// Auth: Bearer access en memoria + refresh en cookie httpOnly
// `customer_refresh` con doble-submit `customer_csrf` (ver customer.http.js).
//
// POST /api/customer-auth/register/   {email,password,first_name?,last_name?,store_slug?}
// POST /api/customer-auth/login/      {email,password,store_slug?} → {access, customer}
// POST /api/customer-auth/logout/     → limpia cookies (csrf via header)
// GET  /api/customer-auth/me/         → {customer}
// PATCH/api/customer-auth/me/         → perfil whitelisted
// POST /api/customer-auth/verify-email/           {token}
// POST /api/customer-auth/verify-email/resend/    → reenvía (sesión)
// POST /api/customer-auth/password-reset/         {email} → respuesta genérica
// POST /api/customer-auth/password-reset/confirm/ {uid,token,new_password,confirm_password}
// GET  /api/customer-auth/google-config/<slug>/   → {client_id, enabled} (público)
// POST /api/customer-auth/google/                 {credential, store_slug} → {access, customer}
// GET|PATCH /api/customer/profile/                → perfil editable
// GET|POST /api/customer/addresses/               → {id,label,line1,line2,city,province,postal_code,country,is_default}
// PATCH|DELETE /api/customer/addresses/<id>/
// GET  /api/customer/memberships/                 → [{store_slug,store_name,status,tags,joined_at}]
// =============================================================================

const auth = '/customer-auth'
const me = `${auth}/me`

export const customerApi = {
  // ---- auth ----
  register: (payload) => customerHttp.post(`${auth}/register/`, payload).then((r) => r.data),
  login: (payload) => customerHttp.post(`${auth}/login/`, payload).then((r) => r.data),
  // Logout consume la cookie customer_refresh → exige doble-submit CSRF.
  logout: () => customerHttp.post(`${auth}/logout/`, {}, { headers: { 'X-CSRFToken': customerCsrfToken() } }).then((r) => r.data),
  fetchMe: () => customerHttp.get(me).then((r) => r.data?.customer || null),
  updateMe: (payload) => customerHttp.patch(me, payload).then((r) => r.data?.customer || null),
  verifyEmail: (token) => customerHttp.post(`${auth}/verify-email/`, { token }).then((r) => r.data),
  resendVerification: () => customerHttp.post(`${auth}/verify-email/resend/`).then((r) => r.data),
  // store_slug opcional: el link del mail cae en la web de ESA tienda.
  requestPasswordReset: (email, store_slug) => customerHttp.post(`${auth}/password-reset/`, { email, ...(store_slug ? { store_slug } : {}) }).then((r) => r.data),
  confirmPasswordReset: (payload) => customerHttp.post(`${auth}/password-reset/confirm/`, payload).then((r) => r.data),
  // Google login del comprador: `credential` = el id_token de Google
  // Identity Services; store_slug = la tienda donde se está comprando.
  googleLogin: (payload) => customerHttp.post(`${auth}/google/`, payload).then((r) => r.data),
  // ---- perfil ----
  getProfile: () => customerHttp.get('/customer/profile/').then((r) => r.data),
  updateProfile: (payload) => customerHttp.patch('/customer/profile/', payload).then((r) => r.data),
  // ---- direcciones ----
  listAddresses: () => customerHttp.get('/customer/addresses/').then((r) => r.data),
  createAddress: (payload) => customerHttp.post('/customer/addresses/', payload).then((r) => r.data),
  updateAddress: (id, payload) => customerHttp.patch(`/customer/addresses/${id}/`, payload).then((r) => r.data),
  deleteAddress: (id) => customerHttp.delete(`/customer/addresses/${id}/`).then((r) => r.data),
  // ---- membresías del comprador en tiendas ----
  listMemberships: () => customerHttp.get('/customer/memberships/').then((r) => r.data),
}

// Config pública de Google Auth por tienda (sin sesión — el client_id
// BYO del dueño o el central). Usa http de DAVENT? NO: es endpoint
// customer-auth → customerHttp sin token (el interceptor no agrega
// Authorization si no hay access; la llamada es anónima igual).
export const customerPublicApi = {
  googleConfig: (storeSlug) => customerHttp.get(`${auth}/google-config/${storeSlug}/`).then((r) => r.data),
}
