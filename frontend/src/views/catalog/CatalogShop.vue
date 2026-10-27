<script setup>
import { ref } from 'vue'
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

// Tienda Pro: resultados de marketplace — sidebar de filtros unificada
// (CatalogFilters), barra de resultados (CatalogToolbar) con selector
// grilla/lista propio y tarjetas con precio y descuento destacados.
const {
  custom, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters,
  activeCategoryName, shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const view = ref('grid') // grid | list
</script>

<template>
<div class="sp-page-root cv cv-sh">
  <div class="cv-wrap cv-sh-wrap">
    <nav class="cv-crumbs" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
      <span aria-current="page">Catálogo</span>
      <template v-if="activeCategoryName"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ activeCategoryName }}</span></template>
    </nav>

    <div class="cf-body">
      <CatalogFilters />

      <section class="cv-sh-results cf-main" aria-label="Resultados">
        <div class="cv-sh-top">
          <CatalogToolbar />
          <div class="cv-sh-view" role="group" aria-label="Vista">
            <button type="button" :class="{ on: view === 'grid' }" :aria-pressed="view === 'grid'" aria-label="Vista en grilla" @click="view = 'grid'"><AppIcon name="layout-grid" :size="16" /></button>
            <button type="button" :class="{ on: view === 'list' }" :aria-pressed="view === 'list'" aria-label="Vista en lista" @click="view = 'list'"><AppIcon name="menu" :size="16" /></button>
          </div>
        </div>

        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" :skeletons="6" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-sh-items" :class="[`is-${view}`, { loading: catalogStatus === 'loading' }]">
          <article
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            class="cv-sh-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <div class="cv-sh-media">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="cv-sh-ph"><AppIcon name="package" :size="28" /></span>
            </div>
            <div class="cv-sh-body">
              <p v-if="brandNameOf(p) || categoryNameOf(p)" class="cv-sh-eyebrow">{{ brandNameOf(p) || categoryNameOf(p) }}</p>
              <h3 class="cv-sh-name">{{ p.name }}</h3>
              <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="heart" :size="12" />
              <p v-if="p.description" class="cv-sh-desc">{{ p.description }}</p>
              <p v-if="productOffer(p) != null" class="cv-sh-was">{{ formatARS(p.price) }}</p>
              <p class="cv-sh-price-row">
                <span class="cv-sh-price-now">{{ formatARS(effectivePrice(p)) }}</span>
                <span v-if="productOffer(p) != null" class="cv-sh-off">{{ offerPct(p) }}% OFF</span>
                <span v-else-if="isNewProduct(p)" class="cv-sh-new">Nuevo</span>
              </p>
            </div>
          </article>
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </section>
    </div>
  </div>
</div>
</template>
