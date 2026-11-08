import { http } from './http.js'

// Checklist "Calidad de tu web" (dominio stores):
// GET /api/stores/<slug>/web-quality/  Bearer -> {score: 0-100,
//   checks: [{id, weight, ok, label, action, tab}]}
//   (los pesos suman 100; `tab` es la sección del dashboard que resuelve
//   el check: photos | catalogs | company | design | settings | store).
//   403 si el slug es de otra tienda (solo dueño o staff); 404 si no existe.
export const qualityApi = {
  async webQuality(slug) {
    const { data } = await http.get(`/stores/${encodeURIComponent(slug)}/web-quality/`)
    return data
  }
}
