<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import '../../assets/store-bloque.css'

// Bloque: el catálogo como índice de archivo — cabecera con meta en mono y
// titular XXL, buscador a campo completo, aside de filtros como celdas
// regladas y grilla de placas duras numeradas.
const {
  ui, custom, homeTo, catalog, catalogStatus, loadCatalog, activeCategory, activeBrand, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, clearPrice, hasFilters,
  hasPriceFilter, productCount, activeCategoryName, activeBrandName, priceRangeLabel,
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
      <label class="cv-bq-search">
        <AppIcon name="search" :size="16" aria-hidden="true" />
        <input v-model="ui.search" type="search" placeholder="Buscar en el catálogo…" aria-label="Buscar productos" />
      </label>
    </header>

    <CatalogPromoBanner :promotions="catalog.promotions" />

    <div class="cv-bq-grid">
      <aside class="cv-bq-aside" aria-label="Filtros">
        <div v-if="catalog.categories.length" class="cv-bq-fset">
          <p class="cv-bq-fset-name">Categoría</p>
          <button
            v-for="cat in catalog.categories" :key="cat.id" type="button"
            class="cv-bq-opt" :class="{ on: activeCategory === cat.id }" :aria-pressed="activeCategory === cat.id"
            @click="pickCategory(cat.id)"
          >{{ cat.name }}</button>
        </div>
        <div v-if="catalog.brands.length" class="cv-bq-fset">
          <p class="cv-bq-fset-name">Marca</p>
          <button
            v-for="b in catalog.brands" :key="b.id" type="button"
            class="cv-bq-opt" :class="{ on: activeBrand === b.id }" :aria-pressed="activeBrand === b.id"
            @click="pickBrand(b.id)"
          >{{ b.name }}</button>
        </div>
        <div class="cv-bq-fset">
          <p class="cv-bq-fset-name">Precio</p>
          <div class="cv-bq-range">
            <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde" aria-label="Precio mínimo" />
            <span aria-hidden="true">–</span>
            <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta" aria-label="Precio máximo" />
          </div>
          <button v-if="hasPriceFilter" type="button" class="cv-bq-opt reset" @click="clearPrice">Limpiar precio</button>
        </div>
        <button v-if="hasFilters" type="button" class="cv-bq-clear" @click="clearFilters">Borrar filtros <AppIcon name="x" :size="13" /></button>
      </aside>

      <div class="cv-bq-results">
        <div class="cv-bq-rbar">
          <p class="cv-bq-count" role="status" aria-live="polite">{{ productCount }}</p>
          <label class="cv-bq-sort">
            <span class="bq-meta-label">Ordenar</span>
            <select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </label>
        </div>

        <div v-if="hasFilters" class="cv-bq-tags">
          <span v-if="activeCategoryName" class="cv-bq-tag">{{ activeCategoryName }} <button type="button" :aria-label="`Quitar categoría ${activeCategoryName}`" @click="pickCategory(activeCategory)"><AppIcon name="x" :size="11" /></button></span>
          <span v-if="activeBrandName" class="cv-bq-tag">{{ activeBrandName }} <button type="button" :aria-label="`Quitar marca ${activeBrandName}`" @click="pickBrand(activeBrand)"><AppIcon name="x" :size="11" /></button></span>
          <span v-if="ui.search.trim()" class="cv-bq-tag">“{{ ui.search.trim() }}”</span>
          <span v-if="hasPriceFilter" class="cv-bq-tag">{{ priceRangeLabel }} <button type="button" aria-label="Quitar rango de precio" @click="clearPrice"><AppIcon name="x" :size="11" /></button></span>
        </div>

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
