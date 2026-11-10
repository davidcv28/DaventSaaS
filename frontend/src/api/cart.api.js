import { customerHttp } from './customer.http.js'
import { publicHttp } from './http.js'

// =============================================================================
// Carrito del comprador por tienda (dominio cart). Requiere sesión de
// comprador (customerHttp — NO la sesión DAVENT del dueño).
//
// GET    /api/cart/<slug>/                 → {store,items,item_count,items_total,member_discount_percent}
// POST   /api/cart/<slug>/                 → get-or-create; body opcional {product_id,qty} upsert
// POST   /api/cart/<slug>/items/           → {product_id,qty} upsert
// PATCH  /api/cart/<slug>/items/           → idem (alias)
// DELETE /api/cart/<slug>/items/           → vacía el carrito
// PATCH  /api/cart/<slug>/items/<id>/      → {qty}
// DELETE /api/cart/<slug>/items/<id>/      → quita la línea
//
// Cada item: {id,product_id,name,qty,list_price,unit_price,line_total,
// image,stock,purchasable,unavailable_reason}. Los precios se recalculan
// server-side en cada lectura — nunca cachear montos.
// =============================================================================

export const cartApi = {
  get: (slug) => customerHttp.get(`/cart/${slug}/`).then((r) => r.data),
  // Atajo: crea el carrito y (opcional) suma la línea en un request.
  add: (slug, productId, qty = 1) => customerHttp.post(`/cart/${slug}/`, { product_id: productId, qty }).then((r) => r.data),
  addItem: (slug, productId, qty = 1) => customerHttp.post(`/cart/${slug}/items/`, { product_id: productId, qty }).then((r) => r.data),
  updateItem: (slug, itemId, qty) => customerHttp.patch(`/cart/${slug}/items/${itemId}/`, { qty }).then((r) => r.data),
  removeItem: (slug, itemId) => customerHttp.delete(`/cart/${slug}/items/${itemId}/`).then((r) => r.data),
  clear: (slug) => customerHttp.delete(`/cart/${slug}/items/`).then((r) => r.data),
}

// Captcha del checkout/pedidos: mismo mecanismo firmado que reviews.
export const orderCaptchaApi = {
  get: (slug) => publicHttp.get(`/stores/public/${slug}/orders/captcha/`).then((r) => r.data),
}
