import { ref } from 'vue'
import { defineStore } from 'pinia'
import { legalApi, buildReportPayload } from '../api/legal.api.js'
import { extractApiError } from '../api/http.js'

// Estado del formulario público de denuncias de contenido (copyright / ilegal).
export const useLegalStore = defineStore('legal', () => {
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const fieldErrors = ref({})

  async function sendReport(form) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    try {
      const data = await legalApi.reportContent(buildReportPayload(form))
      status.value = 'success'
      return { ok: true, message: data?.Exito || 'Denuncia registrada correctamente' }
    } catch (err) {
      status.value = 'error'
      const parsed = extractApiError(err)
      const { nonField, status: _s, pendingBackend, ...fields } = parsed
      fieldErrors.value = fields
      lastError.value = nonField || Object.values(fields)[0] || 'Ocurrió un error'
      if (err.response?.status === 404) {
        lastError.value = 'El servicio de denuncias no está disponible. Intentá nuevamente en unos minutos.'
      }
      return { ok: false, parsed }
    }
  }

  return { status, lastError, fieldErrors, sendReport }
})
