<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import TplProductCard from '../../components/store/TplProductCard.vue'
import { vReveal } from '../../directives/reveal.js'

// Página de catálogo de la web pública (/<slug>/catalogo): navegación por
// categorías/marcas multi-selección, facetas por atributo, buscador,
// filtro de precios y orden. Cada tarjeta abre la ficha completa del
// producto (/<slug>/producto/<id>, estilo marketplace). El estado lo da
// useStoreCatalog y los filtros los monta CatalogFilters (sidebar en
// desktop, bottom sheet en móvil) junto a la barra CatalogToolbar.
const {
  custom, hasDesignAdvanced, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore,
  clearFilters, hasFilters,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

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
})

onBeforeUnmount(() => {
  clearInterval(slideTimer)
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

    <div class="cf-body">
      <CatalogFilters />

      <section class="sp-catalog cf-main" aria-labelledby="sp-catalog-title">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <h2 id="sp-catalog-title" class="sp-section-title" v-reveal>{{ hasFilters ? 'Resultados' : 'Todos los productos' }}</h2>
        <CatalogToolbar />

        <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="sp-grid cv-skels" aria-busy="true">
          <span v-for="n in 8" :key="n" class="cv-skel" aria-hidden="true"></span>
        </div>

        <div v-else-if="catalogStatus === 'error'" class="sp-empty">
          <span class="sp-empty-icon"><AppIcon name="circle-alert" :size="26" /></span>
          <strong>No pudimos cargar el catálogo</strong>
          <p>Revisá tu conexión e intentá de nuevo.</p>
          <button type="button" class="sp-btn ghost" @click="loadCatalog"><AppIcon name="refresh" :size="16" /> Reintentar</button>
        </div>

        <div v-else-if="catalog.products.length" class="sp-grid" :class="{ loading: catalogStatus === 'loading' }" @pointermove="onCardMove">
          <TplProductCard
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 70"
            class="sp-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
            :stars="custom.show_reviews" stars-icon="star" seal-shape="" quick="Ver producto"
            go-label="Ver más" @open="openProduct">
            <template v-if="productDiscount(p)" #tags>
              <p class="sp-card-promo">
                <AppIcon name="tag" :size="12" aria-hidden="true" />
                {{ productDiscount(p).name }}<span v-if="offerEndsLabel(productDiscount(p))" class="sp-card-promo-ends"> · {{ offerEndsLabel(productDiscount(p)) }}</span>
              </p>
            </template>
          </TplProductCard>
        </div>

        <div v-else class="sp-empty">
          <span class="sp-empty-icon"><AppIcon name="package" :size="26" /></span>
          <strong>{{ hasFilters ? 'Sin resultados' : 'Todavía no hay productos publicados' }}</strong>
          <p>{{ hasFilters ? 'Ningún producto coincide con esos filtros. Probá con otra búsqueda o quitá alguno.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
          <button v-if="hasFilters" type="button" class="sp-btn ghost" @click="clearFilters">Limpiar filtros</button>
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
