import { ref, computed } from 'vue'

// Normaliza errores DRF a { campo: mensaje } para la UI (FRONTEND_RULES §4).
// DRF responde {field: [msgs]} | {field: "msg"} | {detail} | {non_field_errors}.
export function useFormErrors() {
  const fieldErrors = ref({})
  const nonField = ref('')

  function firstMessage(value) {
    if (Array.isArray(value)) return String(value[0])
    return String(value)
  }

  function setFromApi(errorPayload = {}) {
    const next = {}
    let banner = ''
    for (const [key, value] of Object.entries(errorPayload || {})) {
      if (key === 'status' || key === 'pendingBackend') continue
      if (['detail', 'non_field_errors', 'nonField'].includes(key)) {
        banner = firstMessage(value)
      } else {
        next[key] = firstMessage(value)
      }
    }
    fieldErrors.value = next
    nonField.value = banner
  }

  function setField(field, message) {
    fieldErrors.value = { ...fieldErrors.value, [field]: message || undefined }
  }

  function clear() {
    fieldErrors.value = {}
    nonField.value = ''
  }

  const hasErrors = computed(() => Object.values(fieldErrors.value).some(Boolean) || Boolean(nonField.value))

  return { fieldErrors, nonField, hasErrors, setFromApi, setField, clear }
}
