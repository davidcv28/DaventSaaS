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
import '../../assets/store-terra.css'

// Terra: catálogo editorial — titular serif, buscador en píldora, filtros
// en una columna de papel y productos en tarjetas con arco. Misma mecánica
// compartida (useStoreCatalog) que el resto de las plantillas.
const {
  ui, custom, homeTo, catalog, catalogStatus, loadCatalog, activeCategories, activeBrands, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, clearPrice, hasFilters,
  hasPriceFilter, productCount, activeTags,
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
      <label class="cv-tr-search">
        <AppIcon name="search" :size="17" aria-hidden="true" />
        <input v-model="ui.search" type="search" placeholder="Buscar un producto…" aria-label="Buscar productos" />
      </label>
    </header>

    <CatalogPromoBanner :promotions="catalog.promotions" />

    <div class="cv-tr-grid">
      <aside class="cv-tr-aside" aria-label="Filtros">
        <div v-if="catalog.categories.length" class="cv-tr-fset">
          <p class="cv-tr-fname">Categoría</p>
          <button
            v-for="cat in catalog.categories" :key="cat.id" type="button"
            class="cv-tr-opt" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)"
            @click="pickCategory(cat.id)"
          >{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></button>
        </div>
        <div v-if="catalog.brands.length" class="cv-tr-fset">
          <p class="cv-tr-fname">Marca</p>
          <button
            v-for="b in catalog.brands" :key="b.id" type="button"
            class="cv-tr-opt" :class="{ on: activeBrands.includes(b.id) }" :aria-pressed="activeBrands.includes(b.id)"
            @click="pickBrand(b.id)"
          >{{ b.name }} <i class="cf-n" aria-hidden="true">{{ b.products_count ?? 0 }}</i></button>
        </div>
        <CatalogFacets />
        <div class="cv-tr-fset">
          <p class="cv-tr-fname">Precio</p>
          <div class="cv-tr-range">
            <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde" aria-label="Precio mínimo" />
            <span aria-hidden="true">–</span>
            <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta" aria-label="Precio máximo" />
          </div>
          <button v-if="hasPriceFilter" type="button" class="cv-tr-opt reset" @click="clearPrice">Limpiar precio</button>
        </div>
        <button v-if="hasFilters" type="button" class="cv-tr-clear" @click="clearFilters">Borrar filtros <AppIcon name="x" :size="13" /></button>
      </aside>

      <div class="cv-tr-results">
        <div class="cv-tr-rbar">
          <label class="cv-tr-sort">
            <span>Ordenar por</span>
            <select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </label>
        </div>

        <div v-if="hasFilters" class="cv-tr-tags">
          <span v-for="t in activeTags" :key="t.key" class="cv-tr-tag">{{ t.label }} <button type="button" :aria-label="`Quitar filtro ${t.label}`" @click="t.remove()"><AppIcon name="x" :size="11" /></button></span>
        </div>

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
