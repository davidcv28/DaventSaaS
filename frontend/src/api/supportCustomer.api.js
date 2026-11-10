import { customerHttp } from './customer.http.js'

// =============================================================================
// Soporte del COMPRADOR (customer JWT — request.customer, nunca el JWT DAVENT).
// Hilos de consulta comprador ↔ dueño de tienda.
//
// GET  /api/support/threads/               → bandeja paginada (results)
// POST /api/support/threads/               {store: <slug>, subject, body, order_token?}
// GET  /api/support/threads/<id>/          → detalle + messages (leer marca leídos)
// POST /api/support/threads/<id>/messages/ {body} → responder (hilo cerrado → 400)
// POST /api/support/threads/<id>/close/    → cerrar (solo el comprador cierra)
//
// IDOR: todo hilo ajeno es 404. Throttles server-side en los writes.
// =============================================================================

export const supportCustomerApi = {
  list: ({ store, page } = {}) => {
    const params = new URLSearchParams()
    if (page) params.set('page', page)
    const qs = params.toString()
    return customerHttp.get(`/support/threads/${qs ? `?${qs}` : ''}`).then((r) => {
      const data = r.data
      const rows = Array.isArray(data) ? data : (data?.results || [])
      // La lista mezcla tiendas: el filtro por slug es del lado cliente
      // (el endpoint no acepta `store` como query param).
      return store ? rows.filter((t) => t?.store?.slug === store) : rows
    })
  },
  create: (payload) => customerHttp.post('/support/threads/', payload).then((r) => r.data),
  detail: (id) => customerHttp.get(`/support/threads/${id}/`).then((r) => r.data),
  reply: (id, body) => customerHttp.post(`/support/threads/${id}/messages/`, { body }).then((r) => r.data),
  close: (id) => customerHttp.post(`/support/threads/${id}/close/`).then((r) => r.data),
}
