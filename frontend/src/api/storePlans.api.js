import { http } from './http.js'

// =============================================================================
// Membresías de tienda del DUEÑO (dominio memberships) — planes que el dueño
// vende a SUS clientes (NO los planes DAVENT del dueño) + suscripciones.
//
// CRUD de planes (router DRF, list NO paginado — array plano):
// GET    /api/store-plans/                 → [plan] con counts anotados
// POST   /api/store-plans/                 {name,price,period,period_days?,
//        has_digital_card,has_free_shipping,has_exclusive_discounts,
//        discount_percent,has_exclusive_access,is_active,position}
//        → 201 {Exito, item}   (period: monthly|yearly|custom; monthly/yearly
//        fijan period_days server-side 30/365 — solo 'custom' usa el cargado)
// PUT    /api/store-plans/<id>/            → {Exito, item} (merge parcial ok)
// PATCH  /api/store-plans/<id/             → idem
// DELETE /api/store-plans/<id>/            → {Exito} borra, o {Exito,item}
//        desactivado si tiene suscripciones (conserva historial)
//
// Suscripciones de SUS clientes (list NO paginado — array plano;
// ?status= pending|active|past_due|cancelled|expired):
// GET    /api/store-subscriptions/         → [{id,status,plan:{…},
//        payment_method,payment_ref,public_token,started_at,vigente_hasta,
//        is_vigente,benefits[],customer_email,customer_first_name,
//        customer_last_name,created_at,updated_at}]
// POST   /api/store-subscriptions/<id>/activate/ → pending/expired/cancelled/
//        past_due → active + período del plan (idempotente)
// POST   /api/store-subscriptions/<id>/cancel/   → corta beneficios al instante
// POST   /api/store-subscriptions/<id>/expire/   → fuerza 'expired' (active/
//        past_due)
// =============================================================================

export const storePlansApi = {
  list: () => http.get('/store-plans/').then((r) => r.data),
  create: (payload) => http.post('/store-plans/', payload).then((r) => r.data),
  update: (id, payload) => http.patch(`/store-plans/${id}/`, payload).then((r) => r.data),
  remove: (id) => http.delete(`/store-plans/${id}/`).then((r) => r.data),

  subscriptions: ({ status } = {}) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return http.get(`/store-subscriptions/${qs}`).then((r) => r.data)
  },
  activateSubscription: (id) => http.post(`/store-subscriptions/${id}/activate/`).then((r) => r.data),
  cancelSubscription: (id) => http.post(`/store-subscriptions/${id}/cancel/`).then((r) => r.data),
  expireSubscription: (id) => http.post(`/store-subscriptions/${id}/expire/`).then((r) => r.data),
}
