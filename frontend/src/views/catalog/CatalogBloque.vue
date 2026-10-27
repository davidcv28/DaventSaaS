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
import '../../assets/store-bloque.css'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Bloque: el catálogo como índice de archivo — cabecera con meta en mono y
// titular XXL, aside de filtros como celdas regladas (CatalogFilters) y
// grilla de placas duras numeradas.
const {
  custom, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-bq">
  <main class="cv-wrap cv-bq-main">
    <nav class="cv-crumbs bq-meta" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
      <span aria-current="page">Catálogo</span>
    </nav>

    <header class="cv-bq-intro">
      <div class="cv-bq-intro-head">
        <p class="bq-meta" aria-hidden="true"><span>Índice</span><span>{{ catalog.categories.length }} categorías</span></p>
        <h1 class="cv-bq-title">Catálogo</h1>
      </div>
    </header>

    <CatalogPromoBanner :promotions="catalog.promotions" />

    <div class="cf-body">
      <CatalogFilters />

      <div class="cv-bq-results cf-main">
        <CatalogToolbar />

        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-bq-cards" :class="{ loading: catalogStatus === 'loading' }">
          <TplProductCard
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            class="bq-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
            seal-shape="" :index="String(i + 1).padStart(2, '0')" :go="false"
            :ph-size="26" @open="openProduct" />
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
