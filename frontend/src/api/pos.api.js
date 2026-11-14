import { http } from './http.js'

// =============================================================================
// Apps federadas (StoreApp/domains/pos — PLAN_POS.md):
// GET  /api/pos/apps/        Bearer → {rubro, rubros[], apps[]} — catálogo
//                            filtrado por plan + rubro (?rubro=<slug> pisa el
//                            rubro derivado del diseño de la tienda). Cada app:
//                            {slug, nombre, descripcion, rubros[], tier_min,
//                            version, download_key, preview_url}
// POST /api/pos/pair-code/   Bearer → {code, expires_at} — código de vinculación
//                            de 8 chars, expira ~10 min, un solo uso. La app de
//                            mostrador lo canjea en /api/pos/pair/ por un
//                            device_token.
// =============================================================================

export const fetchPosApps = (rubro) =>
  http.get('/pos/apps/', { params: rubro ? { rubro } : {} }).then((r) => r.data)
// GET /api/pos/download/<slug>/ → {url} — URL firmada de R2 (10 min).
export const downloadPosApp = (slug) => http.get(`/pos/download/${slug}/`).then((r) => r.data)
export const createPosPairCode = () => http.post('/pos/pair-code/').then((r) => r.data)
