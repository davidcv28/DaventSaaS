import { http } from './http.js'

// =============================================================================
// Panel "Cobros" del DUEÑO (dominio storepayments) — config de métodos
// manuales, datos fiscales, login social Google, storage R2 propio y la
// cuenta de Mercado Pago DEL VENDEDOR.
//
// REGLA DE SECRETOS: los tokens MP, el client_secret de Google y las llaves
// R2 son WRITE-ONLY — viajan cifrados al backend y JAMÁS vuelven. Los GET
// solo informan flags (has_client_secret, has_credentials, is_configured,
// webhook_configured). Nunca mostrar ni precargar valores secretos.
//
// GET|PATCH /api/store-payments/config/        → métodos manuales
//   {accept_transfer,accept_whatsapp,accept_cash,mp_enabled,transfer_alias,
//    transfer_holder,transfer_instructions,whatsapp_number,
//    require_payment_proof,payment_deadline_hours}
// GET|PUT   /api/store-payments/fiscal-profile/ → {legal_name,tax_condition
//   (CF|MO|RI|EX),cuit,fiscal_address,point_of_sale,is_complete,updated_at}
// GET|PUT   /api/store-payments/oauth-config/   → {enabled,google_client_id,
//   has_client_secret,has_own_client,updated_at} (+ google_client_secret
//   write-only en el PUT — ausente conserva, '' limpia)
// GET|PUT|DELETE /api/store-payments/storage-config/ → {endpoint,bucket,
//   region,public_base_url,enabled,is_configured,has_credentials,url_mode,
//   updated_at} (+ access_key/secret_key write-only; DELETE deshabilita y
//   limpia secretos conservando lo no secreto)
// GET  /api/store-payments/storage-config/guide/ → {title,intro,steps[],warnings[]}
// GET  /api/store-payments/mp/status/          → {connected,live_mode,
//   mp_user_id,connected_at,has_payment_config,webhook_configured}
// POST /api/store-payments/mp/connect/         {access_token,refresh_token?,
//   live_mode?,webhook_secret?} → valida el token contra MP y devuelve el
//   mismo payload de status (NO hay OAuth/redirect: son credenciales
//   pegadas del vendedor — ver views/mp.py).
// POST /api/store-payments/mp/disconnect/      → limpia tokens (no revoca en MP)
// POST /api/store-payments/mp/refund/<order_id>/ → reembolso total en MP del
//   pedido (solo si status=PAID y payment_method=mp; luego marca REFUNDED).
// =============================================================================

export const storePaymentsApi = {
  // ----- Métodos manuales de cobro -----
  getConfig: () => http.get('/store-payments/config/').then((r) => r.data),
  updateConfig: (payload) => http.patch('/store-payments/config/', payload).then((r) => r.data),

  // ----- Datos fiscales (gate de orders_enabled junto a ecommerce_enabled) -----
  getFiscalProfile: () => http.get('/store-payments/fiscal-profile/').then((r) => r.data),
  updateFiscalProfile: (payload) => http.put('/store-payments/fiscal-profile/', payload).then((r) => r.data),

  // ----- Login con Google del checkout (BYO del dueño) -----
  getOAuthConfig: () => http.get('/store-payments/oauth-config/').then((r) => r.data),
  updateOAuthConfig: (payload) => http.put('/store-payments/oauth-config/', payload).then((r) => r.data),

  // ----- Storage R2 propio (BYO) -----
  getStorageConfig: () => http.get('/store-payments/storage-config/').then((r) => r.data),
  updateStorageConfig: (payload) => http.put('/store-payments/storage-config/', payload).then((r) => r.data),
  deleteStorageConfig: () => http.delete('/store-payments/storage-config/').then((r) => r.data),
  storageGuide: () => http.get('/store-payments/storage-config/guide/').then((r) => r.data),

  // ----- Mercado Pago del vendedor -----
  mpStatus: () => http.get('/store-payments/mp/status/').then((r) => r.data),
  mpConnect: (payload) => http.post('/store-payments/mp/connect/', payload).then((r) => r.data),
  mpDisconnect: () => http.post('/store-payments/mp/disconnect/').then((r) => r.data),
  mpRefund: (orderId) => http.post(`/store-payments/mp/refund/${orderId}/`).then((r) => r.data),
}
