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

// Boutique: departamentos primero — título serif centrado con ornamento,
// una fila de departamentos redondos con la foto de su primera prenda y una
// grilla de 3 columnas con marco fino y barra "Ver prenda" al pasar.
const {
  custom, shopName, homeTo, year, catalog, catalogStatus, loadCatalog, activeCategories,
  visibleProducts, hasMoreProducts, showMore, pickCategory, clearCategories, clearFilters, hasFilters, total, catThumbs,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-bt">
  <header class="cv-bt-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs center" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <p class="cv-bt-season"><span>{{ shopName }}</span><i aria-hidden="true"></i><span>Colección {{ year }}</span></p>
      <h1 class="cv-bt-title">La <em>colección</em></h1>
      <p class="cv-bt-orn" aria-hidden="true"><i></i><AppIcon name="sparkles" :size="14" /><i></i></p>
      <p class="cv-bt-lede" role="status" aria-live="polite">{{ total }} {{ total === 1 ? 'producto' : 'productos' }} · Precios en pesos argentinos</p>

      <div v-if="catalog.categories.length" class="cv-bt-depts" role="group" aria-label="Departamentos">
        <button type="button" class="cv-bt-dept" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories">
          <span class="cv-bt-disc all"><AppIcon name="layout-grid" :size="22" /></span><b>Todo</b>
        </button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" class="cv-bt-dept" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">
          <span class="cv-bt-disc"><img v-if="catThumbs[cat.id]" :src="catThumbs[cat.id]" alt="" loading="lazy" /><AppIcon v-else name="tag" :size="20" /></span><b>{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></b>
        </button>
      </div>
    </div>
  </header>

  <main class="cv-wrap cv-bt-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
    <CatalogToolbar />
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-bt-grid" :class="{ loading: catalogStatus === 'loading' }">
      <TplProductCard
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 70"
        class="cv-bt-card" :p="p" :cat="brandNameOf(p) || categoryNameOf(p)"
        :stars="custom.show_reviews" stars-icon="crown" seal-shape="" offer-new
        quick="Ver producto" :go="false" :ph-size="28" @open="openProduct" />
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
