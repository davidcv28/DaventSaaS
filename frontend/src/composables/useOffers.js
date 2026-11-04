import { computed, reactive, ref } from 'vue'
import { offersApi } from '../api/offers.api.js'

// Calendario de campañas de ofertas: una sola descarga por sesión,
// compartida por el panel (selector de campaña del descuento) y la web
// pública (etiquetas junto al badge de oferta).
const state = reactive({
  status: 'idle', // idle | loading | success | error
  campaigns: []
})
const loaded = ref(false)
let inflight = null

export function useOffers() {
  async function load(force = false) {
    if (loaded.value && !force) return state
    if (inflight) return inflight
    state.status = 'loading'
    inflight = offersApi.listCampaigns()
      .then((list) => {
        state.campaigns = list || []
        state.status = 'success'
        loaded.value = true
        return state
      })
      .catch(() => {
        state.status = 'error'
        return state
      })
      .finally(() => { inflight = null })
    return inflight
  }

  return {
    campaigns: computed(() => state.campaigns),
    running: computed(() => state.campaigns.filter((c) => c.is_running)),
    upcoming: computed(() => state.campaigns.filter((c) => !c.is_running)),
    bySlug: (slug) => state.campaigns.find((c) => c.slug === slug) || null,
    status: computed(() => state.status),
    load
  }
}
