// =============================================================================
// Comercio compartido de la web pública: métodos de pago del checkout y
// línea de envío. Lo consumen la ficha de producto (Vue), el checkout y —
// con su propio render — los documentos de diseño (pattern_render emite el
// mismo criterio en `product_payments`).
//
// Fuente del payload `payments` (StorePublicSerializer.payments y
// /membership-plans/): {accept_transfer, accept_whatsapp, accept_cash,
// mp_enabled, mp_connected}. Los flags ausentes NO habilitan métodos:
// transfer/whatsapp/mp siguen la lógica del checkout (default del modelo
// ya viene resuelto por el backend).
// =============================================================================
import { formatARS } from './billing.api.js'

// Icono + descripción por método — el server decide qué están habilitados
// (mismo mapa que StoreCheckoutView: si cambia un label, cambia en ambos).
export const PAYMENT_UI = {
  transfer: { icon: 'building-2',  hint: 'Transferí o depositá en la cuenta del comercio y después subí el comprobante.' },
  whatsapp: { icon: 'whatsapp',    hint: 'El pago se coordina por WhatsApp con el comercio.' },
  cash:     { icon: 'wallet',      hint: 'Pagás en efectivo al retirar el pedido o al recibirlo.' },
  mp:       { icon: 'credit-card', hint: 'Te llevamos a Mercado Pago para pagar; la acreditación es automática.' },
}

// paymentMethodsFromConfig(payments) → [{value,label,icon,hint}] en el
// orden comercial del checkout. Acepta el objeto `payments` del payload
// público (store.payments o data.payments de membership-plans).
export function paymentMethodsFromConfig(payments) {
  const p = payments || {}
  const list = []
  if (p.accept_transfer !== false) list.push({ value: 'transfer', label: 'Transferencia / depósito', ...PAYMENT_UI.transfer })
  if (p.accept_whatsapp !== false) list.push({ value: 'whatsapp', label: 'Coordinar por WhatsApp', ...PAYMENT_UI.whatsapp })
  if (p.accept_cash) list.push({ value: 'cash', label: 'Efectivo / en persona', ...PAYMENT_UI.cash })
  if (p.mp_connected) list.push({ value: 'mp', label: 'Mercado Pago', ...PAYMENT_UI.mp })
  return list
}

// Tarifa de envío a domicilio del payload público (store.shipping):
// home_price null = "a coordinar"; número >= 0 = precio fijo del checkout
// (0 = envío gratis). El retiro en el local siempre es sin cargo.
export function homeShippingPrice(storeData) {
  const raw = storeData?.shipping?.home_price
  if (raw === null || raw === undefined || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

// Línea corta para fichas/tarjetas: "Envío a domicilio $X · retiro sin cargo".
// Devuelve '' cuando la tienda no vende online (la vista decide el gate).
export function shippingLine(storeData, ordersEnabled) {
  if (!ordersEnabled) return ''
  const price = homeShippingPrice(storeData)
  const home = price === null ? 'a coordinar' : price > 0 ? formatARS(price) : 'sin cargo'
  return `Envío a domicilio ${home} · retiro en el local sin cargo`
}
