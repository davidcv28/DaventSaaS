<script setup>
import { ref } from 'vue'
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'

// Tienda Pro: resultados de marketplace — columna de filtros a la izquierda,
// barra de resultados con orden y selector grilla/lista, chips de filtros
// activos y tarjetas de producto con precio y descuento destacados. El
// buscador es el del masthead (ui.search).
const {
  ui, custom, homeTo, catalog, catalogStatus, loadCatalog, activeCategory, activeBrand, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, clearPrice, hasFilters, hasPriceFilter, priceRangeLabel,
  activeCategoryName, activeBrandName, shownLabel, shownPct, productCount, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const view = ref('grid') // grid | list
const filtersOpen = ref(false)
</script>

<template>
<div class="sp-page-root cv cv-sh">
  <div class="cv-wrap cv-sh-wrap">
    <nav class="cv-crumbs" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
      <span aria-current="page">Catálogo</span>
      <template v-if="activeCategoryName"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ activeCategoryName }}</span></template>
    </nav>

    <div class="cv-sh-layout">
      <aside class="cv-sh-side" :class="{ open: filtersOpen }" aria-label="Filtros">
        <section v-if="catalog.categories.length" class="cv-sh-box">
          <h2>Categorías</h2>
          <ul>
            <li><button type="button" :class="{ on: !activeCategory }" @click="activeCategory && pickCategory(activeCategory)">Todas</button></li>
            <li v-for="cat in catalog.categories" :key="cat.id"><button type="button" :class="{ on: activeCategory === cat.id }" :aria-pressed="activeCategory === cat.id" @click="pickCategory(cat.id)">{{ cat.name }}</button></li>
          </ul>
        </section>
        <section v-if="catalog.brands.length" class="cv-sh-box">
          <h2>Marca</h2>
          <ul>
            <li v-for="b in catalog.brands" :key="b.id"><button type="button" class="check" :class="{ on: activeBrand === b.id }" :aria-pressed="activeBrand === b.id" @click="pickBrand(b.id)"><i aria-hidden="true"></i>{{ b.name }}</button></li>
          </ul>
        </section>
        <section class="cv-sh-box">
          <h2>Precio</h2>
          <div class="cv-sh-price">
            <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mínimo" aria-label="Precio mínimo" />
            <span aria-hidden="true">—</span>
            <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máximo" aria-label="Precio máximo" />
          </div>
        </section>
        <button v-if="hasFilters" type="button" class="cv-sh-reset" @click="clearFilters"><AppIcon name="x" :size="14" /> Limpiar filtros</button>
      </aside>

      <section class="cv-sh-results" aria-label="Resultados">
        <div class="cv-sh-bar">
          <p class="cv-sh-count" role="status" aria-live="polite"><strong>{{ catalogStatus === 'success' || catalog.products.length ? productCount : 'Cargando…' }}</strong></p>
          <button type="button" class="cv-sh-filter-btn" :aria-expanded="filtersOpen" @click="filtersOpen = !filtersOpen"><AppIcon name="layout-grid" :size="15" /> Filtros</button>
          <label class="cv-sh-sort"><span>Ordenar por</span>
            <select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </label>
          <div class="cv-sh-view" role="group" aria-label="Vista">
            <button type="button" :class="{ on: view === 'grid' }" :aria-pressed="view === 'grid'" aria-label="Vista en grilla" @click="view = 'grid'"><AppIcon name="layout-grid" :size="16" /></button>
            <button type="button" :class="{ on: view === 'list' }" :aria-pressed="view === 'list'" aria-label="Vista en lista" @click="view = 'list'"><AppIcon name="menu" :size="16" /></button>
          </div>
        </div>

        <div v-if="hasFilters" class="cv-sh-chips" aria-label="Filtros activos">
          <button v-if="ui.search.trim()" type="button" @click="ui.search = ''">&ldquo;{{ ui.search.trim() }}&rdquo; <AppIcon name="x" :size="12" /></button>
          <button v-if="activeCategoryName" type="button" @click="pickCategory(activeCategory)">{{ activeCategoryName }} <AppIcon name="x" :size="12" /></button>
          <button v-if="activeBrandName" type="button" @click="pickBrand(activeBrand)">{{ activeBrandName }} <AppIcon name="x" :size="12" /></button>
          <button v-if="hasPriceFilter" type="button" @click="clearPrice">{{ priceRangeLabel }} <AppIcon name="x" :size="12" /></button>
        </div>

        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" :skeletons="6" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-sh-items" :class="[`is-${view}`, { loading: catalogStatus === 'loading' }]">
          <article
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            class="cv-sh-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <div class="cv-sh-media">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="cv-sh-ph"><AppIcon name="package" :size="28" /></span>
            </div>
            <div class="cv-sh-body">
              <p v-if="brandNameOf(p) || categoryNameOf(p)" class="cv-sh-eyebrow">{{ brandNameOf(p) || categoryNameOf(p) }}</p>
              <h3 class="cv-sh-name">{{ p.name }}</h3>
              <p v-if="p.description" class="cv-sh-desc">{{ p.description }}</p>
              <p v-if="productOffer(p) != null" class="cv-sh-was">{{ formatARS(p.price) }}</p>
              <p class="cv-sh-price-row">
                <span class="cv-sh-price-now">{{ formatARS(effectivePrice(p)) }}</span>
                <span v-if="productOffer(p) != null" class="cv-sh-off">{{ offerPct(p) }}% OFF</span>
                <span v-else-if="isNewProduct(p)" class="cv-sh-new">Nuevo</span>
              </p>
            </div>
          </article>
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </section>
    </div>
  </div>
</div>
</template>
