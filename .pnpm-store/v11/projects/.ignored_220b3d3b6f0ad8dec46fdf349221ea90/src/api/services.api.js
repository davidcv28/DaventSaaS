import { http } from './http.js'

// Dominio services (StoreApp): ítems de la página "Servicios" de la web del
// cliente. Todo cuelga de la tienda del usuario autenticado (scope
// server-side). Requiere el flag 'has_services_site' del plan vigente
// (Estándar en adelante): sin el beneficio todo el endpoint responde 403.
// La web pública recibe estos ítems dentro del payload de
// GET /api/stores/public/<slug>/ (campo service_items, solo activos y solo
// si la página está en los site_templates efectivos). La página nunca
// persiste pedidos/reservas/pagos: la selección del visitante viaja en un
// mensaje de WhatsApp que el frontend arma con el número del dueño.
//
// GET    /api/services/             Bearer -> [{id,name,description,price,duration,icon,is_active,position,created_at}]
// POST   /api/services/             Bearer {name,description?,price?,duration?,icon?,is_active?} -> {Exito,item}
// PATCH  /api/services/<pk>/        Bearer idem parcial -> {Exito,item}
// DELETE /api/services/<pk>/        Bearer -> {Exito}
// PATCH  /api/services/order/       Bearer {order:[ids]} -> {Exito} (reordena position;
//                                       los ids ajenos/desconocidos se ignoran)
//                                        -> 403 si el plan no incluye has_services_site
//                                        -> 403 si se supera el tope defensivo (SERVICES_MAX = 24)
// price = precio ORIENTATIVO, puede ser null -> la web lo rotula "a convenir"
//         y no lo suma al presupuesto. icon = clave del catálogo cerrado
//         SERVICE_ICONS (mismo que las secciones de la portada).

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const servicesApi = {
  async listServices() {
    const { data } = await http.get('/services/', { params: { page_size: 200 } })
    return unwrap(data)
  },
  async createService(payload) {
    const { data } = await http.post('/services/', payload)
    return data
  },
  async updateService(pk, payload) {
    const { data } = await http.patch(`/services/${pk}/`, payload)
    return data
  },
  async deleteService(pk) {
    const { data } = await http.delete(`/services/${pk}/`)
    return data
  },
  async saveOrder(order) {
    const { data } = await http.patch('/services/order/', { order })
    return data
  }
}

// ===== Espejo de config_fields.py / models.py del dominio services =====
export const SERVICE_LIMITS = {
  max: 24,          // SERVICES_MAX del servicio (tope defensivo, no es plan)
  name: 80,         // StoreService.NAME_MAX
  description: 160, // StoreService.DESCRIPTION_MAX
  duration: 40,     // StoreService.DURATION_MAX
  priceMax: 9999999999
}

// Duración/precio son opcionales: el ítem puede existir sin ambos
// ("a convenir"). Solo el nombre es obligatorio.
export function validateServiceName(value) {
  const v = String(value || '').trim()
  if (!v) return 'El servicio necesita un nombre'
  if (v.length < 2) return 'El nombre es demasiado corto'
  if (v.length > SERVICE_LIMITS.name) return `El nombre admite hasta ${SERVICE_LIMITS.name} caracteres`
  return ''
}

export function validateServiceDescription(value) {
  if (value && value.length > SERVICE_LIMITS.description) return `La descripción admite hasta ${SERVICE_LIMITS.description} caracteres`
  return ''
}

export function validateServicePrice(value) {
  if (value === '' || value === null || value === undefined) return ''
  const n = Number(value)
  if (Number.isNaN(n)) return 'Ingresá un precio válido'
  if (n < 0) return 'El precio no puede ser negativo'
  if (n > SERVICE_LIMITS.priceMax) return 'El precio es demasiado grande'
  return ''
}

export function validateServiceDuration(value) {
  if (value && value.length > SERVICE_LIMITS.duration) return `La duración admite hasta ${SERVICE_LIMITS.duration} caracteres`
  return ''
}

// Normaliza el form: precio '' -> null (a convenir), strings recortadas.
export function servicePayload(form) {
  const price = form.price === '' || form.price === null || form.price === undefined ? null : Number(form.price)
  return {
    name: String(form.name || '').trim(),
    description: String(form.description || '').trim(),
    price: Number.isNaN(price) ? null : price,
    duration: String(form.duration || '').trim(),
    icon: String(form.icon || '').trim() || 'wrench',
    is_active: Boolean(form.is_active ?? true)
  }
}

// ===== Config de la página (service_* de customization) =====
// Mismo espejo que el modelo StoreCustomization.
export const SERVICE_PAGE_LIMITS = { steps: 4, stepTitle: 60, stepText: 160, days: 7, day: 24, slots: 4, slot: 24, note: 160 }

// Texto de precio para la web pública: "$ 12.000" o "A convenir".
export function servicePriceLabel(item) {
  const n = Number(item?.price)
  return Number.isFinite(n) && item.price !== null ? `$ ${n.toLocaleString('es-AR')}` : 'A convenir'
}

// Arma el mensaje de WhatsApp del pedido (servicios elegidos + datos del
// visitante + total orientativo). Devuelve texto plano; el llamador lo
// mete en ?text= de wa.me. Nada se persiste en el backend.
export function buildServiceRequestMessage({ shopName, items, total, visitor }) {
  const lines = [`Hola ${shopName}, quiero pedir:`]
  items.forEach((it) => {
    const price = it.price != null ? ` — ${servicePriceLabel(it)}` : ''
    lines.push(`• ${it.name}${price}`)
  })
  if (items.some((it) => it.price != null)) lines.push(`Total estimado: $ ${Number(total).toLocaleString('es-AR')} (orientativo)`)
  lines.push('')
  lines.push(`Nombre: ${visitor.name}`)
  lines.push(`Teléfono: ${visitor.phone}`)
  if (visitor.address) lines.push(`Dirección: ${visitor.address}`)
  if (visitor.day || visitor.slot) lines.push(`Preferencia: ${[visitor.day, visitor.slot].filter(Boolean).join(' — ')}`)
  return lines.join('\n')
}
