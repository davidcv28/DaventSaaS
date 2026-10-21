import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { storesApi, CUSTOMIZATION_DEFAULTS } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'

// Tienda del cliente: link público (claim en el primer ingreso), rename y pausa.
// El backend modela OneToOne UserProfile->Store: lista de 0..1.
export const useStoreStore = defineStore('store', () => {
  const store = ref(null)
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const notice = ref('')
  const fieldErrors = ref({})

  const hasStore = computed(() => Boolean(store.value))
  // Diseño de la web pública (StoreCustomization anidado en /stores/; null -> defaults).
  const customization = computed(() => ({ ...CUSTOMIZATION_DEFAULTS, ...(store.value?.customization || {}) }))

  async function loadMine() {
    status.value = 'loading'
    lastError.value = ''
    try {
      const rows = await storesApi.listMine()
      store.value = rows[0] || null
      status.value = 'success'
    } catch (e) {
      status.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudo cargar tu tienda.'
    }
  }

  function setApiError(err) {
    const parsed = extractApiError(err)
    lastError.value = parsed.nonField || 'Ocurrió un error'
    const { nonField, status: _s, pendingBackend, ...fields } = parsed
    fieldErrors.value = fields
    return parsed
  }

  async function claim(slug) {
    status.value = 'loading'
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.claim(slug)
      notice.value = data?.Exito || 'Tu link público se creó correctamente.'
      await loadMine()
      return true
    } catch (e) {
      status.value = 'error'
      setApiError(e)
      return false
    }
  }

  async function update(payload) {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.update(store.value.id, payload)
      notice.value = data?.Exito || 'Tu tienda se actualizó correctamente.'
      await loadMine()
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function saveCustomization(payload) {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.updateCustomization(payload)
      notice.value = data?.Exito || 'El diseño de tu web se actualizó correctamente.'
      if (data?.customization) store.value = { ...store.value, customization: data.customization }
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  function reset() {
    store.value = null
    status.value = 'idle'
    lastError.value = ''
    notice.value = ''
    fieldErrors.value = {}
  }

  return {
    store, status, lastError, notice, fieldErrors, hasStore, customization, saveCustomization,
    loadMine, claim, update, reset
  }
})
