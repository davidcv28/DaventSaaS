<script setup>
import { ref, computed, watch, watchEffect, inject, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeHostSlug } from '../../config/env.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import ProductStars from '../../components/ProductStars.vue'
import { vReveal } from '../../directives/reveal.js'

// Página de catálogo de la web pública (/<slug>/catalogo): navegación por
// categorías/marcas, buscador, filtro de precios y orden. Cada tarjeta
// abre la ficha completa del producto (/<slug>/producto/<id>, estilo
// marketplace). La tienda la resuelve StorePublicLayout
// (inject 'storePage'); el buscador del header y el burger comparten el
// estado `ui` provisto por el layout.
const ctx = inject('storePage')
const { slug, ui, custom, hasDesignAdvanced, shopName, loadPublicCatalog } = ctx
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const route = useRoute()
const router = useRouter()

// Catálogo opcional: si el dueño lo apagó la web queda como vidriera y esta
// página no existe (el endpoint público también devuelve 404). Se resuelve
// async en el layout, así que se espera a que customization llegue.
watch(() => custom.value.show_catalog, (v) => {
  if (v === false) router.replace(homeTo.value)
}, { immediate: true })

// La búsqueda también puede llegar por URL (?q=) — alimenta el buscador
// compartido con el header.
watch(() => route.query.q, (q) => {
  const next = typeof q === 'string' ? q : ''
  if (next !== ui.search) ui.search = next
}, { immediate: true })

const catalog = ref({ categories: [], brands: [], products: [] })
const catalogStatus = ref('idle') // idle | loading | success | error

// --- Filtros de la tienda (el texto de búsqueda vive en ui.search para
// compartirlo con el buscador del header) ---
// Los accesos de la portada (categoría, marca, orden) llegan por query.
const queryId = (v) => (/^\d+$/.test(String(v || '')) ? Number(v) : null)
const SORTS = ['name', 'recent', 'price_asc', 'price_desc']
const activeCategory = ref(queryId(route.query.category))
const activeBrand = ref(queryId(route.query.brand))
const priceMin = ref('')
const priceMax = ref('')
const sort = ref(SORTS.includes(route.query.sort) ? route.query.sort : 'name')
let searchTimer = null

// parsePrice acepta formato es-AR ("1.500,50") y punto decimal: lo que no
// sea un número >= 0 se ignora (el backend también descarta bounds inválidos).
function parsePrice(value) {
  const raw = String(value || '').trim().replace(/\s/g, '')
  if (!raw) return ''
  const normalized = raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw
  const n = Number(normalized)
  return Number.isFinite(n) && n >= 0 ? n : ''
}

const PAGE_SIZE = 12
const visibleCount = ref(PAGE_SIZE)
const visibleProducts = computed(() => catalog.value.products.slice(0, visibleCount.value))
const hasMoreProducts = computed(() => catalog.value.products.length > visibleCount.value)
const showMore = () => { visibleCount.value += PAGE_SIZE }

async function loadCatalog() {
  visibleCount.value = PAGE_SIZE
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
    catalogStatus.value = 'success'
  } catch {
    catalogStatus.value = 'error'
  }
}

watch(() => ui.search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadCatalog, 300)
})
// El rango de precios también es debounceado (el visitante escribe a su ritmo);
// el orden recarga al instante porque el select ya entrega el valor final.
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

// El orden no entra en hasFilters ni se resetea con "Limpiar": ordenar no
// filtra resultados y el visitante espera que se mantenga.
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
// El burger del header solo aparece cuando hay categorías o marcas.
watchEffect(() => { ui.hasCatalogNav = hasCatalogNav.value })
const activeCategoryName = computed(() => catalog.value.categories.find((c) => c.id === activeCategory.value)?.name)
const activeBrandName = computed(() => catalog.value.brands.find((b) => b.id === activeBrand.value)?.name)
const activeFilterCount = computed(() => [activeCategory.value, activeBrand.value, ui.search.trim(), hasPriceFilter.value].filter(Boolean).length)
const productCount = computed(() => {
  const n = catalog.value.products.length
  const base = `${n} ${n === 1 ? 'producto' : 'productos'}`
  return hasFilters.value ? `${base}, ${activeFilterCount.value} ${activeFilterCount.value === 1 ? 'filtro' : 'filtros'}` : base
})

const brandNameOf = (p) => catalog.value.brands.find((b) => b.id === p.brand)?.name || ''
const categoryNameOf = (p) => catalog.value.categories.find((c) => c.id === p.category)?.name || ''
const shownLabel = computed(() => `Mostrando ${Math.min(visibleCount.value, catalog.value.products.length)} de ${catalog.value.products.length}`)
const shownPct = computed(() => `${Math.round((Math.min(visibleCount.value, catalog.value.products.length) / Math.max(1, catalog.value.products.length)) * 100)}%`)

// La tarjeta entera navega a la ficha del producto (página aparte, como
// en un marketplace): en dominio de plataforma lleva el slug, en
// subdominio de tienda la ruta es /producto/<id> sin params extra.
const productTo = (p) => ({
  name: 'store-product',
  params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id }
})
const openProduct = (p) => router.push(productTo(p))

const onKey = (e) => {
  if (e.key === 'Escape') ui.menuOpen = false
}

// --- Portada: carrusel de destacados (premium), abre la página del
// catálogo como vitrina del negocio ---
const carousel = computed(() => custom.value.carousel || [])
const slide = ref(0)
// slideEpoch fuerza el remount de la barra de progreso cada vez que el
// temporizador se reinicia (auto-avance, flechas, dots, hover out, drag).
const slideEpoch = ref(0)
let slideTimer = null
const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

function goSlide(index) {
  const total = carousel.value.length
  if (!total) return
  slide.value = ((index % total) + total) % total
  restartSlideTimer()
}
function pauseSlideTimer() {
  clearInterval(slideTimer)
  slideTimer = null
}
function restartSlideTimer() {
  pauseSlideTimer()
  slideEpoch.value += 1
  if (carousel.value.length > 1 && !reduceMotion) {
    slideTimer = setInterval(() => { slide.value = (slide.value + 1) % carousel.value.length }, 5000)
  }
}

// Arrastre: el track sigue el puntero y al soltar hace snap a la imagen
// siguiente/anterior si se supera el umbral. Sirve táctil y mouse.
const carouselEl = ref(null)
const dragging = ref(false)
const dragX = ref(0)
let dragStartX = 0
const trackStyle = computed(() => ({
  transform: `translateX(calc(-${slide.value * 100}% + ${dragX.value}px))`,
  transition: dragging.value ? 'none' : ''
}))
function onSlideDragStart(event) {
  if (carousel.value.length < 2 || event.target.closest('button')) return
  dragging.value = true
  dragStartX = event.clientX
  dragX.value = 0
  event.currentTarget.setPointerCapture?.(event.pointerId)
  pauseSlideTimer()
}
function onSlideDragMove(event) {
  if (!dragging.value) return
  dragX.value = event.clientX - dragStartX
}
function onSlideDragEnd() {
  if (!dragging.value) return
  dragging.value = false
  const width = carouselEl.value?.clientWidth || 1
  const threshold = Math.min(80, width * 0.15)
  const total = carousel.value.length
  if (dragX.value <= -threshold) slide.value = (slide.value + 1) % total
  else if (dragX.value >= threshold) slide.value = (slide.value - 1 + total) % total
  dragX.value = 0
  restartSlideTimer()
}

// Foco de luz que sigue al puntero sobre las tarjetas (desactivado con
// prefers-reduced-motion).
function onCardMove(event) {
  const card = event.target.closest?.('.sp-card')
  if (!card || reduceMotion) return
  const rect = card.getBoundingClientRect()
  card.style.setProperty('--mx', `${event.clientX - rect.left}px`)
  card.style.setProperty('--my', `${event.clientY - rect.top}px`)
}

onMounted(() => {
  restartSlideTimer()
  if (custom.value.show_catalog !== false) loadCatalog()
  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  clearInterval(slideTimer)
  ui.menuOpen = false
  ui.hasCatalogNav = false
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
<div class="sp-page-root">
  <div class="sp-hero-band sp-cat-hero">
    <div class="sp-hero-decor" aria-hidden="true">
      <span class="sp-orb o1"></span>
      <span class="sp-orb o2"></span>
      <span class="sp-float f1"><AppIcon name="package" :size="24" /></span>
      <span class="sp-float f3"><AppIcon name="tag" :size="22" /></span>
      <span class="sp-float f4"><AppIcon name="search" :size="20" /></span>
    </div>
    <div class="sp-container sp-cat-hero-inner">
      <nav v-reveal class="sp-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="14" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <div v-reveal="80" class="sp-cat-head">
        <span class="sp-cat-head-icon" aria-hidden="true"><AppIcon name="package" :size="26" /></span>
        <div>
          <h1 class="sp-cat-title">Catálogo</h1>
          <p class="sp-cat-sub">Explorá todo lo que tiene {{ shopName }} para ofrecerte.</p>
        </div>
      </div>
      <ul v-reveal="160" class="sp-cat-stats">
        <li><AppIcon name="package" :size="14" /> <strong>{{ catalog.products.length }}</strong> {{ catalog.products.length === 1 ? 'producto' : 'productos' }}</li>
        <li v-if="catalog.categories.length"><AppIcon name="layout-grid" :size="14" /> <strong>{{ catalog.categories.length }}</strong> {{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</li>
        <li v-if="catalog.brands.length"><AppIcon name="tag" :size="14" /> <strong>{{ catalog.brands.length }}</strong> {{ catalog.brands.length === 1 ? 'marca' : 'marcas' }}</li>
      </ul>
    </div>
  </div>

  <main class="sp-container sp-main">
    <!-- Portada: carrusel de destacados (premium), vitrina sobre el catálogo.
         Tienda Pro no lo repite: la portada ya es el banner de la home y acá
         el catálogo tiene que entrar directo, sin una franja de imágenes. -->
    <div v-if="hasDesignAdvanced && carousel.length" class="sp-catalog-banner">
      <div v-reveal class="sp-banner">
        <div ref="carouselEl" class="sp-carousel" :class="{ dragging }" @mouseenter="pauseSlideTimer" @mouseleave="restartSlideTimer" @focusin="pauseSlideTimer" @focusout="restartSlideTimer" @pointerdown="onSlideDragStart" @pointermove="onSlideDragMove" @pointerup="onSlideDragEnd" @pointercancel="onSlideDragEnd">
          <div class="sp-carousel-track" :style="trackStyle">
            <img v-for="(img, i) in carousel" :key="img.id" class="sp-carousel-img" :class="{ active: i === slide }" :src="img.url" alt="" draggable="false" />
          </div>
          <template v-if="carousel.length > 1">
            <button type="button" class="sp-carousel-arrow prev" aria-label="Imagen anterior" @click="goSlide(slide - 1)">
              <AppIcon name="chevron-left" :size="20" />
            </button>
            <button type="button" class="sp-carousel-arrow next" aria-label="Imagen siguiente" @click="goSlide(slide + 1)">
              <AppIcon name="chevron-right" :size="20" />
            </button>
            <div class="sp-carousel-dots" role="group" aria-label="Imágenes del carrusel">
              <button
                v-for="(img, i) in carousel" :key="img.id" type="button"
                class="sp-carousel-dot" :class="{ active: i === slide }"
                :aria-label="`Ir a la imagen ${i + 1}`" :aria-current="i === slide"
                @click="goSlide(i)"
              ></button>
            </div>
            <span v-if="!reduceMotion" :key="`${slide}-${slideEpoch}`" class="sp-slide-progress" aria-hidden="true"></span>
          </template>
        </div>
      </div>
    </div>

    <div class="sp-layout" :class="{ 'has-nav': hasCatalogNav }">
      <div v-if="hasCatalogNav" class="sp-overlay" :class="{ open: ui.menuOpen }" aria-hidden="true" @click="ui.menuOpen = false"></div>
      <aside v-if="hasCatalogNav" id="sp-drawer" class="sp-drawer" :class="{ open: ui.menuOpen }" aria-label="Categorías y marcas">
        <div class="sp-drawer-head">
          <strong>Explorar</strong>
          <button type="button" class="sp-drawer-close" aria-label="Cerrar menú" @click="ui.menuOpen = false">
            <AppIcon name="x" :size="18" />
          </button>
        </div>
        <nav v-if="catalog.categories.length" class="sp-nav-group" aria-label="Categorías">
          <p class="sp-nav-heading">Categorías</p>
          <button
            v-for="c in catalog.categories" :key="`c-${c.id}`" type="button"
            class="sp-nav-item" :class="{ active: activeCategory === c.id }"
            :aria-pressed="activeCategory === c.id"
            @click="pickCategory(c.id); ui.menuOpen = false"
          >
            <AppIcon name="layout-grid" :size="15" /> <span>{{ c.name }}</span>
          </button>
        </nav>
        <nav v-if="catalog.brands.length" class="sp-nav-group" aria-label="Marcas">
          <p class="sp-nav-heading">Marcas</p>
          <button
            v-for="b in catalog.brands" :key="`b-${b.id}`" type="button"
            class="sp-nav-item" :class="{ active: activeBrand === b.id }"
            :aria-pressed="activeBrand === b.id"
            @click="pickBrand(b.id); ui.menuOpen = false"
          >
            <AppIcon name="tag" :size="15" /> <span>{{ b.name }}</span>
          </button>
        </nav>
        <button v-if="hasFilters" type="button" class="sp-nav-clear" @click="clearFilters(); ui.menuOpen = false">
          <AppIcon name="x" :size="14" /> Limpiar filtros
        </button>
      </aside>

      <section class="sp-catalog" aria-labelledby="sp-catalog-title">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <div v-if="catalog.categories.length" class="sp-quick" role="group" aria-label="Categorías rápidas">
          <button type="button" class="sp-quick-pill" :class="{ active: !activeCategory }" :aria-pressed="!activeCategory" @click="activeCategory && pickCategory(activeCategory)">Todas</button>
          <button
            v-for="c in catalog.categories" :key="`q-${c.id}`" type="button"
            class="sp-quick-pill" :class="{ active: activeCategory === c.id }" :aria-pressed="activeCategory === c.id"
            @click="pickCategory(c.id)"
          >{{ c.name }}</button>
        </div>
        <div v-reveal class="sp-toolbar">
          <div class="sp-toolbar-title">
            <h2 id="sp-catalog-title" class="sp-section-title">{{ hasFilters ? 'Resultados' : 'Todos los productos' }}</h2>
            <span v-if="catalogStatus === 'success'" class="sp-count" role="status" aria-live="polite">{{ productCount }}</span>
          </div>
          <label class="sp-search sp-search-inline">
            <AppIcon name="search" :size="16" aria-hidden="true" />
            <input v-model="ui.search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" @keydown.esc.stop="ui.search = ''" />
            <button v-if="ui.search" type="button" class="sp-search-clear" aria-label="Borrar búsqueda" @click="ui.search = ''"><AppIcon name="x" :size="14" /></button>
          </label>
        </div>

        <div v-reveal="60" class="sp-filters" role="group" aria-label="Filtros del catálogo">
          <div class="sp-field">
            <span class="sp-field-label">Precio</span>
            <div class="sp-price" role="group" aria-label="Filtrar por rango de precios">
              <span class="sp-currency" aria-hidden="true">$</span>
              <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mínimo" aria-label="Precio mínimo" />
              <span class="sp-price-sep" aria-hidden="true"></span>
              <span class="sp-currency" aria-hidden="true">$</span>
              <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máximo" aria-label="Precio máximo" />
            </div>
          </div>
          <div class="sp-field">
            <label class="sp-field-label" for="sp-sort-select">Ordenar por</label>
            <div class="sp-sort">
              <select id="sp-sort-select" v-model="sort">
                <option value="name">Nombre (A-Z)</option>
                <option value="recent">Más recientes</option>
                <option value="price_asc">Menor precio</option>
                <option value="price_desc">Mayor precio</option>
              </select>
              <AppIcon name="chevron-down" :size="14" class="sp-sort-caret" aria-hidden="true" />
            </div>
          </div>
        </div>

        <div v-if="hasFilters" class="sp-chips" aria-label="Filtros activos">
          <button v-if="ui.search.trim()" type="button" class="sp-chip" @click="ui.search = ''">
            &ldquo;{{ ui.search.trim() }}&rdquo; <AppIcon name="x" :size="12" />
          </button>
          <button v-if="activeCategoryName" type="button" class="sp-chip" @click="pickCategory(activeCategory)">
            {{ activeCategoryName }} <AppIcon name="x" :size="12" />
          </button>
          <button v-if="activeBrandName" type="button" class="sp-chip" @click="pickBrand(activeBrand)">
            {{ activeBrandName }} <AppIcon name="x" :size="12" />
          </button>
          <button v-if="hasPriceFilter" type="button" class="sp-chip" @click="priceMin = ''; priceMax = ''">
            {{ priceRangeLabel }} <AppIcon name="x" :size="12" />
          </button>
          <button type="button" class="sp-chip clear" @click="clearFilters">Limpiar</button>
        </div>

        <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="sp-grid" aria-busy="true">
          <div v-for="n in 8" :key="n" class="sp-card sp-skeleton" aria-hidden="true">
            <div class="sp-card-img"></div>
            <div class="sp-card-body"><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
          </div>
        </div>

        <div v-else-if="catalogStatus === 'error'" class="sp-empty">
          <span class="sp-empty-icon"><AppIcon name="circle-alert" :size="26" /></span>
          <strong>No pudimos cargar el catálogo</strong>
          <p>Revisá tu conexión e intentá de nuevo.</p>
          <button type="button" class="sp-btn ghost" @click="loadCatalog"><AppIcon name="refresh" :size="16" /> Reintentar</button>
        </div>

        <div v-else-if="catalog.products.length" class="sp-grid" :class="{ loading: catalogStatus === 'loading' }" @pointermove="onCardMove">
          <article
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 70"
            class="sp-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <div class="sp-card-img">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="sp-card-placeholder"><AppIcon name="package" :size="28" /></span>
              <span class="sp-card-quick" aria-hidden="true"><AppIcon name="eye" :size="15" /> Ver producto</span>
              <span v-if="isNewProduct(p)" class="sp-card-flag">Nuevo</span>
              <span v-if="productOffer(p) != null" class="sp-card-flag offer">-{{ offerPct(p) }}%</span>
            </div>
            <div class="sp-card-body">
              <p v-if="categoryNameOf(p) || brandNameOf(p)" class="sp-card-eyebrow">
                <span v-if="categoryNameOf(p)">{{ categoryNameOf(p) }}</span>
                <i v-if="categoryNameOf(p) && brandNameOf(p)" aria-hidden="true"></i>
                <span v-if="brandNameOf(p)">{{ brandNameOf(p) }}</span>
              </p>
              <h3 class="sp-card-name">{{ p.name }}</h3>
              <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" :size="12" />
              <p v-if="productDiscount(p)" class="sp-card-promo">
                <AppIcon name="tag" :size="12" aria-hidden="true" />
                {{ productDiscount(p).name }}<span v-if="offerEndsLabel(productDiscount(p))" class="sp-card-promo-ends"> · {{ offerEndsLabel(productDiscount(p)) }}</span>
              </p>
              <div class="sp-card-foot">
                <span class="sp-card-price"><s v-if="productOffer(p) != null" class="sp-price-old">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
                <span class="sp-card-go" aria-hidden="true">
                  Ver más <AppIcon name="arrow-right" :size="15" />
                </span>
              </div>
            </div>
          </article>
        </div>

        <div v-else class="sp-empty">
          <span class="sp-empty-icon"><AppIcon name="package" :size="26" /></span>
          <strong>{{ hasFilters ? 'No hay productos con esos filtros' : 'Todavía no hay productos publicados' }}</strong>
          <p>{{ hasFilters ? 'Probá con otra búsqueda o quitá los filtros.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
          <button v-if="hasFilters" type="button" class="sp-btn ghost" @click="clearFilters">Ver todo</button>
        </div>

        <div v-if="hasMoreProducts && catalogStatus !== 'error'" class="sp-more">
          <p class="sp-more-label">{{ shownLabel }}</p>
          <span class="sp-more-bar" aria-hidden="true"><span :style="{ width: shownPct }"></span></span>
          <button type="button" class="sp-btn" @click="showMore"><AppIcon name="plus" :size="16" /> Ver más productos</button>
        </div>
      </section>
    </div>
  </main>
</div>
</template>
