import { http } from './http.js'

// Dominio notifications (AdminApp): avisos del sistema del panel — NO son
// mensajes de chat. El click marca leído y navega a `target` (sección del
// dashboard); nunca abre la conversación de soporte.
//
// GET  /api/notifications/               Bearer -> {notifications[], unread, unread_reviews}
// POST /api/notifications/read/          Bearer {id} | {all:true} -> {ok}
// POST /api/notifications/reviews-seen/  Bearer -> {ok, unread_reviews}
// GET  /api/changelog/                   Bearer -> [{id,title,body,published_at,created_at}]

export function fetchNotifications() {
  return http.get('/notifications/').then((r) => r.data)
}

export function markNotificationRead(id) {
  return http.post('/notifications/read/', id ? { id } : { all: true }).then((r) => r.data)
}

// El dueño abrió la sección Opiniones: las creadas hasta ahora quedan vistas.
export function markReviewsSeen() {
  return http.post('/notifications/reviews-seen/').then((r) => r.data)
}

export function fetchChangelog() {
  return http.get('/changelog/').then((r) => r.data)
}
