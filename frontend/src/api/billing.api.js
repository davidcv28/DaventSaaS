import { http } from './http.js'

// Dominio planes (SuscriptionApp/benefits):
// GET  /api/plans/             público  -> tarjetas completas:
//   [{id, name, price, is_trial, slug, tagline, cta_label, bullets, featured, display_order,
//     benefits: {max_catalogs, has_public_link, has_qr, max_products(null=ilimitado),
//                max_storage_mb, has_stats, has_flyers, has_customization,
//                has_design_advanced, has_advanced_menu}}]
//   is_trial=true -> plan de prueba (1 día, solo se otorga en el registro):
//   viaja en el catálogo para la tarjeta informativa y los beneficios del plan
//   vigente, pero no es seleccionable (el backend también lo rechaza).
// Dominio suscripciones (AdminApp):
// GET  /api/suscriptions/      Bearer   -> mi suscripción (lista con 0..1)
// POST /api/suscriptions/      Bearer {plan_suscription: <pk>} -> 201
// PUT  /api/suscriptions/<pk>/ Bearer {plan_suscription: <pk>} -> 200
// POST /api/suscriptions/redeem-coupon/ Bearer {code} -> 200 (cupón promocional)

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const billingApi = {
  async listPlans() {
    const { data } = await http.get('/plans/')
    return unwrap(data)
  },

  async listMine() {
    const { data } = await http.get('/suscriptions/')
    return unwrap(data)
  },

  async subscribe(planPk) {
    const { data } = await http.post('/suscriptions/', { plan_suscription: planPk })
    return data
  },

  async changePlan(subscriptionPk, planPk) {
    const { data } = await http.put(`/suscriptions/${subscriptionPk}/`, { plan_suscription: planPk })
    return data
  },

  async redeemCoupon(code) {
    const { data } = await http.post('/suscriptions/redeem-coupon/', { code })
    return data
  }
}

export function formatARS(value, digits = 0) {
  const n = Number(value ?? 0)
  if (n === 0) return 'Gratis'
  return new Intl.NumberFormat('es-AR', {
    style: 'currency', currency: 'ARS',
    minimumFractionDigits: digits, maximumFractionDigits: digits
  }).format(n)
}

export function daysLeft(endDate) {
  if (!endDate) return null
  const diff = new Date(endDate).getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / 86400000))
}
