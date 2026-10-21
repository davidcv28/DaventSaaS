import { http } from './http.js'

// Dominio payments:
// GET  /api/payments/            Bearer -> mis pagos [{id, suscription, plan_name, amount, currency, status, status_display, external_reference, paid_at, created_at}]
// POST /api/payments/            Bearer {suscription: <pk>, payment_id: <int>} -> 201 {Exito} (verifica el pago contra Mercado Pago)
// POST /api/payments/sync/       Bearer -> registra pagos acreditados en MP que aún no estén en el sistema
// GET  /api/daily-revenues/      Bearer admin -> rollups diarios [{id, date, total_amount, payments_count}]
// GET  /api/monthly-revenues/    Bearer admin -> rollups mensuales [{id, year, month, total_amount, payments_count}]
// El webhook /payments/webhook/ y POST /payments/<id>/approve/ son del backend/admin, no se consumen desde la UI.

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const paymentsApi = {
  async listPayments() {
    const { data } = await http.get('/payments/')
    return unwrap(data)
  },

  async confirmPayment({ suscription, paymentId }) {
    const { data } = await http.post('/payments/', {
      suscription,
      payment_id: Number(paymentId)
    })
    return data
  },

  // POST /payments/checkout/ {suscription?, plan_suscription} -> {checkout_url, init_point, sandbox_init_point, preference_id}
  // El plan elegido queda pendiente en backend; la suscripción se establece cuando el pago se acredita.
  async createCheckout({ suscription, planPk }) {
    const { data } = await http.post('/payments/checkout/', { suscription, plan_suscription: planPk })
    return data
  },

  // POST /payments/subscription/ {suscription?, plan_suscription} -> débito automático MP (preapproval):
  // {status, auto_renew?, checkout_url, init_point, sandbox_init_point, preapproval_id}
  // Si ya está autorizado (auto_renew) no hay redirect: el plan pendiente se aplica en el próximo débito.
  async createSubscription({ suscription, planPk }) {
    const { data } = await http.post('/payments/subscription/', { suscription, plan_suscription: planPk })
    return data
  },

  // POST /payments/cancel-renewal/ -> baja del débito automático. El acceso sigue hasta end_date.
  async cancelRenewal() {
    const { data } = await http.post('/payments/cancel-renewal/')
    return data
  },

  // POST /payments/sync/ {payment_id?} -> {Exito, synced} — red de seguridad cuando el redirect de MP no vuelve.
  // Con payment_id se verifica ese pago directo en MP (acreditación instantánea).
  async syncPayments(paymentId = null) {
    const { data } = await http.post('/payments/sync/', paymentId ? { payment_id: Number(paymentId) } : {})
    return data
  },

  async listDailyRevenues() {
    const { data } = await http.get('/daily-revenues/')
    return unwrap(data)
  },

  async listMonthlyRevenues() {
    const { data } = await http.get('/monthly-revenues/')
    return unwrap(data)
  }
}

// Meta visual por estado (status llega en inglés; status_display ya viene traducido).
export function paymentStatusMeta(status) {
  const map = {
    approved: { kind: 'ok', label: 'Aprobado' },
    pending: { kind: 'warn', label: 'Pendiente' },
    rejected: { kind: 'danger', label: 'Rechazado' },
    refunded: { kind: 'muted', label: 'Reembolsado' }
  }
  return map[status] || { kind: 'muted', label: status || '—' }
}

export function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

export const MONTH_NAMES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
