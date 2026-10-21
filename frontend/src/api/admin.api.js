import { http } from './http.js'

// Panel de administración (todos los endpoints requieren usuario staff):
// GET  /api/payments/admin-summary/      Bearer admin -> KPIs + revenue_by_day/month + by_plan
// GET  /api/payments/                    Bearer staff -> TODOS los pagos (paginado, PAGE_SIZE=10)
// GET  /api/suscriptions/                Bearer staff -> TODAS las suscripciones (paginado)
// POST /api/payments/<id>/approve/       Bearer admin -> sella status=approved + paid_at y acredita el plan
// GET  /api/daily-revenues/              Bearer admin -> rollups materializados por día
// GET  /api/monthly-revenues/            Bearer admin -> rollups materializados por mes
// POST /api/suscription-plans/           Bearer admin {name, price} -> crear plan
// PUT  /api/suscription-plans/<id>/      Bearer admin {name, price} -> actualizar plan
// GET  /api/user/                        Bearer admin -> listado de usuarios [{id, username, email, is_staff}]

// DRF pagina con PageNumberPagination (PAGE_SIZE=10). Recorremos todas las
// páginas con ?page=N hasta que `next` sea null (tope de seguridad en 50).
async function fetchAllPages(path) {
  const out = []
  for (let page = 1; page <= 50; page++) {
    const { data } = await http.get(path, { params: { page } })
    if (Array.isArray(data)) return out.concat(data)
    out.push(...(data?.results || []))
    if (!data?.next) break
  }
  return out
}

export const adminApi = {
  async summary() {
    const { data } = await http.get('/payments/admin-summary/')
    return data
  },

  async listAllPayments() {
    return fetchAllPages('/payments/')
  },

  async listAllSuscriptions() {
    return fetchAllPages('/suscriptions/')
  },

  async approvePayment(id) {
    const { data } = await http.post(`/payments/${id}/approve/`)
    return data
  },

  async listPlans() {
    return fetchAllPages('/suscription-plans/')
  },

  async createPlan({ name, price }) {
    const { data } = await http.post('/suscription-plans/', { name: name.trim(), price: Number(price) })
    return data
  },

  async updatePlan(id, { name, price }) {
    const { data } = await http.put(`/suscription-plans/${id}/`, { name: name.trim(), price: Number(price) })
    return data
  },

  async listUsers() {
    return fetchAllPages('/user/')
  }
}
