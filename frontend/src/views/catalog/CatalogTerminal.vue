<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import ProductStars from '../../components/ProductStars.vue'

// Terminal: el catálogo como salida de consola — barra de ventana, prompt
// y los productos como un listado `ls -l` con columnas ordenables. Los
// filtros van en la sidebar/sheet unificada, vestida de consola vía tokens.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, sort,
  visibleProducts, hasMoreProducts, showMore,
  clearFilters, hasFilters, total,
  shownLabel, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 15 })

const slugify = (s) => String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
// Click en el encabezado: alterna asc/desc de la columna (nombre o precio).
function toggleSort(col) {
  if (col === 'name') sort.value = sort.value === 'name' ? 'recent' : 'name'
  else sort.value = sort.value === 'price_asc' ? 'price_desc' : 'price_asc'
}
const arrow = (col) => (col === 'name' ? (sort.value === 'name' ? '↑' : '') : sort.value === 'price_asc' ? '↑' : sort.value === 'price_desc' ? '↓' : '')
const pad = (n) => String(n + 1).padStart(3, '0')
</script>

<template>
<div class="sp-page-root cv cv-tm">
  <div class="cv-wrap cv-tm-wrap">
    <div class="cv-tm-win">
      <div class="cv-tm-bar" aria-hidden="true">
        <span class="cv-tm-dots"><i></i><i></i><i></i></span>
        <span class="cv-tm-path">{{ slugify(shopName) }}@catalogo: ~/productos</span>
        <span class="cv-tm-pid">pid {{ total }}</span>
      </div>

      <div class="cv-tm-body">
        <nav class="cv-tm-crumbs" aria-label="Ruta">
          <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">cd ..</RouterLink>
          <span v-if="custom.site_mode !== 'catalog'"> / </span><span aria-current="page">catalogo</span>
        </nav>
        <h1 class="cv-tm-title"><span aria-hidden="true">$</span> ls -l ./catalogo</h1>

        <CatalogPromoBanner :promotions="catalog.promotions" />

        <div class="cf-body">
          <CatalogFilters />
          <div class="cf-main">
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" :skeletons="6" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-tm-table" role="table" :class="{ loading: catalogStatus === 'loading' }" aria-label="Productos">
          <div class="cv-tm-row head" role="row">
            <span role="columnheader">id</span>
            <span role="columnheader"></span>
            <button type="button" role="columnheader" class="cv-tm-th" @click="toggleSort('name')">nombre {{ arrow('name') }}</button>
            <span role="columnheader" class="cv-tm-hide">categoria</span>
            <span role="columnheader" class="cv-tm-hide">marca</span>
            <button type="button" role="columnheader" class="cv-tm-th right" @click="toggleSort('price')">precio {{ arrow('price') }}</button>
          </div>
          <div
            v-for="(p, i) in visibleProducts" :key="p.id"
            class="cv-tm-row" role="row" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <span role="cell" class="cv-tm-id">{{ pad(i) }}</span>
            <span role="cell" class="cv-tm-thumb"><img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" /><AppIcon v-else name="package" :size="16" /></span>
            <span role="cell" class="cv-tm-name">{{ p.name }}<em v-if="productOffer(p) != null"> -{{ offerPct(p) }}%</em><ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="terminal" :size="11" /></span>
            <span role="cell" class="cv-tm-hide cv-tm-dim">{{ categoryNameOf(p) || '—' }}</span>
            <span role="cell" class="cv-tm-hide cv-tm-dim">{{ brandNameOf(p) || '—' }}</span>
            <span role="cell" class="cv-tm-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
          </div>
        </div>

        <p v-if="catalog.products.length" class="cv-tm-foot" role="status">
          <span>{{ shownLabel.toLowerCase() }}</span>
          <button v-if="hasMoreProducts && catalogStatus !== 'error'" type="button" class="cv-tm-more" @click="showMore">[ver más ↓]</button>
          <span v-else>EOF</span>
        </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</template>
