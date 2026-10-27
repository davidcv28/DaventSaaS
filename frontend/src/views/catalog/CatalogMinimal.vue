<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct } from '../../api/catalog.api.js'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Minimal: lo esencial — sin hero ni cromo. Un título chico, una línea
// fina con las categorías como texto separado por barras y una grilla de
// fotos 3:4 sin bordes con nombre y precio.
const {
  custom, homeTo, catalog, catalogStatus, loadCatalog, activeCategories,
  visibleProducts, hasMoreProducts, showMore, pickCategory, clearCategories, clearFilters, hasFilters, productCount,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-mn">
  <main class="cv-wrap cv-mn-main">
    <nav class="cv-crumbs" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
      <span aria-current="page">Catálogo</span>
    </nav>
    <div class="cv-mn-top">
      <h1 class="cv-mn-title">Catálogo</h1>
      <p class="cv-mn-count" role="status" aria-live="polite">{{ productCount }}</p>
    </div>

    <div class="cv-mn-rule">
      <div class="cv-mn-cats" role="group" aria-label="Categorías">
        <button type="button" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories">Todo</button>
        <template v-for="cat in catalog.categories" :key="cat.id"><i aria-hidden="true">/</i><button type="button" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">{{ cat.name }} <small class="cf-n">{{ cat.products_count ?? 0 }}</small></button></template>
      </div>
    </div>

    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
    <CatalogToolbar />
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-mn-grid" :class="{ loading: catalogStatus === 'loading' }">
      <TplProductCard
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 50"
        class="cv-mn-item" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
        :stars="custom.show_reviews" stars-icon="dot" seal-shape="" :go="false" :ph-size="26"
        @open="openProduct" />
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
