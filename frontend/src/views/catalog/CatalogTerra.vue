<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import '../../assets/store-terra.css'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Terra: catálogo editorial — titular serif, filtros en una columna de
// papel unificada y productos en tarjetas con arco. Misma mecánica
// compartida (useStoreCatalog) que el resto de las plantillas.
const {
  custom, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, productCount,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-tr">
  <main class="cv-wrap cv-tr-main">
    <nav class="cv-crumbs" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
      <span aria-current="page">Catálogo</span>
    </nav>

    <header class="cv-tr-intro">
      <div>
        <p class="tr-eyebrow"><span class="tr-rule" aria-hidden="true"></span>Catálogo</p>
        <h1 class="cv-tr-title">Todo lo que tenemos</h1>
        <p class="cv-tr-count" role="status" aria-live="polite">{{ productCount }}</p>
      </div>
    </header>

    <CatalogPromoBanner :promotions="catalog.promotions" />

    <div class="cf-body">
      <CatalogFilters />

      <div class="cv-tr-results cf-main">
        <CatalogToolbar />

        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-tr-cards" :class="{ loading: catalogStatus === 'loading' }">
          <TplProductCard
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            tag="figure" class="tr-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
            seal-shape="" :go="false" :ph-size="26" @open="openProduct" />
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
