<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'

// Lookbook: el catálogo como edición de revista — título serif con índice de
// contenidos (las categorías, numeradas), filtros escritos como texto
// subrayado y pliegos de imagen en columnas con proporciones alternadas.
const {
  ui, custom, shopName, homeTo, year, catalog, catalogStatus, loadCatalog, activeCategory, activeBrand, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const pad = (n) => String(n).padStart(2, '0')
</script>

<template>
<div class="sp-page-root cv cv-lb">
  <header class="cv-wrap cv-lb-head">
    <div class="cv-lb-masthead">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <p class="cv-lb-issue"><span>Edición Nº {{ pad(1) }}</span><i aria-hidden="true"></i><span>{{ shopName }} · {{ year }}</span></p>
      <h1 class="cv-lb-title">Índice de la <em>colección</em></h1>
      <p class="cv-lb-lede">{{ total }} {{ total === 1 ? 'pieza' : 'piezas' }} seleccionadas, ordenadas para hojear sin apuro.</p>
    </div>
    <nav v-if="catalog.categories.length" class="cv-lb-toc" aria-label="Categorías">
      <p class="cv-lb-toc-h">Contenido</p>
      <ol>
        <li><button type="button" :class="{ on: !activeCategory }" @click="activeCategory && pickCategory(activeCategory)"><b>00</b><span>Toda la colección</span><i aria-hidden="true"></i></button></li>
        <li v-for="(cat, i) in catalog.categories" :key="cat.id"><button type="button" :class="{ on: activeCategory === cat.id }" :aria-pressed="activeCategory === cat.id" @click="pickCategory(cat.id)"><b>{{ pad(i + 1) }}</b><span>{{ cat.name }}</span><i aria-hidden="true"></i></button></li>
      </ol>
    </nav>
  </header>

  <main class="cv-wrap cv-lb-main">
    <div class="cv-lb-bar" role="group" aria-label="Filtros del catálogo">
      <label class="cv-lb-line"><span>Buscar</span><input v-model="ui.search" type="search" placeholder="una pieza…" aria-label="Buscar productos" /></label>
      <div class="cv-lb-line"><span>Precio</span><input v-model="priceMin" type="text" inputmode="decimal" placeholder="desde" aria-label="Precio mínimo" /><i aria-hidden="true">–</i><input v-model="priceMax" type="text" inputmode="decimal" placeholder="hasta" aria-label="Precio máximo" /></div>
      <div class="cv-lb-line cv-lb-sorts" role="group" aria-label="Ordenar por"><span>Orden</span><button v-for="o in SORT_OPTIONS" :key="o.value" type="button" :class="{ on: sort === o.value }" :aria-pressed="sort === o.value" @click="sort = o.value">{{ o.label.replace(' (A-Z)', '') }}</button></div>
      <div v-if="catalog.brands.length" class="cv-lb-line cv-lb-sorts" role="group" aria-label="Marcas"><span>Firmas</span><button v-for="b in catalog.brands" :key="b.id" type="button" :class="{ on: activeBrand === b.id }" :aria-pressed="activeBrand === b.id" @click="pickBrand(b.id)">{{ b.name }}</button></div>
      <button v-if="hasFilters" type="button" class="cv-lb-reset" @click="clearFilters">Quitar filtros</button>
    </div>

    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" :skeletons="6" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-lb-sheets" :class="{ loading: catalogStatus === 'loading' }">
      <figure v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 80" class="cv-lb-sheet" role="link" tabindex="0" :aria-label="`Ver ${p.name}`" @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)">
        <div class="cv-lb-plate">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-lb-ph"><AppIcon name="package" :size="30" /></span>
          <span v-if="productOffer(p) != null" class="cv-lb-seal">-{{ offerPct(p) }}%</span>
        </div>
        <figcaption>
          <span class="cv-lb-no">Nº {{ pad(i + 1) }}</span>
          <h3 class="cv-lb-name">{{ p.name }}</h3>
          <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-lb-meta">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' — ') }}</p>
          <p class="cv-lb-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
        </figcaption>
      </figure>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" text="Pasar la página" @more="showMore" />
  </main>
</div>
</template>
