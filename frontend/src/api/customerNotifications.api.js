import { customerHttp } from './customer.http.js'
import { env } from '../config/env.js'

// =============================================================================
// Notificaciones del COMPRADOR en la web de tienda (campana + /cuenta).
// Auth: Bearer customer (customer.http.js) — distinto del JWT DAVENT.
//
// GET  /api/customer/notifications/               ?store=<slug> → {notifications[], unread}
// POST /api/customer/notifications/read/          {id} | {all:true, store?} → {ok, unread}
// POST /api/customer/notifications/stream-ticket/ {store} → {ticket, expires_in}
// GET  /api/customer/notifications/stream/        ?ticket&store → SSE (EventSource)
//
// El EventSource no puede mandar Authorization: el Bearer se canjea por
// un ticket firmado de vida corta (~120s) que viaja en la query. Cada
// stream dura ~50s y el front reconecta con ticket nuevo.
// =============================================================================

const base = '/customer/notifications'

export const customerNotificationsApi = {
  // Lista los avisos del comprador (≤50, de más nuevo a más viejo).
  list: (store) => customerHttp.get(`${base}/`, { params: store ? { store } : {} }).then((r) => r.data),
  // Marca UN aviso como leído (404 si es ajeno — lo decide el backend).
  markRead: (id) => customerHttp.post(`${base}/read/`, { id }).then((r) => r.data),
  // Marca todos los no-leídos; `store` acota a la tienda visitada.
  markAllRead: (store) => customerHttp.post(`${base}/read/`, { all: true, ...(store ? { store } : {}) }).then((r) => r.data),
  // Canjea un ticket de stream ligado a (comprador, tienda).
  streamTicket: (store) => customerHttp.post(`${base}/stream-ticket/`, { store: store || '' }).then((r) => r.data),
}

// URL absoluta del stream SSE con el ticket ya resuelto.
export function notificationsStreamUrl(ticket, store) {
  const q = new URLSearchParams({ ticket })
  if (store) q.set('store', store)
  return `${env.apiBaseUrl.replace(/\/$/, '')}${base}/stream/?${q.toString()}`
}
