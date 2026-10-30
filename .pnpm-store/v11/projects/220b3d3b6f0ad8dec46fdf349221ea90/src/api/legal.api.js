import { http } from './http.js'

// Dominio legal — denuncia pública de contenido (AllowAny):
// POST /api/content-reports/  -> 201 {Exito}
// GET/PATCH /api/content-reports/ solo staff (IsAdminUser), sin UI por ahora.

export const legalApi = {
  async reportContent(payload) {
    // Mismo patrón que authApi.register: slash canónico DRF + fallback sin slash.
    try {
      const { data } = await http.post('/content-reports/', payload)
      return data
    } catch (e) {
      if (e.response?.status === 404) {
        const { data } = await http.post('/content-reports', payload)
        return data
      }
      throw e
    }
  }
}

// Arma el payload exacto de ContentReportSerializer.
export function buildReportPayload(form) {
  return {
    reporter_name: form.reporter_name?.trim(),
    reporter_email: form.reporter_email?.trim(),
    kind: form.kind || 'COPYRIGHT',
    reported_url: form.reported_url?.trim(),
    original_work: form.original_work?.trim() || null,
    description: form.description?.trim(),
    good_faith: form.good_faith === true
  }
}
