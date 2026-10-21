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
      applyCustomizationData(data)
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  // Cuota de almacenamiento ({used_bytes, max_mb}) devuelta por las acciones de diseño/logo.
  const storage = ref(null)

  function applyCustomizationData(data) {
    if (data?.customization) store.value = { ...store.value, customization: data.customization }
    if (data?.storage) storage.value = data.storage
  }

  async function uploadLogo(file) {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.uploadLogo(file)
      notice.value = data?.Exito || 'El logo se actualizó correctamente.'
      applyCustomizationData(data)
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function removeLogo() {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.removeLogo()
      notice.value = data?.Exito || 'El logo se eliminó correctamente.'
      applyCustomizationData(data)
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  // Carrusel de banners de la web pública (premium). Cada acción devuelve
  // customization/storage actualizados o solo storage; acá se renormaliza.
  async function addCarouselImage(file) {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.addCarouselImage(file)
      notice.value = data?.Exito || 'La imagen se agregó al carrusel.'
      if (data?.storage) storage.value = data.storage
      await refreshCustomization()
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function removeCarouselImage(imageId) {
    if (!store.value) return false
    lastError.value = ''
    notice.value = ''
    try {
      const data = await storesApi.removeCarouselImage(imageId)
      notice.value = data?.Exito || 'La imagen se eliminó del carrusel.'
      if (data?.storage) storage.value = data.storage
      await refreshCustomization()
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function moveCarouselImage(imageId, direction) {
    const list = customization.value.carousel || []
    const index = list.findIndex((img) => img.id === imageId)
    const target = index + direction
    if (index < 0 || target < 0 || target >= list.length) return false
    const order = list.map((img) => img.id)
    ;[order[index], order[target]] = [order[target], order[index]]
    try {
      await storesApi.reorderCarousel(order)
      await refreshCustomization()
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function refreshCustomization() {
    try {
      const data = await storesApi.customization()
      if (data) store.value = { ...store.value, customization: data }
    } catch {
      // Si falla el refresh quedan los datos previos; no interrumpe el flujo.
    }
  }

  function reset() {
    store.value = null
    status.value = 'idle'
    lastError.value = ''
    notice.value = ''
    fieldErrors.value = {}
    storage.value = null
  }

  return {
    store, status, lastError, notice, fieldErrors, hasStore, customization, storage,
    saveCustomization, uploadLogo, removeLogo,
    addCarouselImage, removeCarouselImage, moveCarouselImage, refreshCustomization,
    loadMine, claim, update, reset
  }
})
