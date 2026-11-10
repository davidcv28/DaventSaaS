import { http } from './http.js'

// =============================================================================
// Soporte del DUEÑO — hilos de consulta de SUS compradores (dominio support).
// Distinto de /api/chat/ (asistente DAVENT con el staff de la plataforma).
//
// GET  /api/store-support/threads/?status=&unread=&page=&page_size=
//   → paginado {count,next,previous,results:[{id,subject,status,store,
//      customer:{name,email},order:{id,code,status}|null,last_message_at,
//      last_message_by,unread_count,created_at,updated_at}]}
//      status ∈ open|closed; unread=1 → solo hilos con mensajes sin leer.
// GET  /api/store-support/threads/<id>/   → detalle + messages[] (leer marca
//      leídos los mensajes DEL COMPRADOR — unread_count vuelve en 0).
// POST /api/store-support/threads/<id>/messages/  {body} → responde (hilo
//      cerrado → 400; reabrir antes con /reopen/).
// POST /api/store-support/threads/<id>/close/     → cerrar (idempotente).
// POST /api/store-support/threads/<id>/reopen/    → reabrir (idempotente).
//
// Todo scopeado a la tienda del dueño (IDOR = 404). Los mensajes son texto
// plano: se renderizan escapados por Vue, NUNCA con v-html.
// =============================================================================

function buildParams(params = {}) {
  const out = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    out.set(key, value)
  }
  const qs = out.toString()
  return qs ? `?${qs}` : ''
}

export const storeSupportApi = {
  list: (params = {}) =>
    http.get(`/store-support/threads/${buildParams(params)}`).then((r) => r.data),

  detail: (id) =>
    http.get(`/store-support/threads/${id}/`).then((r) => r.data),

  reply: (id, body) =>
    http.post(`/store-support/threads/${id}/messages/`, { body }).then((r) => r.data),

  close: (id) =>
    http.post(`/store-support/threads/${id}/close/`).then((r) => r.data),

  reopen: (id) =>
    http.post(`/store-support/threads/${id}/reopen/`).then((r) => r.data),
}
