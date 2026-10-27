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

// Signature (casa de autor): el catálogo como vitrina ceremonial — dateline
// grabado, título Cinzel centrado con ornamento de rombo, el índice de
// categorías como mayúsculas espaciadas y placas 4:5 enmarcadas con doble
// filete.
const {
  custom, shopName, homeTo, year, catalog, catalogStatus, loadCatalog, activeCategories,
  visibleProducts, hasMoreProducts, showMore, pickCategory, clearCategories, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-sg">
  <header class="cv-sg-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs center" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <p class="cv-sg-dateline"><i aria-hidden="true"></i><span>{{ shopName }}</span><i aria-hidden="true"></i><span>{{ year }}</span></p>
      <h1 class="cv-sg-title">La vitrina</h1>
      <p class="cv-sg-orn" aria-hidden="true"><i></i><span class="cv-sg-romb"></span><i></i></p>
      <p class="cv-sg-lede" role="status" aria-live="polite">{{ total }} {{ total === 1 ? 'pieza' : 'piezas' }} · Precios en pesos argentinos</p>

      <div v-if="catalog.categories.length" class="cv-sg-cats" role="group" aria-label="Categorías">
        <button type="button" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories">Todo</button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></button>
      </div>
    </div>
  </header>

  <main class="cv-wrap cv-sg-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
    <CatalogToolbar />
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-sg-grid" :class="{ loading: catalogStatus === 'loading' }">
      <TplProductCard
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 70"
        class="cv-sg-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
        :stars="custom.show_reviews" stars-icon="pencil" seal-shape="" offer-new
        :go="false" :ph-size="26" @open="openProduct" />
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
