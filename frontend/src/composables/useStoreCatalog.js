import { ref, reactive, computed, watch, inject, provide, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeHostSlug } from '../config/env.js'
import { formatARS } from '../api/billing.api.js'
import { productOffer } from '../api/catalog.api.js'

// Estado y lógica compartidos por todas las páginas de catálogo de la web
// pública (/<slug>/catalogo): búsqueda de texto (compartida con el buscador
// del header por `ui.search`), taxonomías multi-selección, facetas por
// atributo (Talle, Color...), banderas oferta/novedades, rango de precios,
// orden, tags de filtros activos y paginado por "ver más". Cada diseño
// (Clásico, Perspectiva, Dúo, ...) solo pone su propia presentación encima
// de este estado — el panel de atributos lo monta CatalogFacets, que llama
// al mismo composable y recibe la instancia ya creada por la página.
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

// ?category=1,2 / ?brand=3,4 — lista de ids numéricos desde la query.
const queryIds = (v) => String(v || '').split(',').map((x) => Number(x.trim())).filter((n) => Number.isInteger(n) && n > 0)

// ?features={"Talle":["M"]} — dict {atributo: [valores]}; JSON inválido cae a {}.
function parseFeatureQuery(raw) {
  try {
    const obj = JSON.parse(typeof raw === 'string' ? raw : '')
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return {}
    return Object.fromEntries(
      Object.entries(obj)
        .map(([k, v]) => [String(k).slice(0, 40), [].concat(v).map(String).map((s) => s.slice(0, 120)).filter(Boolean)])
        .filter(([, v]) => v.length)
    )
  } catch { return {} }
}

export function useStoreCatalog({ pageSize = 12 } = {}) {
  // La página de catálogo crea el estado una vez y lo provee a sus hijos:
  // CatalogFacets (y cualquier panel de filtros) recibe la misma instancia
  // por inject. Se ata a la instancia del componente (no al ctx del layout),
  // así los watchers y el load onMounted mueren/renacen con la página.
  const shared = inject('storeCatalog', null)
  if (shared) return shared
  const ctx = inject('storePage')
  const state = buildCatalogState(ctx, { pageSize })
  provide('storeCatalog', state)
  return state
}

function buildCatalogState(ctx, { pageSize }) {
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

  const catalog = ref({ categories: [], brands: [], products: [], facets: [], promotions: [] })
  const catalogStatus = ref('idle') // idle | loading | success | error
  const activeCategories = ref(queryIds(route.query.category))
  const activeBrands = ref(queryIds(route.query.brand))
  // Atributos dinámicos (?features=): {nombre -> [valores]} — dentro de un
  // grupo los valores suman (OR), entre grupos se exigen (AND).
  const featureFilters = reactive(parseFeatureQuery(route.query.features))
  const onlyOffer = ref(route.query.offer === '1')
  const onlyNew = ref(route.query.new === '1')
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
        category: activeCategories.value,
        brand: activeBrands.value,
        features: featureFilters,
        offer: onlyOffer.value,
        is_new: onlyNew.value,
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

  const toggleIn = (list, id) => {
    if (id == null) return
    const i = list.value.indexOf(id)
    if (i === -1) list.value.push(id)
    else list.value.splice(i, 1)
    loadCatalog()
  }
  const pickCategory = (id) => toggleIn(activeCategories, id)
  const pickBrand = (id) => toggleIn(activeBrands, id)
  function pickFeature(name, value) {
    const list = featureFilters[name] || []
    const i = list.indexOf(value)
    if (i === -1) list.push(value)
    else list.splice(i, 1)
    if (list.length) featureFilters[name] = list
    else delete featureFilters[name]
    loadCatalog()
  }
  const toggleOffer = () => { onlyOffer.value = !onlyOffer.value; loadCatalog() }
  const toggleNew = () => { onlyNew.value = !onlyNew.value; loadCatalog() }
  function clearFilters() {
    activeCategories.value = []
    activeBrands.value = []
    Object.keys(featureFilters).forEach((k) => delete featureFilters[k])
    onlyOffer.value = false
    onlyNew.value = false
    ui.search = ''
    priceMin.value = ''
    priceMax.value = ''
    loadCatalog()
  }
  function clearPrice() { priceMin.value = ''; priceMax.value = '' }
  // "Todas"/"Todo" de las barras rápidas: limpia solo su taxonomía.
  function clearCategories() { if (activeCategories.value.length) { activeCategories.value = []; loadCatalog() } }
  function clearBrands() { if (activeBrands.value.length) { activeBrands.value = []; loadCatalog() } }

  const hasPriceFilter = computed(() => parsePrice(priceMin.value) !== '' || parsePrice(priceMax.value) !== '')
  const priceRangeLabel = computed(() => {
    const min = parsePrice(priceMin.value)
    const max = parsePrice(priceMax.value)
    if (min !== '' && max !== '') return `${formatARS(min)} – ${formatARS(max)}`
    if (min !== '') return `Desde ${formatARS(min)}`
    return `Hasta ${formatARS(max)}`
  })
  const featureFilterCount = computed(() => Object.values(featureFilters).reduce((n, v) => n + v.length, 0))
  const hasFilters = computed(() => Boolean(
    activeCategories.value.length || activeBrands.value.length || featureFilterCount.value
    || onlyOffer.value || onlyNew.value || ui.search || hasPriceFilter.value
  ))
  const hasCatalogNav = computed(() => Boolean(catalog.value.categories.length || catalog.value.brands.length))
  const categoryNameOf = (p) => catalog.value.categories.find((c) => c.id === p.category)?.name || ''
  const brandNameOf = (p) => catalog.value.brands.find((b) => b.id === p.brand)?.name || ''
  const activeCategoryNames = computed(() => catalog.value.categories.filter((c) => activeCategories.value.includes(c.id)).map((c) => c.name))
  const activeBrandNames = computed(() => catalog.value.brands.filter((b) => activeBrands.value.includes(b.id)).map((b) => b.name))
  // Compat con plantillas que muestran el filtro de taxonomía como texto
  // (breadcrumbs, encabezados): los seleccionados viajan unidos.
  const activeCategoryName = computed(() => activeCategoryNames.value.join(' · ') || '')
  const activeBrandName = computed(() => activeBrandNames.value.join(' · ') || '')
  const activeFilterCount = computed(() =>
    activeCategories.value.length + activeBrands.value.length + featureFilterCount.value
    + (onlyOffer.value ? 1 : 0) + (onlyNew.value ? 1 : 0)
    + (ui.search.trim() ? 1 : 0) + (hasPriceFilter.value ? 1 : 0)
  )
  const total = computed(() => catalog.value.products.length)
  const productCount = computed(() => {
    const n = total.value
    const base = `${n} ${n === 1 ? 'producto' : 'productos'}`
    return hasFilters.value ? `${base}, ${activeFilterCount.value} ${activeFilterCount.value === 1 ? 'filtro' : 'filtros'}` : base
  })
  const offerCount = computed(() => catalog.value.products.filter((p) => productOffer(p) != null).length)
  const shownLabel = computed(() => `Mostrando ${Math.min(visibleCount.value, total.value)} de ${total.value}`)
  const shownPct = computed(() => `${Math.round((Math.min(visibleCount.value, total.value) / Math.max(1, total.value)) * 100)}%`)

  // Facetas y topes del panel de filtros (calculados en el backend sobre
  // todo el catálogo activo — los conteos no cambian al filtrar).
  const facets = computed(() => catalog.value.facets || [])
  const priceCeiling = computed(() => Math.ceil(Number(catalog.value.price_max || 0)))
  const offerTotal = computed(() => Number(catalog.value.offer_count || 0))
  const newTotal = computed(() => Number(catalog.value.new_count || 0))

  // Tags removibles de los filtros activos (una por valor elegido): cada
  // plantilla las dibuja con su propio estilo sobre la misma lista.
  const activeTags = computed(() => {
    const tags = []
    if (ui.search.trim()) tags.push({ key: 'q', label: `“${ui.search.trim()}”`, remove: () => { ui.search = '' } })
    activeCategories.value.forEach((id) => {
      const name = catalog.value.categories.find((c) => c.id === id)?.name || `#${id}`
      tags.push({ key: `c${id}`, label: name, remove: () => pickCategory(id) })
    })
    activeBrands.value.forEach((id) => {
      const name = catalog.value.brands.find((b) => b.id === id)?.name || `#${id}`
      tags.push({ key: `b${id}`, label: name, remove: () => pickBrand(id) })
    })
    Object.entries(featureFilters).forEach(([name, values]) => {
      values.forEach((value) => tags.push({ key: `f-${name}-${value}`, label: `${name}: ${value}`, remove: () => pickFeature(name, value) }))
    })
    if (onlyOffer.value) tags.push({ key: 'offer', label: 'En oferta', remove: toggleOffer })
    if (onlyNew.value) tags.push({ key: 'new', label: 'Novedades', remove: toggleNew })
    if (hasPriceFilter.value) tags.push({ key: 'price', label: priceRangeLabel.value, remove: clearPrice })
    return tags
  })

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
    activeCategories, activeBrands, featureFilters, onlyOffer, onlyNew, priceMin, priceMax, sort,
    visibleCount, visibleProducts, hasMoreProducts, showMore,
    catThumbs, pickCategory, pickBrand, pickFeature, toggleOffer, toggleNew, clearFilters, clearPrice, clearCategories, clearBrands,
    hasPriceFilter, priceRangeLabel, hasFilters, hasCatalogNav,
    activeCategoryName, activeBrandName, activeCategoryNames, activeBrandNames, activeFilterCount,
    total, productCount, facets, priceCeiling, offerTotal, newTotal, activeTags,
    brandNameOf, categoryNameOf, offerCount, shownLabel, shownPct,
    productTo, openProduct, whatsappUrl, askUrl
  }
}
