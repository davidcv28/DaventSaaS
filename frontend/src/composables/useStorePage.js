import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../config/env.js'
import { formatARS } from '../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../api/catalog.api.js'
import { openStatus } from '../utils/storeHours.js'

// Base compartida de las portadas/fichas por familia (atelier, circuit,
// mercado, studio y variantes): inyecta el contexto `storePage` del layout,
// trae la vitrina del catálogo una sola vez y centraliza los builders de
// WhatsApp, el "abierto ahora", el pool de imágenes y los helpers de
// producto — cada familia solo pone su esqueleto encima, sin duplicar
// lógica.
export function useStorePage() {
  const ctx = inject('storePage')
  const router = useRouter()
  const {
    slug, store, status, custom, shopName, nameFont, initial, location,
    hasDesignAdvanced, pageTemplate, hasAbout, showGallery, showContact,
    showCatalog, showServices, siteTemplates, loadPublicCatalog
  } = ctx

  const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
  const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
  const servicesTo = computed(() => ({ path: storeHostSlug ? '/servicios' : `/${slug.value}/servicios` }))
  const productTo = (p) => ({
    name: 'store-product',
    params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id }
  })
  const openProduct = (p) => router.push(productTo(p))

  // ===== Identidad =====
  const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
  const heroTitleIsName = computed(() => !custom.value.headline?.trim())
  const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))
  const carousel = computed(() => (hasDesignAdvanced.value ? (custom.value.carousel || []) : []))
  const gallery = computed(() => (showGallery.value ? (custom.value.gallery || []) : []))
  const socials = computed(() => [
    { key: 'instagram', label: 'Instagram', url: custom.value.instagram && `https://instagram.com/${custom.value.instagram}` },
    { key: 'tiktok', label: 'TikTok', url: custom.value.tiktok && `https://tiktok.com/@${custom.value.tiktok}` },
    { key: 'facebook', label: 'Facebook', url: custom.value.facebook && `https://facebook.com/${custom.value.facebook}` }
  ].filter((s) => s.url))
  const year = new Date().getFullYear()
  // Colección corta para el sello vertical ("SS/26" estilo temporada).
  const collectionTag = computed(() => {
    const month = new Date().getMonth() + 1
    const season = month >= 9 || month <= 2 ? 'SS' : 'FW'
    return `${season}/${String(year).slice(2)}`
  })

  // ===== "Abierto ahora" (reloj de un minuto) =====
  const now = ref(new Date())
  let clock = null
  const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))

  // ===== Catálogo / vitrina =====
  const catalog = ref({ categories: [], brands: [], products: [] })
  const catalogStatus = ref('idle') // idle | loading | success | error
  async function loadCatalog(params = { sort: 'recent' }) {
    if (!showCatalog.value) return
    catalogStatus.value = 'loading'
    try {
      catalog.value = await loadPublicCatalog(params)
      catalogStatus.value = 'success'
    } catch {
      catalog.value = { categories: [], brands: [], products: [] }
      catalogStatus.value = 'error'
    }
  }
  const products = computed(() => catalog.value.products || [])
  const categories = computed(() => catalog.value.categories || [])
  const brands = computed(() => catalog.value.brands || [])
  const catOf = (p) => categories.value.find((c) => c.id === p?.category)?.name || ''
  const brandOf = (p) => brands.value.find((b) => b.id === p?.brand)?.name || ''
  const deptTo = (id) => ({ ...catalogTo.value, query: { category: id } })
  // Departamentos reales: categorías con productos + miniatura del primero con foto.
  const departments = computed(() => categories.value
    .map((c) => {
      const items = products.value.filter((p) => p.category === c.id)
      return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
    })
    .filter((d) => d.count > 0))
  const offerCount = computed(() => products.value.filter((p) => productOffer(p) != null).length)

  // Pool de imágenes reales de la tienda (portada → carrusel → galería →
  // fotos de producto), sin repetir — alimenta héroes y pliegos.
  const imagePool = computed(() => {
    const seen = new Set()
    return [cover.value, ...carousel.value.map((i) => i.url), ...gallery.value.map((g) => g.url), ...products.value.map((p) => p.image)]
      .filter((u) => { if (!u || seen.has(u)) return false; seen.add(u); return true })
  })
  const heroImage = computed(() => imagePool.value[0] || '')

  // ===== WhatsApp =====
  const waNumber = computed(() => String(custom.value.whatsapp || '').replace(/\D/g, ''))
  const waBase = computed(() => (waNumber.value ? `https://wa.me/${waNumber.value}` : ''))
  // Mensaje precargado: saludo + líneas arbitrarias (producto, talle,
  // cantidad, nota). La web nunca persiste el pedido — solo abre wa.me.
  const waLink = (lines) => {
    if (!waBase.value) return ''
    const text = [`Hola ${shopName.value},`, ...[].concat(lines).filter(Boolean)].join('\n')
    return `${waBase.value}?text=${encodeURIComponent(text)}`
  }
  const waProduct = (p, extra = []) => waLink([`me interesa "${p.name}" (${formatARS(effectivePrice(p))}) que vi en tu web.`, ...extra])
  const waGeneral = computed(() => waLink([custom.value.description?.trim() ? 'los vi en tu web y quiero consultar.' : 'quiero hacer una consulta.']))

  // ===== Producto =====
  // Características ordenadas: primero las del feature_schema de su
  // categoría (orden del dueño), después las libres.
  const featureRows = (p) => {
    if (!p?.features) return []
    const schema = categories.value.find((c) => c.id === p.category)?.feature_schema || []
    const order = new Map(schema.map((name, i) => [name.toLowerCase(), i]))
    return Object.entries(p.features).sort(
      (a, b) => (order.get(a[0].toLowerCase()) ?? schema.length) - (order.get(b[0].toLowerCase()) ?? schema.length)
    )
  }
  // Valores de un atributo como lista ("Talle": "S, M, L" -> ['S','M','L']).
  const featureValues = (p, ...names) => {
    const rows = featureRows(p)
    const hit = rows.find(([k]) => names.some((n) => k.toLowerCase().includes(n)))
    return hit ? String(hit[1]).split(/[,\/·]/).map((s) => s.trim()).filter(Boolean) : []
  }
  // Relacionados: misma categoría primero, misma marca después, resto al final.
  const related = (p, limit = 6) => {
    if (!p) return []
    const rest = products.value.filter((x) => x.id !== p.id)
    const sameCat = rest.filter((x) => x.category && x.category === p.category)
    const sameBrand = rest.filter((x) => x.brand && x.brand === p.brand && !sameCat.includes(x))
    const others = rest.filter((x) => !sameCat.includes(x) && !sameBrand.includes(x))
    return [...sameCat, ...sameBrand, ...others].slice(0, limit)
  }

  // ===== Secciones de marketing (datos reales del dueño) =====
  const listOf = (v) => (Array.isArray(v) ? v : [])
  const stats = computed(() => (custom.value.show_stats !== false ? listOf(custom.value.stats) : []))
  const testimonials = computed(() => (custom.value.show_testimonials !== false ? listOf(custom.value.testimonials) : []))
  const faqs = computed(() => (custom.value.show_faq !== false ? listOf(custom.value.faqs) : []))
  const aboutSpecialties = computed(() => String(custom.value.about_specialties || '')
    .split(',').map((s) => s.trim()).filter(Boolean).slice(0, 12))
  const serviceItems = computed(() => (status.value === 'success' ? store.value?.service_items || [] : []))
  const hours = computed(() => (custom.value.show_hours !== false ? listOf(custom.value.hours) : []))

  onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
  onBeforeUnmount(() => clearInterval(clock))

  return {
    ctx, slug, store, status, custom, shopName, nameFont, initial, location,
    hasDesignAdvanced, pageTemplate, hasAbout, showGallery, showContact,
    showCatalog, showServices, siteTemplates,
    homeTo, catalogTo, servicesTo, productTo, openProduct,
    heroTitle, heroTitleIsName, cover, carousel, gallery, socials, year, collectionTag,
    now, openNow,
    catalog, catalogStatus, loadCatalog, products, categories, brands,
    catOf, brandOf, deptTo, departments, offerCount, imagePool, heroImage,
    waNumber, waBase, waLink, waProduct, waGeneral,
    featureRows, featureValues, related,
    stats, testimonials, faqs, aboutSpecialties, serviceItems, hours,
    formatARS, productOffer, effectivePrice, offerPct, isNewProduct
  }
}
