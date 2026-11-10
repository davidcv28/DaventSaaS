import { customerHttp } from './customer.http.js'
import { http, publicHttp } from './http.js'

// =============================================================================
// Pedidos de tienda (dominio orders + storepayments MP).
//
// PÚBLICOS (tracking_token = credencial anti-IDOR, sin login):
// GET  /api/stores/public/<slug>/orders/captcha/                    → challenge
// POST /api/stores/public/<slug>/orders/                            → crear (customer JWT + captcha)
// GET  /api/stores/public/<slug>/orders/<token>/                    → seguimiento
// GET  /api/stores/public/<slug>/orders/<token>/events/             → timeline (polling)
// GET  /api/stores/public/<slug>/orders/<token>/receipt/            → datos comprobante NO FISCAL
// POST /api/stores/public/<slug>/orders/<token>/proof/              → multipart comprobante (manual)
// POST /api/stores/public/<slug>/orders/<token>/pay/                → preferencia MP → {checkout_url,...}
//
// COMPRADOR (customer JWT):
// GET  /api/customer/orders/                  → pedidos propios (store?, status?)
// GET  /api/customer/orders/<token>/          → detalle propio (404 si ajeno)
//
// DUEÑO (DAVENT JWT, store-scoped):
// GET  /api/store-orders/?status=&page=       → bandeja
// GET  /api/store-orders/<id>/                → detalle
// POST /api/store-orders/<id>/confirm-payment/ {reference?}
// POST /api/store-orders/<id>/advance/        {status: PACKING|SHIPPED|DELIVERED|REFUNDED}
// POST /api/store-orders/<id>/cancel/         {reason?}
// POST /api/store-orders/<id>/invoice-ref/    {invoice_ref}
// =============================================================================

const pub = (slug) => `/stores/public/${slug}/orders`

export const orderPublicApi = {
  // Crear pedido: body = {items?|use_cart?, address_id?|address?,
  // shipping_method, payment_method, idempotency_key, challenge_id,
  // captcha_answer, website?} — el front genera idempotency_key por
  // intento de checkout (crypto.randomUUID) para que un retry no duplique.
  create: (slug, payload) => customerHttp.post(`${pub(slug)}/`, payload).then((r) => r.data),
  track: (slug, token) => publicHttp.get(`${pub(slug)}/${token}/`).then((r) => r.data),
  events: (slug, token) => publicHttp.get(`${pub(slug)}/${token}/events/`).then((r) => r.data),
  receipt: (slug, token) => publicHttp.get(`${pub(slug)}/${token}/receipt/`).then((r) => r.data),
  // Comprobante: multipart {image: File} — solo métodos manuales y
  // pedido PENDING_PAYMENT.
  uploadProof: (slug, token, file) => {
    const form = new FormData()
    form.append('image', file)
    return publicHttp.post(`${pub(slug)}/${token}/proof/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
  // Inicia el pago MP del pedido → {init_point, sandbox_init_point,
  // preference_id, checkout_url} — el front redirige a checkout_url.
  payMp: (slug, token) => publicHttp.post(`${pub(slug)}/${token}/pay/`).then((r) => r.data),
}

export const customerOrdersApi = {
  list: ({ store, status, page } = {}) => {
    const params = new URLSearchParams()
    if (store) params.set('store', store)
    if (status) params.set('status', status)
    if (page) params.set('page', page)
    const qs = params.toString()
    return customerHttp.get(`/customer/orders/${qs ? `?${qs}` : ''}`).then((r) => r.data)
  },
  detail: (token) => customerHttp.get(`/customer/orders/${token}/`).then((r) => r.data),
}

export const ownerOrdersApi = {
  list: ({ status, page } = {}) => {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (page) params.set('page', page)
    const qs = params.toString()
    return http.get(`/store-orders/${qs ? `?${qs}` : ''}`).then((r) => r.data)
  },
  detail: (id) => http.get(`/store-orders/${id}/`).then((r) => r.data),
  confirmPayment: (id, reference = '') => http.post(`/store-orders/${id}/confirm-payment/`, { reference }).then((r) => r.data),
  advance: (id, status) => http.post(`/store-orders/${id}/advance/`, { status }).then((r) => r.data),
  cancel: (id, reason = '') => http.post(`/store-orders/${id}/cancel/`, { reason }).then((r) => r.data),
  setInvoiceRef: (id, invoiceRef) => http.post(`/store-orders/${id}/invoice-ref/`, { invoice_ref: invoiceRef }).then((r) => r.data),
}
