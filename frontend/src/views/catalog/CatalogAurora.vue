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
import TplProductCard from '../../components/store/TplProductCard.vue'

// Aurora (observatorio de luz): el catálogo se lee como la mesa del
// observatorio — cabecera con lecturas finas, la constelación de
// categorías como chips de vidrio y las piezas en placas con etiqueta
// esmerilada sobre la imagen. La primera pieza brilla a lo ancho como
// estrella polar. Los filtros van en la sidebar/sheet unificada.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, activeCategories,
  visibleProducts, hasMoreProducts, showMore, pickCategory, clearCategories, clearFilters, hasFilters,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-au">
  <main class="cv-wrap cv-au-main">
    <header class="cv-au-head">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
        <span aria-current="page">Catálogo</span>
      </nav>
      <div class="cv-au-title-row">
        <div class="cv-au-title-copy">
          <p class="cv-au-kicker"><AppIcon name="sparkles" :size="13" :stroke="2" aria-hidden="true" /> Observatorio · {{ shopName }}</p>
          <h1 class="cv-au-title">Catálogo</h1>
        </div>
        <p class="cv-au-count" role="status" aria-live="polite"><strong>{{ catalog.products.length }}</strong><span>{{ catalog.products.length === 1 ? 'pieza' : 'piezas' }}</span></p>
      </div>
    </header>

    <!-- Constelación de categorías: acceso rápido a una categoría. -->
    <div class="cv-au-barwrap">
      <div class="cv-au-cats" role="group" aria-label="Categorías">
        <button type="button" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories"><AppIcon name="sparkles" :size="12" :stroke="2" aria-hidden="true" /> Todo el cielo</button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></button>
      </div>
    </div>

    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
    <CatalogToolbar />
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-au-grid" :class="{ loading: catalogStatus === 'loading' }">
      <TplProductCard
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 60"
        class="cv-au-card" :class="{ polar: i === 0 }" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
        :stars="custom.show_reviews" stars-icon="sparkles" :stars-size="11" seal-shape=""
        quick="Ver pieza" :go="false" :ph-size="26" @open="openProduct" />
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
