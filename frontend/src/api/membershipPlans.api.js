import { customerHttp } from './customer.http.js'
import { publicHttp } from './http.js'

// =============================================================================
// Planes de suscripción de la tienda (dominio memberships).
//
// PÚBLICO (sin login — página "Suscripciones" y checkout de planes):
// GET /api/stores/public/<slug>/membership-plans/
//   → {store:{slug,name}, plans:[{id,name,price,period,period_days,
//      duration_days,discount_percent,benefits[]}],
//      payments:{accept_transfer,transfer_alias,transfer_holder,
//      transfer_instructions,accept_whatsapp,whatsapp_number,accept_cash,
//      mp_enabled,mp_connected,deadline_hours}}
//
// COMPRADOR (customer JWT — Bearer en memoria + refresh cookie):
// GET  /api/customer/subscriptions/<slug>/   → {store, plans, subscription, benefits}
// POST /api/customer/subscriptions/<slug>/   {plan_id, payment_method?} → 201
//      {subscription, payment} | 409 {detail, subscription} si ya tiene una
// GET  /api/customer/subscriptions/          → historial (paginado → results)
// GET  /api/customer/subscriptions/<slug>/card/ → tarjeta digital (403/404 si no)
// GET  /api/membership-cards/<slug>/<token>/ → tarjeta pública por token (sin auth)
// =============================================================================

export const membershipPlansApi = {
  publicPlans: (slug) => publicHttp.get(`/stores/public/${slug}/membership-plans/`).then((r) => r.data),
  storePlans: (slug) => customerHttp.get(`/customer/subscriptions/${slug}/`).then((r) => r.data),
  subscribe: (slug, payload) => customerHttp.post(`/customer/subscriptions/${slug}/`, payload).then((r) => r.data),
  listSubscriptions: () => customerHttp.get('/customer/subscriptions/').then((r) => {
    const data = r.data
    // ListAPIView paginado del proyecto: {count, results} — tolerante a lista plana.
    return Array.isArray(data) ? data : (data?.results || [])
  }),
  subscriptionCard: (slug) => customerHttp.get(`/customer/subscriptions/${slug}/card/`).then((r) => r.data),
}

export const membershipCardApi = {
  publicCard: (slug, token) => publicHttp.get(`/membership-cards/${slug}/${token}/`).then((r) => r.data),
}
