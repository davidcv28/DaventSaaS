<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFacets from './CatalogFacets.vue'
import CatalogTags from './CatalogTags.vue'
import ProductStars from '../../components/ProductStars.vue'

// Minimal: lo esencial — sin hero ni cromo. Un título chico, una línea
// fina con las categorías como texto separado por barras, buscador y orden
// al costado, y una grilla de fotos 3:4 sin bordes con nombre y precio.
const {
  ui, custom, homeTo, catalog, catalogStatus, loadCatalog, activeCategories, activeBrands, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearCategories, clearFilters, hasFilters, productCount,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-mn">
  <main class="cv-wrap cv-mn-main">
    <nav class="cv-crumbs" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
      <span aria-current="page">Catálogo</span>
    </nav>
    <div class="cv-mn-top">
      <h1 class="cv-mn-title">Catálogo</h1>
      <p class="cv-mn-count" role="status" aria-live="polite">{{ productCount }}</p>
    </div>

    <div class="cv-mn-rule">
      <div class="cv-mn-cats" role="group" aria-label="Categorías">
        <button type="button" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories">Todo</button>
        <template v-for="cat in catalog.categories" :key="cat.id"><i aria-hidden="true">/</i><button type="button" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">{{ cat.name }} <small class="cf-n">{{ cat.products_count ?? 0 }}</small></button></template>
      </div>
      <div class="cv-mn-tools">
        <label class="cv-mn-field"><AppIcon name="search" :size="14" aria-hidden="true" /><input v-model="ui.search" type="search" placeholder="Buscar" aria-label="Buscar productos" /></label>
        <div class="cv-mn-field cv-mn-range"><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde $" aria-label="Precio mínimo" /><i aria-hidden="true">–</i><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta $" aria-label="Precio máximo" /></div>
        <label class="cv-mn-field"><select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select><AppIcon name="chevron-down" :size="13" aria-hidden="true" /></label>
      </div>
    </div>
    <div v-if="catalog.brands.length || hasFilters" class="cv-mn-brands">
      <button v-for="b in catalog.brands" :key="b.id" type="button" :class="{ on: activeBrands.includes(b.id) }" :aria-pressed="activeBrands.includes(b.id)" @click="pickBrand(b.id)">{{ b.name }} <small class="cf-n">{{ b.products_count ?? 0 }}</small></button>
      <button v-if="hasFilters" type="button" class="reset" @click="clearFilters">Limpiar</button>
    </div>
    <CatalogFacets />
    <CatalogTags />

    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-mn-grid" :class="{ loading: catalogStatus === 'loading' }">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 50"
        class="cv-mn-item" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-mn-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-mn-ph"><AppIcon name="package" :size="26" /></span>
        </div>
        <h3 class="cv-mn-name">{{ p.name }}</h3>
        <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="dot" :size="12" />
        <p class="cv-mn-meta">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') || '\u00a0' }}</p>
        <p class="cv-mn-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}<em v-if="productOffer(p) != null"> −{{ offerPct(p) }}%</em></p>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
  </main>
</div>
</template>
