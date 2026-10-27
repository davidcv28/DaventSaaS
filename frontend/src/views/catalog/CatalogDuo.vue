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
          <article class="cv-du-row" role="link" tabindex="0" :aria-label="`Ver ${p.name}`" @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)">
            <div class="cv-du-media">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="cv-du-ph"><AppIcon name="package" :size="28" /></span>
            </div>
            <div class="cv-du-copy">
              <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-du-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') }}</p>
              <h3 class="cv-du-name">{{ p.name }}</h3>
              <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="moon" :size="12" />
              <p v-if="p.description" class="cv-du-desc">{{ p.description }}</p>
              <div class="cv-du-foot">
                <span class="cv-du-price-tag"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
                <span v-if="productOffer(p) != null" class="cv-du-flag">-{{ offerPct(p) }}%</span>
                <span v-else-if="isNewProduct(p)" class="cv-du-flag new">Nuevo</span>
                <span class="cv-du-go" aria-hidden="true"><AppIcon name="arrow-right" :size="16" /></span>
              </div>
            </div>
          </article>
        </li>
      </ol>
      <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
    </section>
  </div>
</div>
</template>
