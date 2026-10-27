<script setup>
import { computed } from 'vue'
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

// Urbano: streetwear — titular XXL en outline, cinta de ticker con las
// categorías y fichas numeradas de borde grueso que se escalonan en la
// grilla. Los filtros van en la sidebar/sheet unificada (CatalogFilters).
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const ticker = computed(() => {
  const words = catalog.value.categories.map((c) => c.name)
  const base = words.length ? words : ['Nueva colección', 'Drop', shopName.value]
  return [...base, ...base, ...base, ...base]
})
const pad = (n) => String(n + 1).padStart(2, '0')
</script>

<template>
<div class="sp-page-root cv cv-st">
  <header class="cv-st-head">
    <span class="cv-st-ghost" aria-hidden="true">Drop</span>
    <div class="cv-wrap cv-st-head-in">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <h1 class="cv-st-title">Catálogo<sup>{{ total }}</sup></h1>
      <p class="cv-st-sub">Todo el stock de {{ shopName }}. Sin vueltas.</p>
      <span class="cv-st-sticker" aria-hidden="true">Nuevo<br />drop</span>
    </div>
  </header>

  <div class="cv-st-ribbon" aria-hidden="true">
    <div class="cv-st-ribbon-track"><span v-for="(w, i) in ticker" :key="i">{{ w }}<AppIcon name="zap" :size="14" /></span></div>
  </div>

  <main class="cv-wrap cv-st-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogToolbar />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-st-grid" :class="{ loading: catalogStatus === 'loading' }">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 60"
        class="cv-st-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-st-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-st-ph"><AppIcon name="package" :size="30" /></span>
          <span class="cv-st-num" aria-hidden="true">#{{ pad(i) }}</span>
          <span v-if="productOffer(p) != null" class="cv-st-off">-{{ offerPct(p) }}%</span>
          <span v-else-if="isNewProduct(p)" class="cv-st-off new">New</span>
        </div>
        <div class="cv-st-body">
          <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-st-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' / ') }}</p>
          <h3 class="cv-st-name">{{ p.name }}</h3>
          <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="zap" :size="12" />
          <p class="cv-st-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
        </div>
        <span class="cv-st-arrow" aria-hidden="true"><AppIcon name="arrow-up-right" :size="18" /></span>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" text="Más piezas" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
