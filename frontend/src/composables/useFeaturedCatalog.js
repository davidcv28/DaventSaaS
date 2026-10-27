// Vitrina compartida de la portada ({sort:'recent'}): una sola carga para
// todos los bloques que muestran productos — hero (chips/placas),
// departamentos, destacados, ofertas, marcas y cuenta regresiva. El
// estado vive en el módulo y loadPublicCatalog ya cachea por params, así
// que N bloques montados no suman requests ni estados duplicados.
import { ref, inject, onMounted } from 'vue'

const featured = ref({ categories: [], brands: [], products: [], promotions: [] })
const featuredStatus = ref('idle') // idle | loading | success | error
const EMPTY = { categories: [], brands: [], products: [], promotions: [] }
let loadedFor = ''

export function useFeaturedCatalog() {
  const ctx = inject('storePage')
  onMounted(() => {
    const key = ctx.slug.value
    if (loadedFor === key || !ctx.showCatalog.value) return
    loadedFor = key
    featuredStatus.value = 'loading'
    ctx.loadPublicCatalog({ sort: 'recent' })
      .then((data) => { featured.value = data; featuredStatus.value = 'success' })
      .catch(() => { featured.value = { ...EMPTY }; featuredStatus.value = 'error' })
  })
  return { featured, featuredStatus }
}
