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
import '../../assets/store-terra.css'

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
          <article
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            class="tr-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <figure class="tr-card-media">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="tr-card-ph"><AppIcon name="package" :size="26" /></span>
              <span v-if="isNewProduct(p)" class="tr-tag">Nuevo</span>
              <span v-if="productOffer(p) != null" class="tr-tag offer">−{{ offerPct(p) }}%</span>
            </figure>
            <div class="tr-card-body">
              <p class="tr-card-kicker">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') || '\u00a0' }}</p>
              <h3 class="tr-card-name">{{ p.name }}</h3>
              <p class="tr-card-price">
                <s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>
                {{ formatARS(effectivePrice(p)) }}
              </p>
            </div>
          </article>
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
