import { http } from './http.js'

// =============================================================================
// Apps federadas (StoreApp/domains/pos — PLAN_POS.md):
// GET  /api/pos/apps/        Bearer → catálogo filtrado por plan + rubro de la
//                            tienda: [{slug, nombre, descripcion, rubros[],
//                            tier_min, version, download_key}]
// POST /api/pos/pair-code/   Bearer → {code, expires_at} — código de vinculación
//                            de 8 chars, expira ~10 min, un solo uso. La app de
//                            mostrador lo canjea en /api/pos/pair/ por un
//                            device_token.
// =============================================================================

export const fetchPosApps = () => http.get('/pos/apps/').then((r) => r.data)
export const createPosPairCode = () => http.post('/pos/pair-code/').then((r) => r.data)
