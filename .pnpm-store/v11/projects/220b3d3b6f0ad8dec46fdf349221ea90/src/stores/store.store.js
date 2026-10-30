import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { storesApi, CUSTOMIZATION_DEFAULTS } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { swrGet, swrSet } from '../utils/swr.js'

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
    // SWR: la tienda (diseño+cuota incluidas) pinta al instante al volver al
    // panel y se revalida en segundo plano. Las mutaciones ya refetchean.
    const cached = swrGet('store.mine')
    if (cached !== undefined) {
      store.value = cached
      storage.value = cached?.storage || null
      status.value = 'success'
    } else {
      status.value = 'loading'
    }
    lastError.value = ''
    try {
      const rows = await storesApi.listMine()
      store.value = rows[0] || null
      storage.value = rows[0]?.storage || null
      swrSet('store.mine', store.value)
      status.value = 'success'
    } catch (e) {
      if (cached !== undefined) return
      status.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudo cargar tu tienda.'
    }
  }

  function setApiError(err) {
    const parsed = extractApiError(err)
    const { nonField, status: _s, pendingBackend, ...fields } = parsed
    fieldErrors.value = fields
    // Sin nonField: mostrar el primer error de campo para no caer en el genérico.
    lastError.value = nonField || Object.values(fields)[0] || 'Ocurrió un error'
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

  // Cuota de almacenamiento ({used_bytes, max_mb, images, max_images}):
  // viaja en /stores/ al cargar y se refresca en cada subida/borrado.
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

  async function uploadCover(file) {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.uploadCover(file)
      notice.value = data?.Exito || 'La imagen de portada se actualizó correctamente.'
      applyCustomizationData(data)
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function removeCover() {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.removeCover()
      notice.value = data?.Exito || 'La imagen de portada se eliminó correctamente.'
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

  // Galería de la web pública (tope max_gallery_images del plan: Básico 0,
  // Estándar 5, Premium 15). Mismo patrón que el carrusel.
  async function addGalleryImage(file, kind = 'gallery') {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.addGalleryImage(file, kind)
      notice.value = data?.Exito || 'La imagen se agregó a la galería.'
      if (data?.storage) storage.value = data.storage
      await refreshCustomization()
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function removeGalleryImage(imageId) {
    if (!store.value) return false
    lastError.value = ''
    notice.value = ''
    try {
      const data = await storesApi.removeGalleryImage(imageId)
      notice.value = data?.Exito || 'La imagen se eliminó de la galería.'
      if (data?.storage) storage.value = data.storage
      await refreshCustomization()
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function moveGalleryImage(imageId, direction) {
    const list = customization.value.gallery || []
    const index = list.findIndex((img) => img.id === imageId)
    const target = index + direction
    if (index < 0 || target < 0 || target >= list.length) return false
    const order = list.map((img) => img.id)
    ;[order[index], order[target]] = [order[target], order[index]]
    try {
      await storesApi.reorderGallery(order)
      await refreshCustomization()
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  // Studio — borrador → publicar: publish aplica los *_draft a la web y
  // guarda versión; discard los revierte al publicado; restore recupera
  // un snapshot. Las tres actualizan customization y dejan el Studio
  // re-sembrado (has_unpublished queda en el payload).
  async function publishCustomization(note = '') {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.publishCustomization(note)
      notice.value = data?.Exito || 'Publicaste los cambios de tu web.'
      applyCustomizationData(data)
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function discardCustomization() {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.discardCustomization()
      notice.value = data?.Exito || 'Descartaste los cambios sin publicar.'
      applyCustomizationData(data)
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  async function restoreStudioVersion(versionId) {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.restoreStudioVersion(versionId)
      notice.value = data?.Exito || 'Restauraste esa versión de tu web.'
      applyCustomizationData(data)
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  // Link temporal "compartir vista previa" del borrador (72 h): el token
  // firmado habilita /<slug>?preview=<token> sin auth. Devuelve la URL
  // absoluta lista para pegar o null si falla.
  async function createShareLink() {
    if (!store.value) return null
    lastError.value = ''
    fieldErrors.value = {}
    try {
      const data = await storesApi.sharePreview()
      const url = `${window.location.origin}${data.path}`
      return { url, expiresAt: data.expires_at, ttl: data.ttl }
    } catch (e) {
      setApiError(e)
      return null
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
    visitStats.value = null
    chatbot.value = null
  }

  // Visitas de la web pública (beneficio has_stats: Estándar+). null = sin
  // dato o sin permiso (403 Básico).
  const visitStats = ref(null) // {total, today, days: [{date, count}]}

  async function loadStats() {
    const cached = swrGet('store.stats')
    if (cached !== undefined) visitStats.value = cached
    try {
      visitStats.value = await storesApi.stats()
      swrSet('store.stats', visitStats.value)
    } catch {
      if (cached === undefined) visitStats.value = null
    }
  }

  // Chatbot de la web pública (beneficio has_chatbot: solo Premium). El dueño
  // carga pares {q, a} que el widget responde a las visitas; PATCH da 403
  // sin el beneficio (el backend lo fuerza igual que el diseño).
  const chatbot = ref(null) // {is_enabled, greeting, qa:[{q,a}]} | null

  async function loadChatbot() {
    if (!store.value) return
    try {
      chatbot.value = await storesApi.chatbot()
    } catch {
      chatbot.value = null
    }
  }

  async function saveChatbot(payload) {
    if (!store.value) return false
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await storesApi.updateChatbot(payload)
      notice.value = data?.Exito || 'El chatbot se actualizó correctamente.'
      if (data?.chatbot) chatbot.value = data.chatbot
      return true
    } catch (e) {
      setApiError(e)
      return false
    }
  }

  return {
    store, status, lastError, notice, fieldErrors, hasStore, customization, storage, visitStats,
    saveCustomization, uploadLogo, removeLogo, uploadCover, removeCover,
    addCarouselImage, removeCarouselImage, moveCarouselImage, refreshCustomization,
    addGalleryImage, removeGalleryImage, moveGalleryImage,
    publishCustomization, discardCustomization, restoreStudioVersion, createShareLink,
    loadMine, claim, update, reset, loadStats, chatbot, loadChatbot, saveChatbot
  }
})
