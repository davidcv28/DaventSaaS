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
import '../../assets/store-riso.css'

// Riso: el catálogo en risografía — titular a dos tintas, buscador píldora,
// aside de filtros como tarjeta con sombra desplazada y grilla de tarjetas
// con placa de color y trama de puntos. Mismo estado que el resto de diseños.
const {
  ui, custom, homeTo, catalog, catalogStatus, loadCatalog, activeCategories, activeBrands, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, clearPrice, hasFilters,
  hasPriceFilter, productCount, activeTags,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const TONES = ['pink', 'blue', 'yellow', 'mint']
const toneOf = (p) => TONES[Math.max(0, catalog.value.categories.findIndex((c) => c.id === p.category)) % TONES.length]
</script>

<template>
<div class="sp-page-root cv cv-rs">
  <main class="cv-wrap cv-rs-main">
    <nav class="cv-crumbs cv-rs-crumbs" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
      <span aria-current="page">Catálogo</span>
    </nav>

    <header class="cv-rs-intro">
      <div>
        <span class="rs-kicker tilt">Catálogo · {{ catalog.categories.length }} categorías</span>
        <h1 class="cv-rs-title"><span class="a">Todo</span><br><span class="b">a la vez.</span></h1>
      </div>
      <label class="cv-rs-search">
        <span class="sr-only">Buscar productos</span>
        <input v-model="ui.search" type="search" placeholder="Buscar en el catálogo" autocomplete="off" />
        <span class="cv-rs-search-btn" aria-hidden="true"><AppIcon name="search" :size="16" /></span>
      </label>
    </header>

    <CatalogPromoBanner :promotions="catalog.promotions" />

    <div class="cv-rs-grid">
      <aside class="cv-rs-aside" aria-label="Filtros">
        <div v-if="catalog.categories.length" class="cv-rs-fset">
          <p class="cv-rs-fset-name">Categoría</p>
          <button
            v-for="cat in catalog.categories" :key="cat.id" type="button"
            class="cv-rs-opt" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)"
            @click="pickCategory(cat.id)"
          ><span>{{ cat.name }}</span><span class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</span></button>
        </div>
        <div v-if="catalog.brands.length" class="cv-rs-fset">
          <p class="cv-rs-fset-name">Marca</p>
          <button
            v-for="b in catalog.brands" :key="b.id" type="button"
            class="cv-rs-opt" :class="{ on: activeBrands.includes(b.id) }" :aria-pressed="activeBrands.includes(b.id)"
            @click="pickBrand(b.id)"
          ><span>{{ b.name }}</span><span class="cf-n" aria-hidden="true">{{ b.products_count ?? 0 }}</span></button>
        </div>
        <CatalogFacets />
        <div class="cv-rs-fset">
          <p class="cv-rs-fset-name">Precio</p>
          <div class="cv-rs-range">
            <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde" aria-label="Precio mínimo" />
            <span aria-hidden="true">–</span>
            <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta" aria-label="Precio máximo" />
          </div>
          <button v-if="hasPriceFilter" type="button" class="cv-rs-opt reset" @click="clearPrice"><span>Limpiar precio</span></button>
        </div>
        <button v-if="hasFilters" type="button" class="cv-rs-clear" @click="clearFilters">Limpiar filtros</button>
      </aside>

      <div class="cv-rs-results">
        <div class="cv-rs-rbar">
          <p class="cv-rs-count" role="status" aria-live="polite">{{ productCount }}</p>
          <label class="cv-rs-sort">
            <span class="sr-only">Ordenar por</span>
            <select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select>
          </label>
        </div>

        <div v-if="hasFilters" class="cv-rs-tags">
          <button v-for="t in activeTags" :key="t.key" type="button" class="cv-rs-tag" :aria-label="`Quitar filtro ${t.label}`" @click="t.remove()">{{ t.label }}</button>
        </div>

        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-rs-cards" :class="{ loading: catalogStatus === 'loading' }">
          <article
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            class="rs-card" :class="`t-${toneOf(p)}`" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <figure class="rs-plate">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="rs-plate-ph"><AppIcon name="package" :size="44" /></span>
              <span class="rs-idx">{{ String(i + 1).padStart(3, '0') }}</span>
              <span v-if="productOffer(p) != null" class="rs-badge">−{{ offerPct(p) }}%</span>
              <span v-else-if="isNewProduct(p)" class="rs-badge">Nuevo</span>
            </figure>
            <div class="rs-info">
              <div class="rs-info-row">
                <h3>{{ p.name }}</h3>
                <span class="rs-price">
                  <s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>
                  {{ formatARS(effectivePrice(p)) }}
                </span>
              </div>
              <p>{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') || '\u00a0' }}</p>
            </div>
            <span class="rs-add" aria-hidden="true">Ver producto</span>
          </article>
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
