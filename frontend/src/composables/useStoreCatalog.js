import { ref, reactive, computed, watch, inject, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeHostSlug } from '../config/env.js'
import { formatARS } from '../api/billing.api.js'
import { productOffer } from '../api/catalog.api.js'

// Estado y lógica compartidos por todas las páginas de catálogo de la web
// pública (/<slug>/catalogo): filtros, orden, búsqueda (compartida con el
// buscador del header por `ui.search`), paginado y navegación a la ficha.
// Cada diseño (Clásico, Perspectiva, Dúo, ...) solo pone su propia
// presentación encima de este estado.
const SORTS = ['name', 'recent', 'price_asc', 'price_desc']
export const SORT_OPTIONS = [
  { value: 'name', label: 'Nombre (A-Z)' },
  { value: 'recent', label: 'Más recientes' },
  { value: 'price_asc', label: 'Menor precio' },
  { value: 'price_desc', label: 'Mayor precio' }
]

// parsePrice acepta formato es-AR ("1.500,50") y punto decimal: lo que no
// sea un número >= 0 se ignora (el backend también descarta bounds inválidos).
function parsePrice(value) {
  const raw = String(value || '').trim().replace(/\s/g, '')
  if (!raw) return ''
  const normalized = raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw
  const n = Number(normalized)
  return Number.isFinite(n) && n >= 0 ? n : ''
}

const queryId = (v) => (/^\d+$/.test(String(v || '')) ? Number(v) : null)

export function useStoreCatalog({ pageSize = 12 } = {}) {
  const ctx = inject('storePage')
  const { slug, ui, custom, shopName, pageTemplate, hasDesignAdvanced, loadPublicCatalog } = ctx
  const route = useRoute()
  const router = useRouter()
  const year = new Date().getFullYear()
  const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))

  // Catálogo opcional: si el dueño lo apagó, esta página no existe.
  watch(() => custom.value.show_catalog, (v) => {
    if (v === false) router.replace(homeTo.value)
  }, { immediate: true })

  watch(() => route.query.q, (q) => {
    const next = typeof q === 'string' ? q : ''
    if (next !== ui.search) ui.search = next
  }, { immediate: true })

  const catalog = ref({ categories: [], brands: [], products: [] })
  const catalogStatus = ref('idle') // idle | loading | success | error
  const activeCategory = ref(queryId(route.query.category))
  const activeBrand = ref(queryId(route.query.brand))
  const priceMin = ref('')
  const priceMax = ref('')
  const sort = ref(SORTS.includes(route.query.sort) ? route.query.sort : 'name')
  let searchTimer = null

  const visibleCount = ref(pageSize)
  const visibleProducts = computed(() => catalog.value.products.slice(0, visibleCount.value))
  const hasMoreProducts = computed(() => catalog.value.products.length > visibleCount.value)
  const showMore = () => { visibleCount.value += pageSize }

  // Miniatura por categoría (primer producto con foto). Se acumula entre
  // cargas para que filtrar no deje a las demás categorías sin imagen.
  const catThumbs = reactive({})

  async function loadCatalog() {
    visibleCount.value = pageSize
    catalogStatus.value = 'loading'
    try {
      let min = parsePrice(priceMin.value)
      let max = parsePrice(priceMax.value)
      if (min !== '' && max !== '' && min > max) [min, max] = [max, min]
      catalog.value = await loadPublicCatalog({
        q: ui.search.trim(),
        category: activeCategory.value || '',
        brand: activeBrand.value || '',
        min_price: min,
        max_price: max,
        sort: sort.value
      })
      catalog.value.products.forEach((p) => {
        if (p.category && p.image && !catThumbs[p.category]) catThumbs[p.category] = p.image
      })
      catalogStatus.value = 'success'
    } catch {
      catalogStatus.value = 'error'
    }
  }

  watch(() => ui.search, () => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(loadCatalog, 300)
  })
  watch([priceMin, priceMax], () => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(loadCatalog, 400)
  })
  watch(sort, loadCatalog)

  function pickCategory(id) {
    activeCategory.value = activeCategory.value === id ? null : id
    loadCatalog()
  }
  function pickBrand(id) {
    activeBrand.value = activeBrand.value === id ? null : id
    loadCatalog()
  }
  function clearFilters() {
    activeCategory.value = null
    activeBrand.value = null
    ui.search = ''
    priceMin.value = ''
    priceMax.value = ''
    loadCatalog()
  }
  function clearPrice() { priceMin.value = ''; priceMax.value = '' }

  const hasPriceFilter = computed(() => parsePrice(priceMin.value) !== '' || parsePrice(priceMax.value) !== '')
  const priceRangeLabel = computed(() => {
    const min = parsePrice(priceMin.value)
    const max = parsePrice(priceMax.value)
    if (min !== '' && max !== '') return `${formatARS(min)} – ${formatARS(max)}`
    if (min !== '') return `Desde ${formatARS(min)}`
    return `Hasta ${formatARS(max)}`
  })
  const hasFilters = computed(() => Boolean(activeCategory.value || activeBrand.value || ui.search || hasPriceFilter.value))
  const hasCatalogNav = computed(() => Boolean(catalog.value.categories.length || catalog.value.brands.length))
  const activeCategoryName = computed(() => catalog.value.categories.find((c) => c.id === activeCategory.value)?.name)
  const activeBrandName = computed(() => catalog.value.brands.find((b) => b.id === activeBrand.value)?.name)
  const activeFilterCount = computed(() => [activeCategory.value, activeBrand.value, ui.search.trim(), hasPriceFilter.value].filter(Boolean).length)
  const total = computed(() => catalog.value.products.length)
  const productCount = computed(() => {
    const n = total.value
    const base = `${n} ${n === 1 ? 'producto' : 'productos'}`
    return hasFilters.value ? `${base}, ${activeFilterCount.value} ${activeFilterCount.value === 1 ? 'filtro' : 'filtros'}` : base
  })
  const brandNameOf = (p) => catalog.value.brands.find((b) => b.id === p.brand)?.name || ''
  const categoryNameOf = (p) => catalog.value.categories.find((c) => c.id === p.category)?.name || ''
  const offerCount = computed(() => catalog.value.products.filter((p) => productOffer(p) != null).length)
  const shownLabel = computed(() => `Mostrando ${Math.min(visibleCount.value, total.value)} de ${total.value}`)
  const shownPct = computed(() => `${Math.round((Math.min(visibleCount.value, total.value) / Math.max(1, total.value)) * 100)}%`)

  const productTo = (p) => ({
    name: 'store-product',
    params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id }
  })
  const openProduct = (p) => router.push(productTo(p))

  const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
  const askUrl = (p) => (whatsappUrl.value ? `${whatsappUrl.value}?text=${encodeURIComponent(`Hola! Quiero consultar por "${p.name}"`)}` : '')

  onMounted(() => { if (custom.value.show_catalog !== false) loadCatalog() })
  onBeforeUnmount(() => clearTimeout(searchTimer))

  return {
    ctx, slug, ui, custom, shopName, pageTemplate, hasDesignAdvanced, year, homeTo,
    catalog, catalogStatus, loadCatalog,
    activeCategory, activeBrand, priceMin, priceMax, sort,
    visibleCount, visibleProducts, hasMoreProducts, showMore,
    catThumbs, pickCategory, pickBrand, clearFilters, clearPrice,
    hasPriceFilter, priceRangeLabel, hasFilters, hasCatalogNav,
    activeCategoryName, activeBrandName, activeFilterCount, total, productCount,
    brandNameOf, categoryNameOf, offerCount, shownLabel, shownPct,
    productTo, openProduct, whatsappUrl, askUrl
  }
}
