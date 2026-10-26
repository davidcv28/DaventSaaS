<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFacets from './CatalogFacets.vue'
import ProductStars from '../../components/ProductStars.vue'

// Signature (casa de autor): el catálogo como vitrina ceremonial — dateline
// grabado, título Cinzel centrado con ornamento de rombo, el índice de
// categorías como mayúsculas espaciadas, filtros como campos de
// documento subrayados y placas 4:5 enmarcadas con doble filete.
const {
  ui, custom, shopName, homeTo, year, catalog, catalogStatus, loadCatalog, activeCategories, activeBrands, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearCategories, clearFilters, hasFilters, total,
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
      <p class="cv-sg-lede">{{ total }} {{ total === 1 ? 'pieza' : 'piezas' }} · Precios en pesos argentinos</p>

      <div v-if="catalog.categories.length" class="cv-sg-cats" role="group" aria-label="Categorías">
        <button type="button" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories">Todo</button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></button>
      </div>
    </div>
  </header>

  <main class="cv-wrap cv-sg-main">
    <div class="cv-sg-bar" role="group" aria-label="Filtros del catálogo">
      <label class="cv-sg-field cv-sg-search"><AppIcon name="search" :size="15" aria-hidden="true" /><input v-model="ui.search" type="search" placeholder="Buscar piezas" aria-label="Buscar productos" /></label>
      <div class="cv-sg-field"><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde $" aria-label="Precio mínimo" /><i aria-hidden="true">—</i><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta $" aria-label="Precio máximo" /></div>
      <label class="cv-sg-field"><select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select><AppIcon name="chevron-down" :size="13" aria-hidden="true" /></label>
    </div>
    <div v-if="catalog.brands.length || hasFilters" class="cv-sg-brands">
      <button v-for="b in catalog.brands" :key="b.id" type="button" :class="{ on: activeBrands.includes(b.id) }" :aria-pressed="activeBrands.includes(b.id)" @click="pickBrand(b.id)">{{ b.name }} <i class="cf-n" aria-hidden="true">{{ b.products_count ?? 0 }}</i></button>
      <button v-if="hasFilters" type="button" class="reset" @click="clearFilters"><AppIcon name="x" :size="13" /> Limpiar</button>
    </div>
    <CatalogFacets />

    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-sg-grid" :class="{ loading: catalogStatus === 'loading' }">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 70"
        class="cv-sg-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-sg-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-sg-ph"><AppIcon name="package" :size="26" /></span>
          <span v-if="productOffer(p) != null" class="cv-sg-flag">-{{ offerPct(p) }}%</span>
          <span v-else-if="isNewProduct(p)" class="cv-sg-flag">Nuevo</span>
        </div>
        <div class="cv-sg-body">
          <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-sg-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') }}</p>
          <h3 class="cv-sg-name">{{ p.name }}</h3>
          <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="pencil" :size="12" />
          <p class="cv-sg-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
        </div>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
  </main>
</div>
</template>
