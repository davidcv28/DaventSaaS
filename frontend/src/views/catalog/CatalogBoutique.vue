<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import ProductStars from '../../components/ProductStars.vue'

// Boutique: departamentos primero — título serif centrado con ornamento,
// una fila de departamentos redondos con la foto de su primera prenda y una
// grilla de 3 columnas con marco fino y barra "Ver prenda" al pasar.
const {
  ui, custom, shopName, homeTo, year, catalog, catalogStatus, loadCatalog, activeCategory, activeBrand, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, hasFilters, total, catThumbs,
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
      <p class="cv-bt-lede">{{ total }} {{ total === 1 ? 'producto' : 'productos' }} · Precios en pesos argentinos</p>

      <div v-if="catalog.categories.length" class="cv-bt-depts" role="group" aria-label="Departamentos">
        <button type="button" class="cv-bt-dept" :class="{ on: !activeCategory }" :aria-pressed="!activeCategory" @click="activeCategory && pickCategory(activeCategory)">
          <span class="cv-bt-disc all"><AppIcon name="layout-grid" :size="22" /></span><b>Todo</b>
        </button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" class="cv-bt-dept" :class="{ on: activeCategory === cat.id }" :aria-pressed="activeCategory === cat.id" @click="pickCategory(cat.id)">
          <span class="cv-bt-disc"><img v-if="catThumbs[cat.id]" :src="catThumbs[cat.id]" alt="" loading="lazy" /><AppIcon v-else name="tag" :size="20" /></span><b>{{ cat.name }}</b>
        </button>
      </div>
    </div>
  </header>

  <main class="cv-wrap cv-bt-main">
    <div class="cv-bt-bar" role="group" aria-label="Filtros del catálogo">
      <label class="cv-bt-field cv-bt-search"><AppIcon name="search" :size="15" aria-hidden="true" /><input v-model="ui.search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" /></label>
      <div class="cv-bt-field"><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde $" aria-label="Precio mínimo" /><i aria-hidden="true">—</i><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta $" aria-label="Precio máximo" /></div>
      <label class="cv-bt-field"><select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select><AppIcon name="chevron-down" :size="13" aria-hidden="true" /></label>
    </div>
    <div v-if="catalog.brands.length || hasFilters" class="cv-bt-brands">
      <button v-for="b in catalog.brands" :key="b.id" type="button" :class="{ on: activeBrand === b.id }" :aria-pressed="activeBrand === b.id" @click="pickBrand(b.id)">{{ b.name }}</button>
      <button v-if="hasFilters" type="button" class="reset" @click="clearFilters"><AppIcon name="x" :size="13" /> Limpiar</button>
    </div>

    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-bt-grid" :class="{ loading: catalogStatus === 'loading' }">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 70"
        class="cv-bt-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-bt-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-bt-ph"><AppIcon name="package" :size="28" /></span>
          <span v-if="productOffer(p) != null" class="cv-bt-flag">-{{ offerPct(p) }}%</span>
          <span v-else-if="isNewProduct(p)" class="cv-bt-flag">Nuevo</span>
          <span class="cv-bt-view" aria-hidden="true">Ver producto</span>
        </div>
        <div class="cv-bt-body">
          <p v-if="brandNameOf(p) || categoryNameOf(p)" class="cv-bt-eyebrow">{{ brandNameOf(p) || categoryNameOf(p) }}</p>
          <h3 class="cv-bt-name">{{ p.name }}</h3>
          <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="crown" :size="12" />
          <p class="cv-bt-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
        </div>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
  </main>
</div>
</template>
