import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { servicesApi, SERVICE_LIMITS } from '../api/services.api.js'
import { extractApiError } from '../api/http.js'
import { swrGet, swrSet } from '../utils/swr.js'

// Servicios del cliente: los ítems de la página "Servicios" de su web.
// Requieren el flag 'has_services_site' del plan vigente (Estándar+): sin
// el beneficio el backend devuelve 403 en todo el endpoint (denied=true).
export const useServicesStore = defineStore('services', () => {
  const items = ref([])
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const notice = ref('')
  const fieldErrors = ref({})
  const denied = ref(false) // 403: el plan no incluye la página Servicios

  const limitReached = computed(() => items.value.length >= SERVICE_LIMITS.max)
  const activeCount = computed(() => items.value.filter((s) => s.is_active).length)

  function setApiError(err) {
    const parsed = extractApiError(err)
    const { nonField, status: _s, pendingBackend, ...fields } = parsed
    lastError.value = nonField || Object.values(fields)[0] || 'Ocurrió un error'
    if (parsed.status === 403) denied.value = true
    fieldErrors.value = fields
    return parsed
  }

  async function loadAll() {
    // SWR: la sección "Mis servicios" pinta con lo último cargado mientras
    // se revalida (mismo patrón que catalog.loadAll).
    const cached = swrGet('services.all')
    if (cached !== undefined) {
      items.value = cached.items || []
      status.value = 'success'
    } else {
      status.value = 'loading'
    }
    lastError.value = ''
    denied.value = false
    try {
      const list = await servicesApi.listServices()
      items.value = list
      swrSet('services.all', { items: list })
      status.value = 'success'
    } catch (e) {
      if (cached !== undefined) return
      status.value = 'error'
      setApiError(e)
    }
  }

  async function run(action, fallback) {
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await action()
      notice.value = data?.Exito || fallback
      return { ok: true, data }
    } catch (e) {
      setApiError(e)
      return { ok: false, data: null }
    }
  }

  async function saveService(pk, payload) {
    const res = await run(
      () => pk ? servicesApi.updateService(pk, payload) : servicesApi.createService(payload),
      'El servicio se guardó correctamente.'
    )
    if (res.ok) items.value = await servicesApi.listServices()
    return res.ok
  }
  async function toggleService(s) {
    const res = await run(
      () => servicesApi.updateService(s.id, { is_active: !s.is_active }),
      s.is_active ? 'El servicio se ocultó de tu página.' : 'El servicio vuelve a estar visible.'
    )
    if (res.ok) {
      const target = items.value.find((x) => x.id === s.id)
      if (target) target.is_active = !s.is_active
    }
    return res.ok
  }
  async function removeService(pk) {
    const res = await run(() => servicesApi.deleteService(pk), 'El servicio se eliminó.')
    if (res.ok) items.value = items.value.filter((s) => s.id !== pk)
    return res.ok
  }
  async function saveOrder() {
    const res = await run(
      () => servicesApi.saveOrder(items.value.map((s) => s.id)),
      'El orden de tus servicios se actualizó.'
    )
    return res.ok
  }
  function moveItem(pk, dir) {
    // Reordenamiento local optimista: al guardar, saveOrder manda la lista
    // de ids tal cual quedó (el backend reasigna position atómico).
    const idx = items.value.findIndex((s) => s.id === pk)
    const target = idx + dir
    if (idx < 0 || target < 0 || target >= items.value.length) return
    const list = [...items.value]
    const [item] = list.splice(idx, 1)
    list.splice(target, 0, item)
    items.value = list
  }

  function reset() {
    items.value = []
    status.value = 'idle'
    lastError.value = ''
    notice.value = ''
    fieldErrors.value = {}
    denied.value = false
  }

  return {
    items, status, lastError, notice, fieldErrors, denied,
    limitReached, activeCount,
    loadAll, saveService, toggleService, removeService, saveOrder, moveItem, reset
  }
})
