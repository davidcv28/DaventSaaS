import { http } from './http.js'

// =============================================================================
// "Tu Asistente" — bot MCP de la cuenta del usuario en sesión.
// Hilo aparte del chat de soporte (el staff no lo ve). Gate server-side:
// autenticado + plan pago vigente no-trial (mcp_user_access).
// =============================================================================

// GET /api/assistant/ → { messages } (+ saludo en el primer acceso).
export function fetchAssistant() {
  return http.get('/assistant/').then((r) => r.data)
}

// POST /api/assistant/send/ {body} → { reply } — el mensaje del usuario
// queda guardado y la respuesta del asistente vuelve en la misma request.
export function sendAssistant(body) {
  return http.post('/assistant/send/', { body }).then((r) => r.data)
}
