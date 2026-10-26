<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'

// Cobre: retail de indumentaria — placa de acento con titular condensado,
// barra de colección fija con las categorías como pestañas, y una grilla de
// tiles 4:5 donde la primera pieza se muestra como destacada a doble tamaño.
const {
  ui, custom, shopName, homeTo, year, catalog, catalogStatus, loadCatalog, activeCategory, activeBrand, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 9 })
</script>

<template>
<div class="sp-page-root cv cv-cb">
  <header class="cv-cb-head">
    <div class="cv-wrap cv-cb-head-in">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <h1 class="cv-cb-title"><span>Colección</span> <mark>{{ year }}</mark></h1>
      <ul class="cv-cb-facts">
        <li><strong>{{ total }}</strong> {{ total === 1 ? 'producto' : 'productos' }}</li>
        <li v-if="catalog.categories.length"><strong>{{ catalog.categories.length }}</strong> {{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</li>
        <li>{{ shopName }}</li>
      </ul>
    </div>
  </header>

  <div class="cv-cb-bar">
    <div class="cv-wrap cv-cb-bar-in">
      <div class="cv-cb-tabs" role="group" aria-label="Categorías">
        <button type="button" :class="{ on: !activeCategory }" :aria-pressed="!activeCategory" @click="activeCategory && pickCategory(activeCategory)">Todo</button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" :class="{ on: activeCategory === cat.id }" :aria-pressed="activeCategory === cat.id" @click="pickCategory(cat.id)">{{ cat.name }}</button>
      </div>
      <div class="cv-cb-tools">
        <label class="cv-cb-tool"><AppIcon name="search" :size="15" aria-hidden="true" /><input v-model="ui.search" type="search" placeholder="Buscar" aria-label="Buscar productos" /></label>
        <div class="cv-cb-tool cv-cb-range"><input v-model="priceMin" type="text" inputmode="decimal" placeholder="$ min" aria-label="Precio mínimo" /><i aria-hidden="true"></i><input v-model="priceMax" type="text" inputmode="decimal" placeholder="$ max" aria-label="Precio máximo" /></div>
        <label class="cv-cb-tool"><select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select><AppIcon name="chevron-down" :size="14" aria-hidden="true" /></label>
      </div>
    </div>
    <div v-if="catalog.brands.length || hasFilters" class="cv-wrap cv-cb-sub">
      <span v-if="catalog.brands.length">Marca</span>
      <button v-for="b in catalog.brands" :key="b.id" type="button" :class="{ on: activeBrand === b.id }" :aria-pressed="activeBrand === b.id" @click="pickBrand(b.id)">{{ b.name }}</button>
      <button v-if="hasFilters" type="button" class="reset" @click="clearFilters"><AppIcon name="x" :size="13" /> Limpiar</button>
    </div>
  </div>

  <main class="cv-wrap cv-cb-main">
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-cb-grid" :class="{ loading: catalogStatus === 'loading' }">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 60"
        class="cv-cb-tile" :class="{ feat: i === 0 && total > 4 }" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-cb-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-cb-ph"><AppIcon name="package" :size="30" /></span>
          <span v-if="productOffer(p) != null" class="cv-cb-plate">-{{ offerPct(p) }}%</span>
          <span v-else-if="isNewProduct(p)" class="cv-cb-plate ink">Nuevo</span>
          <span class="cv-cb-hover" aria-hidden="true">Ver producto <AppIcon name="arrow-right" :size="15" /></span>
        </div>
        <div class="cv-cb-cap">
          <div>
            <h3 class="cv-cb-name">{{ p.name }}</h3>
            <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-cb-meta">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' / ') }}</p>
          </div>
          <p class="cv-cb-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
        </div>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
  </main>
</div>
</template>
