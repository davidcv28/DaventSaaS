import { ref, computed } from 'vue'
import { storesApi, normalizeSlug, validateSlugFormat } from '../api/stores.api.js'

// Check de disponibilidad de slug con debounce (onboarding + rename).
// Estados: idle | checking | available | taken | reserved | invalid | error | same
export function useSlugCheck() {
  const state = ref('idle')
  const checked = ref('')
  let timer = null

  const isAvailable = computed(() => state.value === 'available')

  const message = computed(() => ({
    checking: 'Verificando disponibilidad…',
    available: 'Ese link está disponible',
    taken: 'Ese link ya está en uso',
    reserved: 'Ese link está reservado por la plataforma',
    invalid: validateSlugFormat(checked.value) || 'Formato inválido',
    error: 'No se pudo verificar. Probá de nuevo.',
    same: 'Es tu link actual'
  }[state.value] || ''))

  const kind = computed(() => {
    if (state.value === 'available') return 'ok'
    if (['taken', 'reserved', 'invalid', 'error'].includes(state.value)) return 'err'
    return 'pending'
  })

  function requestCheck(raw, { current = '' } = {}) {
    const slug = normalizeSlug(raw)
    clearTimeout(timer)
    checked.value = slug
    if (!slug) { state.value = 'idle'; return }
    if (current && slug === current) { state.value = 'same'; return }
    if (validateSlugFormat(slug)) { state.value = 'invalid'; return }
    state.value = 'checking'
    timer = setTimeout(async () => {
      try {
        const res = await storesApi.slugAvailable(slug)
        if (checked.value !== slug) return
        state.value = res.available ? 'available' : (res.reason || 'taken')
      } catch {
        if (checked.value === slug) state.value = 'error'
      }
    }, 350)
  }

  function clear() {
    clearTimeout(timer)
    state.value = 'idle'
    checked.value = ''
  }

  return { state, isAvailable, message, kind, checked, requestCheck, clear }
}
