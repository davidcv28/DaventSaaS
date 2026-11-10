import { extractApiError } from '../../../api/http.js'

// =============================================================================
// Helpers compartidos de la sección "Vender online" (dashboard/ecommerce).
// Labels es-AR de estados del contrato backend + parseo de errores DRF.
// =============================================================================

const arsFmt = new Intl.NumberFormat('es-AR', {
  style: 'currency', currency: 'ARS',
  minimumFractionDigits: 2, maximumFractionDigits: 2,
})

export function apiErr(err, fallback = 'Ocurrió un error. Intentá de nuevo.') {
  const parsed = extractApiError(err)
  if (parsed?.pendingBackend) return parsed.nonField
  const first = parsed?.nonField
    || Object.entries(parsed || {})
        .filter(([k]) => !['status', 'nonField'].includes(k))
        .map(([, v]) => v)[0]
  return first || err?.message || fallback
}

export function isNotFound(err) {
  return extractApiError(err)?.status === 404
}

// ----- Pedidos (Order.Status / PaymentMethod / ShippingMethod) -----
export const ORDER_STATUS = {
  PENDING_PAYMENT: { label: 'Pendiente de pago', kind: 'warn' },
  PAID:            { label: 'Pagado',           kind: 'ok' },
  PACKING:         { label: 'Preparando',       kind: 'muted' },
  SHIPPED:         { label: 'Enviado',          kind: 'muted' },
  DELIVERED:       { label: 'Entregado',        kind: 'ok' },
  CANCELLED:       { label: 'Cancelado',        kind: 'danger' },
  REFUNDED:        { label: 'Reembolsado',      kind: 'danger' },
  EXPIRED:         { label: 'Vencido',          kind: 'muted' },
}
export const ORDER_STATUSES = Object.keys(ORDER_STATUS)

export const PAYMENT_METHODS = {
  transfer: { label: 'Transferencia' },
  whatsapp: { label: 'WhatsApp' },
  cash:     { label: 'Efectivo' },
  mp:       { label: 'Mercado Pago' },
}
export const PAYMENT_METHOD_KEYS = Object.keys(PAYMENT_METHODS)

export const SHIPPING_METHODS = {
  home:   { label: 'Envío a domicilio' },
  pickup: { label: 'Retiro en el local' },
}

// Siguiente paso logístico sugerido al dueño (espejo de TRANSITIONS del
// modelo Order — solo orientativo: el backend valida la transición real).
export const NEXT_ORDER_ACTION = {
  PENDING_PAYMENT: null,
  PAID:            { target: 'PACKING',     label: 'Preparar pedido' },
  PACKING:         { target: 'SHIPPED',    label: 'Marcar enviado' },
  SHIPPED:         { target: 'DELIVERED',  label: 'Marcar entregado' },
  DELIVERED:       null,
  CANCELLED:       null,
  REFUNDED:        null,
  EXPIRED:         null,
}

// ----- Soporte de compradores (Thread.status) -----
export const THREAD_STATUS = {
  open:   { label: 'Abierto', kind: 'ok' },
  closed: { label: 'Cerrado', kind: 'muted' },
}

// ----- Suscripciones de tienda (Subscription.status) -----
export const SUBSCRIPTION_STATUS = {
  pending:    { label: 'Pendiente de pago', kind: 'warn' },
  active:     { label: 'Activa',            kind: 'ok' },
  past_due:   { label: 'Pago vencido',      kind: 'warn' },
  cancelled:  { label: 'Cancelada',         kind: 'muted' },
  expired:    { label: 'Vencida',           kind: 'muted' },
}
export const SUBSCRIPTION_STATUSES = Object.keys(SUBSCRIPTION_STATUS)

// ----- Planes de membresía -----
export const PLAN_PERIODS = {
  monthly: { label: 'Mensual',    days: 30 },
  yearly:  { label: 'Anual',      days: 365 },
  custom:  { label: 'Personalizado' },
}

// Beneficios del contrato (StorePlan boolean fields → códigos benefits.py).
export const PLAN_BENEFITS = [
  { key: 'has_digital_card',          label: 'Tarjeta digital',            code: 'digital_card' },
  { key: 'has_free_shipping',         label: 'Envío gratis',               code: 'free_shipping' },
  { key: 'has_exclusive_discounts',   label: 'Descuentos exclusivos',      code: 'exclusive_discounts' },
  { key: 'has_exclusive_access',      label: 'Acceso a productos exclusivos', code: 'exclusive_access' },
]

// ----- Condición fiscal -----
export const TAX_CONDITIONS = [
  { value: 'CF', label: 'Consumidor Final' },
  { value: 'MO', label: 'Monotributo' },
  { value: 'RI', label: 'Responsable Inscripto' },
  { value: 'EX', label: 'Exento' },
]

// ----- Membresía del cliente (StoreMembership.status) -----
export const MEMBERSHIP_STATUS = {
  active:     { label: 'Miembro',  kind: 'ok' },
  suspended:  { label: 'Suspendido', kind: 'warn' },
}

// ----- Fechas -----
export function fmtDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('es-AR')
}
export function fmtDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })
}
export function todayISO() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
export function daysAgoISO(days) {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
export function statusMeta(map, key) {
  return map?.[key] || { label: key || '—', kind: 'muted' }
}
export function money(v) {
  // Los decimales vienen como string desde el backend; 0 es un total
  // válido (no "Gratis" como hace formatARS de billing).
  const n = Number(v ?? 0)
  return Number.isFinite(n) ? arsFmt.format(n) : '—'
}
