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

// Aurora (observatorio de luz): el catálogo se lee como la mesa del
// observatorio — cabecera con lecturas finas, una barra de cristal fija
// con los instrumentos de búsqueda, la constelación de categorías como
// chips de vidrio y las piezas en placas con etiqueta esmerilada sobre
// la imagen. La primera pieza brilla a lo ancho como estrella polar.
const {
  ui, custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, activeCategories, activeBrands, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearCategories, clearFilters, hasFilters, productCount,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv cv-au">
  <main class="cv-wrap cv-au-main">
    <header class="cv-au-head">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
        <span aria-current="page">Catálogo</span>
      </nav>
      <div class="cv-au-title-row">
        <div class="cv-au-title-copy">
          <p class="cv-au-kicker"><AppIcon name="sparkles" :size="13" :stroke="2" aria-hidden="true" /> Observatorio · {{ shopName }}</p>
          <h1 class="cv-au-title">Catálogo</h1>
        </div>
        <p class="cv-au-count" role="status" aria-live="polite"><strong>{{ catalog.products.length }}</strong><span>{{ catalog.products.length === 1 ? 'pieza' : 'piezas' }}</span></p>
      </div>
    </header>

    <!-- Barra de cristal fija: los instrumentos siempre a mano. -->
    <div class="cv-au-barwrap">
      <div class="cv-au-bar">
        <label class="cv-au-field cv-au-search">
          <AppIcon name="search" :size="15" aria-hidden="true" />
          <input v-model="ui.search" type="search" placeholder="Buscar en el cielo" aria-label="Buscar productos" />
        </label>
        <div class="cv-au-field cv-au-range">
          <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde $" aria-label="Precio mínimo" />
          <i aria-hidden="true">–</i>
          <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta $" aria-label="Precio máximo" />
        </div>
        <label class="cv-au-field cv-au-sort">
          <select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          <AppIcon name="chevron-down" :size="14" aria-hidden="true" />
        </label>
      </div>
      <div class="cv-au-cats" role="group" aria-label="Categorías">
        <button type="button" :class="{ on: !activeCategories.length }" :aria-pressed="!activeCategories.length" @click="clearCategories"><AppIcon name="sparkles" :size="12" :stroke="2" aria-hidden="true" /> Todo el cielo</button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></button>
      </div>
      <div v-if="catalog.brands.length || hasFilters" class="cv-au-brands">
        <button v-for="b in catalog.brands" :key="b.id" type="button" :class="{ on: activeBrands.includes(b.id) }" :aria-pressed="activeBrands.includes(b.id)" @click="pickBrand(b.id)">{{ b.name }} <i class="cf-n" aria-hidden="true">{{ b.products_count ?? 0 }}</i></button>
        <button v-if="hasFilters" type="button" class="reset" @click="clearFilters"><AppIcon name="x" :size="12" aria-hidden="true" /> Limpiar</button>
      </div>
      <CatalogFacets />
    </div>

    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-au-grid" :class="{ loading: catalogStatus === 'loading' }">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 60"
        class="cv-au-card" :class="{ polar: i === 0 }" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-au-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-au-ph"><AppIcon name="package" :size="26" /></span>
          <span class="cv-au-quick" aria-hidden="true"><AppIcon name="eye" :size="14" /> Ver pieza</span>
          <span v-if="isNewProduct(p)" class="cv-au-flag">Nuevo</span>
          <span v-if="productOffer(p) != null" class="cv-au-flag offer">-{{ offerPct(p) }}%</span>
          <div class="cv-au-label">
            <span class="cv-au-label-copy">
              <span v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-au-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') }}</span>
              <h3 class="cv-au-name">{{ p.name }}</h3>
              <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="sparkles" :size="11" />
            </span>
            <span class="cv-au-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
          </div>
        </div>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
  </main>
</div>
</template>
