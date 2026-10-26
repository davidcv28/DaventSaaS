import { http } from './http.js'

// =============================================================================
// Chat de soporte cliente <-> staff (asíncrono: polling + heartbeat).
// Sin websockets — el backend corre gunicorn sync; el polling con cursor
// `after` (último id conocido) trae solo lo nuevo.
//   Cliente: exige el flag has_support_chat del plan (gate server-side).
//   Staff: siempre habilitado, ve la bandeja completa de conversaciones.
// =============================================================================

// Cliente: hilo propio (mensajes + staff_online + unread).
// Staff: bandeja completa (threads[] + online[]).
export function fetchChat() {
  return http.get('/chat/').then((r) => r.data)
}

// Incremental: `after` = último id de mensaje ya mostrado (0 = últimos 50).
// `thread` solo aplica al staff (lee el hilo indicado); el cliente siempre
// recibe el suyo aunque mande un id ajeno.
export function fetchChatMessages({ after = 0, thread = null } = {}) {
  const params = { after }
  if (thread) params.thread = thread
  return http.get('/chat/messages/', { params }).then((r) => r.data)
}

// Cliente: {body} (el hilo se crea solo en el primer envío).
// Staff: {body, thread} con el id de la conversación a responder.
export function sendChatMessage(body, thread = null) {
  const payload = { body }
  if (thread) payload.thread = thread
  return http.post('/chat/send/', payload).then((r) => r.data)
}

// Heartbeat de presencia (~45s mientras el chat está abierto): marca al
// usuario como conectado y devuelve unread + quiénes están en línea.
export function chatHeartbeat() {
  return http.post('/chat/heartbeat/', {}).then((r) => r.data)
}
