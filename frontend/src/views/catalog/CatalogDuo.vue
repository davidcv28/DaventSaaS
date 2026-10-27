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
import TplProductCard from '../../components/store/TplProductCard.vue'

// Dúo: pantalla partida — a la izquierda un panel fijo con la presentación
// y debajo la sidebar de filtros (CatalogFilters); a la derecha el catálogo
// como lista de fichas horizontales (foto + copy), una por renglón.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 10 })
</script>

<template>
<div class="sp-page-root cv cv-du">
  <div class="cv-wrap cv-du-split">
    <div class="cv-du-cols">
      <aside class="cv-du-side" aria-label="Presentación">
        <nav class="cv-crumbs" aria-label="Ruta">
          <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
          <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
          <span aria-current="page">Catálogo</span>
        </nav>
        <h1 class="cv-du-title">Todo lo que<br /><em>{{ shopName }}</em> tiene para vos</h1>
        <p class="cv-du-count" role="status" aria-live="polite"><strong>{{ total }}</strong> {{ total === 1 ? 'producto' : 'productos' }}<template v-if="catalog.categories.length"> · <strong>{{ catalog.categories.length }}</strong> {{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</template></p>
      </aside>
      <CatalogFilters />
    </div>

    <section class="cv-du-list" aria-label="Productos">
      <CatalogToolbar />
      <CatalogPromoBanner :promotions="catalog.promotions" />
      <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" :skeletons="5" @retry="loadCatalog" @clear="clearFilters" />
      <ol v-if="catalog.products.length" class="cv-du-rows" :class="{ loading: catalogStatus === 'loading' }">
        <li v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60">
          <TplProductCard class="cv-du-row" layout="row" :p="p"
              :cat="categoryNameOf(p)" :brand="brandNameOf(p)" :desc="p.description || ''"
              :stars="custom.show_reviews" stars-icon="moon" seal-shape="" offer-new
              go-label="" :ph-size="28" @open="openProduct" />
        </li>
      </ol>
      <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
    </section>
  </div>
</div>
</template>
