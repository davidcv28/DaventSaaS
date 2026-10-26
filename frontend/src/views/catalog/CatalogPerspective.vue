<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'

// Perspectiva: el catálogo como un escenario en profundidad — piso con punto
// de fuga bajo el título extruido, categorías como planos flotantes y
// tarjetas que se inclinan hacia el puntero sobre su propio zócalo.
const {
  ui, custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, activeCategory, activeBrand, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog()

const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
function tilt(e) {
  const card = e.target.closest?.('.cv-pe-card')
  if (!card || reduceMotion || e.pointerType === 'touch') return
  const r = card.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width - 0.5
  const y = (e.clientY - r.top) / r.height - 0.5
  card.style.setProperty('--ry', `${(x * 12).toFixed(2)}deg`)
  card.style.setProperty('--rx', `${(-y * 10).toFixed(2)}deg`)
}
function untilt(e) {
  const card = e.target.closest?.('.cv-pe-card')
  card?.style.removeProperty('--rx')
  card?.style.removeProperty('--ry')
}
</script>

<template>
<div class="sp-page-root cv cv-pe">
  <header class="cv-pe-stage">
    <div class="cv-pe-floor" aria-hidden="true"></div>
    <div class="cv-wrap cv-pe-stage-in">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <p class="cv-pe-kicker">{{ shopName }} <i aria-hidden="true"></i> {{ total }} {{ total === 1 ? 'producto' : 'productos' }}</p>
      <h1 class="cv-pe-title" data-text="Catálogo">Catálogo</h1>
      <div v-if="catalog.categories.length" class="cv-pe-planes" role="group" aria-label="Categorías">
        <button type="button" class="cv-pe-plane" :class="{ on: !activeCategory }" :aria-pressed="!activeCategory" @click="activeCategory && pickCategory(activeCategory)"><span>Todo</span></button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" class="cv-pe-plane" :class="{ on: activeCategory === cat.id }" :aria-pressed="activeCategory === cat.id" @click="pickCategory(cat.id)"><span>{{ cat.name }}</span></button>
      </div>
    </div>
  </header>

  <main class="cv-wrap cv-pe-main">
    <div class="cv-pe-panel" role="group" aria-label="Filtros del catálogo">
      <label class="cv-pe-field cv-pe-search">
        <AppIcon name="search" :size="16" aria-hidden="true" />
        <input v-model="ui.search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" />
      </label>
      <div class="cv-pe-field">
        <span>$</span>
        <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mínimo" aria-label="Precio mínimo" />
        <b aria-hidden="true">—</b>
        <span>$</span>
        <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máximo" aria-label="Precio máximo" />
      </div>
      <label class="cv-pe-field">
        <select v-model="sort" aria-label="Ordenar por">
          <option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <AppIcon name="chevron-down" :size="14" aria-hidden="true" />
      </label>
      <button v-if="hasFilters" type="button" class="cv-pe-clear" @click="clearFilters"><AppIcon name="x" :size="14" /> Limpiar</button>
    </div>

    <div v-if="catalog.brands.length" class="cv-pe-brands" role="group" aria-label="Marcas">
      <button v-for="b in catalog.brands" :key="b.id" type="button" class="cv-pe-brand" :class="{ on: activeBrand === b.id }" :aria-pressed="activeBrand === b.id" @click="pickBrand(b.id)">{{ b.name }}</button>
    </div>

    <CatalogPromoBanner :promotions="catalog.promotions" />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-pe-grid" :class="{ loading: catalogStatus === 'loading' }" @pointermove="tilt" @pointerout="untilt">
      <article
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 80"
        class="cv-pe-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
        @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
      >
        <div class="cv-pe-media">
          <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
          <span v-else class="cv-pe-ph"><AppIcon name="package" :size="30" /></span>
          <span v-if="productOffer(p) != null" class="cv-pe-badge">-{{ offerPct(p) }}%</span>
          <span v-else-if="isNewProduct(p)" class="cv-pe-badge new">Nuevo</span>
        </div>
        <div class="cv-pe-plinth" aria-hidden="true"></div>
        <div class="cv-pe-body">
          <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-pe-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') }}</p>
          <h3 class="cv-pe-name">{{ p.name }}</h3>
          <p class="cv-pe-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
        </div>
      </article>
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
  </main>
</div>
</template>
