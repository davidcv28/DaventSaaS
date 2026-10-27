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
import '../../assets/store-bloque.css'

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
          <article
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            class="bq-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <figure class="bq-card-plate">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="bq-card-ph"><AppIcon name="package" :size="26" /></span>
              <span v-if="isNewProduct(p)" class="bq-card-flag">Nuevo</span>
              <span v-if="productOffer(p) != null" class="bq-card-flag offer">−{{ offerPct(p) }}%</span>
            </figure>
            <div class="bq-card-row">
              <span class="bq-card-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
              <h3 class="bq-card-name">{{ p.name }}</h3>
              <span class="bq-card-price">
                <s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>
                {{ formatARS(effectivePrice(p)) }}
              </span>
            </div>
            <p class="bq-card-cat">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' / ') || '\u00a0' }}</p>
          </article>
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
