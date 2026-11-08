import { ref, computed, watch } from 'vue'
import { qualityApi } from '../api/quality.api.js'

// Checklist "Calidad de tu web": score 0-100 + checks fallidos accionables.
// `getSlug` puede ser un ref/computed o una función que devuelva el slug de
// la tienda (store.store?.slug en DashboardView). Recarga cuando el slug
// aparece o cambia; `load()` queda expuesta para refrescar al volver a Inicio.
export function useWebQuality(getSlug) {
  const report = ref(null)   // {score, checks:[{id, weight, ok, label, action, tab}]}
  const loading = ref(false)
  const loaded = ref(false)

  const slugOf = () => (typeof getSlug === 'function' ? getSlug() : getSlug?.value ?? getSlug)

  async function load() {
    const slug = slugOf()
    if (!slug) {
      report.value = null
      return
    }
    loading.value = true
    try {
      report.value = await qualityApi.webQuality(slug)
    } catch {
      //La tarjeta es un extra del resumen: si el endpoint falla queda
      //oculta, nunca rompe el dashboard.
      report.value = null
    } finally {
      loading.value = false
      loaded.value = true
    }
  }

  watch(slugOf, (slug, prev) => {
    if (slug && slug !== prev) load()
  }, { immediate: true })

  const score = computed(() => report.value?.score ?? null)
  //Los checks que faltan, del mayor peso al menor (el endpoint ya los manda
  //todos con ok; la tarjeta muestra solo el top).
  const failedChecks = computed(() =>
    (report.value?.checks || []).filter((c) => !c?.ok).sort((a, b) => (b.weight || 0) - (a.weight || 0))
  )

  return { report, loading, loaded, score, failedChecks, load }
}
