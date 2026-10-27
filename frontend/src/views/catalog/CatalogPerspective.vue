<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import ProductStars from '../../components/ProductStars.vue'

// Perspectiva: el catálogo como un escenario en profundidad — piso con punto
// de fuga bajo el título extruido, categorías como planos flotantes y
// tarjetas que se inclinan hacia el puntero sobre su propio zócalo.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, activeCategories,
  visibleProducts, hasMoreProducts, showMore, pickCategory, clearCategories, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog()

const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
function tilt(e) {
  const card = e.target.closest?.('.cv-pe-card')
  if (!card || reduceMotion || e.pointerType === 'touch') return
  const r = card.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width - 0.5
  const y = (e.clientY - r.top) / r.height - 0.5
  card.style.setProperty('--ry', `${(x * 12).toFixed(2)}deg`)
  card.style.setProperty('--rx', `${(-y * 10).toFixed(2)}deg`)
}
function untilt(e) {
  const card = e.target.closest?.('.cv-pe-card')
  card?.style.removeProperty('--rx')
  card?.style.removeProperty('--ry')
}
</script>

<template>
<div class="sp-page-root cv cv-pe">
  <header class="cv-pe-stage">
    <div class="cv-pe-floor" aria-hidden="true"></div>
    <div class="cv-wrap cv-pe-stage-in">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <p class="cv-pe-kicker" role="status" aria-live="polite">{{ shopName }} <i aria-hidden="true"></i> {{ total }} {{ total === 1 ? 'producto' : 'productos' }}</p>
      <h1 class="cv-pe-title" data-text="Catálogo">Catálogo</h1>
      <div v-if="catalog.categories.length" class="cv-pe-planes" role="group" aria-label="Categorías">
        <button type="button" class="cv-pe-plane" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories"><span>Todo</span></button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" class="cv-pe-plane" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)"><span>{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></span></button>
      </div>
    </div>
  </header>

  <main class="cv-wrap cv-pe-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-pe-grid" :class="{ loading: catalogStatus === 'loading' }" @pointermove="tilt" @pointerout="untilt">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 80"
        class="cv-pe-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-pe-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-pe-ph"><AppIcon name="package" :size="30" /></span>
          <span v-if="productOffer(p) != null" class="cv-pe-badge">-{{ offerPct(p) }}%</span>
          <span v-else-if="isNewProduct(p)" class="cv-pe-badge new">Nuevo</span>
        </div>
        <div class="cv-pe-plinth" aria-hidden="true"></div>
        <div class="cv-pe-body">
          <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-pe-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') }}</p>
          <h3 class="cv-pe-name">{{ p.name }}</h3>
          <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="hexagon" :size="12" />
          <p class="cv-pe-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
        </div>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
