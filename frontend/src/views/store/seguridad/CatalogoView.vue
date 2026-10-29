<script setup>
// Catálogo del diseño SEGURIDAD: encabezado condensado con contadores,
// promociones vigentes, riel de filtros (280 px) y grilla de 3 columnas con
// la tarjeta compartida re-skineada (borde 2 px, precio condensado, chips
// técnicos amarillos). Toda la lógica de filtros/orden/búsqueda/paginado la
// resuelve useStoreCatalog; acá solo se pinta.
import { ref, computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import { effectivePrice, productDiscount, productOffer, offerEndsLabel } from '../../../api/catalog.api.js'
import { useStoreCatalog, SORT_OPTIONS } from '../../../composables/useStoreCatalog.js'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { custom, shopName, slug } = ctx
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const c = useStoreCatalog({ pageSize: 12 })
const {
  catalog, catalogStatus, loadCatalog, activeCategories, activeBrands,
  onlyOffer, onlyNew, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, pickFeature, isFeatureOn,
  toggleOffer, toggleNew, clearFilters, hasFilters, activeTags, facets,
  brandNameOf, categoryNameOf, openProduct, shownLabel
} = c

const filtersOpen = ref(false)
const note = computed(() => (custom.value.show_catalog !== false ? custom.value.catalog_note || '' : ''))
const promotions = computed(() => catalog.value.promotions || [])
const priceBounds = computed(() => {
  const max = Number(catalog.value.price_max || 0)
  return max > 0 ? `Hasta ${formatARS(max)}` : ''
})
const toggleFeature = (name, value) => pickFeature(name, value)
// Chips de specs de la tarjeta: los primeros tres pares cargados por el dueño.
const specChips = (p) => Object.entries(p?.features || {})
  .map(([k, v]) => (String(v || '').trim() ? `${k} ${v}` : k))
  .filter(Boolean)
  .slice(0, 3)
</script>

<template>
  <div class="sp-page-root sg-catalog">
    <!-- Encabezado -->
    <section class="sg-cat-head">
      <div class="sg-wrap">
        <nav class="sg-crumbs" aria-label="Ruta">
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <span aria-hidden="true">/</span>
          <span aria-current="page">Catálogo</span>
        </nav>
        <div class="sg-cat-head-row">
          <div class="sg-cat-head-copy">
            <p class="sg-eyebrow">Catálogo</p>
            <h1 class="sg-cat-title">Todo el equipamiento</h1>
            <p class="sg-cat-lead">Precios y especificaciones de {{ shopName }}, en un solo lugar.</p>
          </div>
          <ul class="sg-cat-counts" aria-label="Contenido del catálogo">
            <li><strong>{{ catalog.products.length }}</strong><span>{{ catalog.products.length === 1 ? 'producto' : 'productos' }}</span></li>
            <li><strong>{{ catalog.categories.length }}</strong><span>{{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</span></li>
            <li><strong>{{ catalog.brands.length }}</strong><span>{{ catalog.brands.length === 1 ? 'marca' : 'marcas' }}</span></li>
          </ul>
        </div>
      </div>
    </section>

    <p v-if="note" class="sg-cat-note">{{ note }}</p>

    <main class="sg-wrap sg-cat-main">
      <!-- Promociones vigentes -->
      <div v-if="promotions.length" class="sg-promos" role="status">
        <span class="sg-promos-label">Promociones vigentes</span>
        <ul>
          <li v-for="promo in promotions" :key="promo.id || promo.name">
            {{ promo.name }} · -{{ promo.percent }}%
            <span v-if="offerEndsLabel(promo)"> · {{ offerEndsLabel(promo) }}</span>
          </li>
        </ul>
      </div>

      <div class="sg-cat-body">
        <button
          type="button" class="sg-filters-toggle" :aria-expanded="filtersOpen"
          aria-controls="sg-filters" @click="filtersOpen = !filtersOpen"
        >
          <AppIcon name="sliders" :size="16" /> Filtros
          <span v-if="activeTags.length" class="sg-filters-count">{{ activeTags.length }}</span>
        </button>

        <!-- Filtros -->
        <aside id="sg-filters" class="sg-filters" :class="{ open: filtersOpen }" aria-label="Filtros del catálogo">
          <header class="sg-filters-head">
            <strong>Filtros</strong>
            <button type="button" class="sg-linkbtn" :disabled="!hasFilters" @click="clearFilters">Limpiar</button>
          </header>

          <fieldset v-if="catalog.categories.length" class="sg-filter-group">
            <legend>Categoría</legend>
            <label v-for="cat in catalog.categories" :key="cat.id" class="sg-check">
              <input type="checkbox" :checked="activeCategories.includes(cat.id)" @change="pickCategory(cat.id)" />
              <span>{{ cat.name }}</span>
              <em>{{ cat.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset v-if="catalog.brands.length" class="sg-filter-group">
            <legend>Marca</legend>
            <label v-for="brand in catalog.brands" :key="brand.id" class="sg-check">
              <input type="checkbox" :checked="activeBrands.includes(brand.id)" @change="pickBrand(brand.id)" />
              <span>{{ brand.name }}</span>
              <em>{{ brand.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset class="sg-filter-group">
            <legend>Precio</legend>
            <div class="sg-price">
              <label><span class="sr-only">Precio mínimo</span><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mín." /></label>
              <label><span class="sr-only">Precio máximo</span><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máx." /></label>
            </div>
            <p v-if="priceBounds" class="sg-filter-hint">{{ priceBounds }}</p>
          </fieldset>

          <fieldset class="sg-filter-group">
            <label class="sg-check"><input type="checkbox" :checked="onlyOffer" @change="toggleOffer" /><span>Solo ofertas</span></label>
            <label class="sg-check"><input type="checkbox" :checked="onlyNew" @change="toggleNew" /><span>Novedades (7 días)</span></label>
          </fieldset>

          <fieldset v-for="facet in facets" :key="facet.name" class="sg-filter-group">
            <legend>{{ facet.name }}</legend>
            <label v-for="value in facet.values" :key="value.value" class="sg-check">
              <input type="checkbox" :checked="isFeatureOn(facet.name, value.value)" @change="toggleFeature(facet.name, value.value)" />
              <span>{{ value.value }}</span>
              <em>{{ value.count }}</em>
            </label>
          </fieldset>

          <p v-if="!catalog.categories.length && !catalog.brands.length && !facets.length" class="sg-filter-hint">
            Los atributos (ej. clase de fuego, capacidad) aparecen acá al elegir una categoría.
          </p>

          <button type="button" class="sg-btn sg-filters-apply" @click="filtersOpen = false">Ver resultados</button>
        </aside>

        <!-- Resultados -->
        <section class="sg-results" aria-labelledby="sg-results-title">
          <div class="sg-results-head">
            <h2 id="sg-results-title">{{ catalog.products.length }} {{ catalog.products.length === 1 ? 'producto' : 'productos' }}</h2>
            <label class="sg-sort">
              <span>Ordenar por</span>
              <select v-model="sort">
                <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>

          <ul v-if="activeTags.length" class="sg-tags">
            <li v-for="tag in activeTags" :key="tag.key">
              <button type="button" @click="tag.remove()">{{ tag.label }} <AppIcon name="x" :size="12" /></button>
            </li>
          </ul>

          <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="sg-grid" aria-busy="true">
            <span v-for="n in 6" :key="n" class="sg-skel" aria-hidden="true"></span>
          </div>

          <div v-else-if="catalogStatus === 'error'" class="sg-empty">
            <AppIcon name="circle-alert" :size="26" />
            <strong>No pudimos cargar el catálogo</strong>
            <p>Revisá tu conexión e intentá de nuevo.</p>
            <button type="button" class="sg-btn sg-btn--ghost" @click="loadCatalog">Reintentar</button>
          </div>

          <div v-else-if="catalog.products.length" class="sg-grid">
            <TplProductCard
              v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60"
              class="sg-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
              :stars="custom.show_reviews" stars-icon="star" seal-shape="" :go="false"
              @open="openProduct"
            >
              <template #tags>
                <ul v-if="specChips(p).length" class="sg-card-specs">
                  <li v-for="chip in specChips(p)" :key="chip">{{ chip }}</li>
                </ul>
                <p v-if="productDiscount(p)" class="sg-card-promo">
                  {{ productDiscount(p).name }}<span v-if="offerEndsLabel(productDiscount(p))"> · {{ offerEndsLabel(productDiscount(p)) }}</span>
                </p>
              </template>
              <template #foot>
                <span class="sg-card-foot">
                  <span class="sg-card-price">
                    <s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>
                    <strong>{{ formatARS(effectivePrice(p)) }}</strong>
                  </span>
                  <span class="sg-card-wa" aria-hidden="true">Ver ficha</span>
                </span>
              </template>
            </TplProductCard>
          </div>

          <div v-else class="sg-empty">
            <AppIcon name="package" :size="26" />
            <strong>{{ hasFilters ? 'Sin resultados' : 'Todavía no hay productos publicados' }}</strong>
            <p>{{ hasFilters ? 'Ningún producto coincide con esos filtros. Probá con otra búsqueda o quitá alguno.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
            <button v-if="hasFilters" type="button" class="sg-btn sg-btn--ghost" @click="clearFilters">Limpiar filtros</button>
          </div>

          <div v-if="hasMoreProducts && catalogStatus !== 'error'" class="sg-more">
            <p>{{ shownLabel }}</p>
            <button type="button" class="sg-btn" @click="showMore"><AppIcon name="plus" :size="16" /> Ver más productos</button>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
