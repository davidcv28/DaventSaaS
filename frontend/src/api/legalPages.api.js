import { publicHttp } from './http.js'

// =============================================================================
// Páginas legales PÚBLICAS de la tienda (dominio legalpages — sin login).
// El `body` es TEXTO PLANO del dueño con placeholders fiscales ya
// interpolados por el servidor: se renderiza literal (whitespace-pre-line),
// NUNCA como HTML — no usar v-html.
//
// GET  /api/stores/public/<slug>/legal/                  → {pages:[{kind,kind_label,title,updated_at,version}]}
// GET  /api/stores/public/<slug>/legal/<kind>/           → {kind,kind_label,title,body,fiscal,fiscal_complete,updated_at}
// GET  /api/stores/public/<slug>/legal/captcha/          → {challenge_id, question}
// POST /api/stores/public/<slug>/legal/returns/request/  → {order_ref?,name,email,reason,details?,website?,challenge_id,captcha_answer}
//      → SIEMPRE 201 {ok:true} en éxito/ honeypot (anti-enumeración)
// =============================================================================

const base = (slug) => `/stores/public/${slug}/legal`

export const legalPagesApi = {
  index: (slug) => publicHttp.get(`${base(slug)}/`).then((r) => r.data),
  page: (slug, kind) => publicHttp.get(`${base(slug)}/${kind}/`).then((r) => r.data),
  captcha: (slug) => publicHttp.get(`${base(slug)}/captcha/`).then((r) => r.data),
  requestReturn: (slug, payload) => publicHttp.post(`${base(slug)}/returns/request/`, payload).then((r) => r.data),
}

// kinds públicos válidos (espejo de StoreLegalPage.KIND_CHOICES).
export const LEGAL_KINDS = {
  terms: 'Términos y condiciones',
  privacy: 'Política de privacidad',
  returns: 'Devoluciones',
}
