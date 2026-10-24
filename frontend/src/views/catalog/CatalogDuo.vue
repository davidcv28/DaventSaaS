<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'

// Dúo: pantalla partida — a la izquierda un panel fijo con la presentación,
// la navegación por categorías y los filtros; a la derecha el catálogo como
// lista de fichas horizontales (foto + copy), una por renglón.
const {
  ui, custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, activeCategory, activeBrand, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 10 })
</script>

<template>
<div class="sp-page-root cv cv-du">
  <div class="cv-wrap cv-du-split">
    <aside class="cv-du-side" aria-label="Navegación del catálogo">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <h1 class="cv-du-title">Todo lo que<br /><em>{{ shopName }}</em> tiene para vos</h1>
      <p class="cv-du-count"><strong>{{ total }}</strong> {{ total === 1 ? 'producto' : 'productos' }}<template v-if="catalog.categories.length"> · <strong>{{ catalog.categories.length }}</strong> {{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</template></p>

      <label class="cv-du-search">
        <AppIcon name="search" :size="16" aria-hidden="true" />
        <input v-model="ui.search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" />
      </label>

      <div v-if="catalog.categories.length" class="cv-du-group">
        <p class="cv-du-label">Categorías</p>
        <button type="button" class="cv-du-link" :class="{ on: !activeCategory }" @click="activeCategory && pickCategory(activeCategory)"><span>Todas</span></button>
        <button v-for="cat in catalog.categories" :key="cat.id" type="button" class="cv-du-link" :class="{ on: activeCategory === cat.id }" :aria-pressed="activeCategory === cat.id" @click="pickCategory(cat.id)"><span>{{ cat.name }}</span></button>
      </div>

      <div v-if="catalog.brands.length" class="cv-du-group">
        <p class="cv-du-label">Marcas</p>
        <div class="cv-du-tags">
          <button v-for="b in catalog.brands" :key="b.id" type="button" class="cv-du-tag" :class="{ on: activeBrand === b.id }" :aria-pressed="activeBrand === b.id" @click="pickBrand(b.id)">{{ b.name }}</button>
        </div>
      </div>

      <div class="cv-du-group">
        <p class="cv-du-label">Precio</p>
        <div class="cv-du-price">
          <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Desde" aria-label="Precio mínimo" />
          <i aria-hidden="true"></i>
          <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Hasta" aria-label="Precio máximo" />
        </div>
        <label class="cv-du-sort">
          <select v-model="sort" aria-label="Ordenar por">
            <option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
          <AppIcon name="chevron-down" :size="14" aria-hidden="true" />
        </label>
      </div>
      <button v-if="hasFilters" type="button" class="cv-du-clear" @click="clearFilters"><AppIcon name="x" :size="14" /> Limpiar filtros</button>
    </aside>

    <section class="cv-du-list" aria-label="Productos">
      <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" :skeletons="5" @retry="loadCatalog" @clear="clearFilters" />
      <ol v-if="catalog.products.length" class="cv-du-rows" :class="{ loading: catalogStatus === 'loading' }">
        <li v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60">
          <article class="cv-du-row" role="link" tabindex="0" :aria-label="`Ver ${p.name}`" @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)">
            <div class="cv-du-media">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="cv-du-ph"><AppIcon name="package" :size="28" /></span>
            </div>
            <div class="cv-du-copy">
              <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-du-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') }}</p>
              <h3 class="cv-du-name">{{ p.name }}</h3>
              <p v-if="p.description" class="cv-du-desc">{{ p.description }}</p>
              <div class="cv-du-foot">
                <span class="cv-du-price-tag"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
                <span v-if="productOffer(p) != null" class="cv-du-flag">-{{ offerPct(p) }}%</span>
                <span v-else-if="isNewProduct(p)" class="cv-du-flag new">Nuevo</span>
                <span class="cv-du-go" aria-hidden="true"><AppIcon name="arrow-right" :size="16" /></span>
              </div>
            </div>
          </article>
        </li>
      </ol>
      <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
    </section>
  </div>
</div>
</template>
