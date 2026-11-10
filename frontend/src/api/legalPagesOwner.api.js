import { http } from './http.js'

// =============================================================================
// Páginas legales de la tienda — lado DUEÑO (dominio legalpages).
// Espejo del archivo público legalPages.api.js (ese queda intacto: acá solo
// viven los endpoints autenticados del panel).
//
// GET  /api/store-legal-pages/                    → {pages:[{kind,kind_label,
//      title,body,is_published,is_customized,uses_default,version,updated_at,
//      persisted}]} — las 3 páginas (defaults si nunca se editaron).
//      `body` es TEXTO PLANO con placeholders {{...}} que el servidor
//      interpola solo en la web pública: acá se edita crudo, NUNCA v-html.
// PUT  /api/store-legal-pages/<kind>/             {title?,body,is_published?}
//      kind ∈ terms|privacy|returns → payload de la página.
//      OJO: 'returns' comparte path con la bandeja (GET = solicitudes,
//      PUT = la página legal).
// POST /api/store-legal-pages/<kind>/reset/       → vuelve al texto base
//      (despublicada hasta re-publicar) → {ok,kind}
// GET  /api/store-legal-pages/returns/            → {results:[{id,order_ref,
//      customer_email,name,reason,reason_display,details,status,created_at,
//      updated_at}]}  (?status= new|in_review|approved|rejected|closed)
// POST /api/store-legal-pages/returns/<pk>/status/ {status} → solicitud
//      actualizada (transiciones validadas server-side: closed es terminal)
// =============================================================================

export const legalPagesOwnerApi = {
  list: () => http.get('/store-legal-pages/').then((r) => r.data),

  save: (kind, payload) =>
    http.put(`/store-legal-pages/${kind}/`, payload).then((r) => r.data),

  reset: (kind) =>
    http.post(`/store-legal-pages/${kind}/reset/`).then((r) => r.data),

  returnRequests: ({ status } = {}) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return http.get(`/store-legal-pages/returns/${qs}`).then((r) => r.data)
  },

  setReturnStatus: (pk, status) =>
    http.post(`/store-legal-pages/returns/${pk}/status/`, { status }).then((r) => r.data),
}

// Espejo de StoreLegalPage.KIND_CHOICES / ReturnRequest.STATUS_CHOICES —
// los labels que el backend ya manda (kind_label, reason_display) son la
// fuente; estos mapas quedan para filtrar/ordenar sin hardcodear en vistas.
export const LEGAL_PAGE_KINDS = ['terms', 'privacy', 'returns']

export const RETURN_STATUS = {
  new:         { label: 'Nueva',        kind: 'warn' },
  in_review:   { label: 'En revisión',  kind: 'muted' },
  approved:    { label: 'Aprobada',     kind: 'ok' },
  rejected:    { label: 'Rechazada',    kind: 'danger' },
  closed:      { label: 'Cerrada',      kind: 'muted' },
}

// Transiciones permitidas (espejo de ReturnRequest.ALLOWED_TRANSITIONS).
export const RETURN_TRANSITIONS = {
  new:         ['in_review', 'approved', 'rejected', 'closed'],
  in_review:   ['approved', 'rejected', 'closed'],
  approved:    ['closed'],
  rejected:    ['closed'],
  closed:      [],
}
