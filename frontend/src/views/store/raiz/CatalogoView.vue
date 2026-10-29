<script setup>
// Catálogo del diseño RAÍZ: hero de acento, tira de catálogo, promociones
// vigentes, sidebar de filtros (280px) y grilla de 3 columnas. Toda la
// lógica de filtros/orden/búsqueda/paginado la resuelve useStoreCatalog
// (misma API que el resto de la web): acá solo se pinta.
import { ref, computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import { productDiscount, offerEndsLabel } from '../../../api/catalog.api.js'
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
  featureFilters, onlyOffer, onlyNew, priceMin, priceMax, sort,
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
</script>

<template>
  <div class="sp-page-root rz-catalog">
    <!-- Hero de acento -->
    <section class="rz-cat-hero">
      <div class="rz-container">
        <nav class="rz-crumbs" aria-label="Ruta">
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <span aria-hidden="true">/</span>
          <span aria-current="page">Catálogo</span>
        </nav>
        <div class="rz-cat-hero-row">
          <div>
            <h1>Catálogo</h1>
            <p class="rz-cat-sub">Todo lo que {{ shopName }} tiene para ofrecerte, en un solo lugar.</p>
          </div>
          <ul class="rz-cat-counters">
            <li><strong>{{ catalog.products.length }}</strong><span>{{ catalog.products.length === 1 ? 'producto' : 'productos' }}</span></li>
            <li><strong>{{ catalog.categories.length }}</strong><span>{{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</span></li>
            <li><strong>{{ catalog.brands.length }}</strong><span>{{ catalog.brands.length === 1 ? 'marca' : 'marcas' }}</span></li>
          </ul>
        </div>
      </div>
    </section>

    <p v-if="note" class="rz-cat-note">{{ note }}</p>

    <main class="rz-container rz-cat-main">
      <!-- Promociones vigentes -->
      <div v-if="promotions.length" class="rz-promos" role="status">
        <span class="rz-promos-label">Promociones vigentes</span>
        <ul>
          <li v-for="promo in promotions" :key="promo.id || promo.name">
            {{ promo.name }} · -{{ promo.percent }}%
            <span v-if="offerEndsLabel(promo)"> · {{ offerEndsLabel(promo) }}</span>
          </li>
        </ul>
      </div>

      <div class="rz-cat-body">
        <!-- Filtros -->
        <button type="button" class="rz-filters-toggle" :aria-expanded="filtersOpen" aria-controls="rz-filters" @click="filtersOpen = !filtersOpen">
          <AppIcon name="sliders" :size="16" /> Filtros
          <span v-if="activeTags.length" class="rz-filters-count">{{ activeTags.length }}</span>
        </button>

        <aside id="rz-filters" class="rz-filters" :class="{ open: filtersOpen }" aria-label="Filtros del catálogo">
          <header class="rz-filters-head">
            <strong>Filtros</strong>
            <button type="button" class="rz-linkbtn" @click="clearFilters">Limpiar</button>
          </header>

          <fieldset v-if="catalog.categories.length" class="rz-filter-group">
            <legend>Categoría</legend>
            <label v-for="cat in catalog.categories" :key="cat.id" class="rz-check">
              <input type="checkbox" :checked="activeCategories.includes(cat.id)" @change="pickCategory(cat.id)" />
              <span>{{ cat.name }}</span>
              <em>{{ cat.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset v-if="catalog.brands.length" class="rz-filter-group">
            <legend>Marca</legend>
            <label v-for="brand in catalog.brands" :key="brand.id" class="rz-check">
              <input type="checkbox" :checked="activeBrands.includes(brand.id)" @change="pickBrand(brand.id)" />
              <span>{{ brand.name }}</span>
              <em>{{ brand.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset class="rz-filter-group">
            <legend>Precio</legend>
            <div class="rz-price">
              <label><span class="sr-only">Precio mínimo</span><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mín." /></label>
              <label><span class="sr-only">Precio máximo</span><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máx." /></label>
            </div>
            <p v-if="priceBounds" class="rz-filter-hint">{{ priceBounds }}</p>
          </fieldset>

          <fieldset class="rz-filter-group">
            <label class="rz-check"><input type="checkbox" :checked="onlyOffer" @change="toggleOffer" /><span>Solo ofertas</span></label>
            <label class="rz-check"><input type="checkbox" :checked="onlyNew" @change="toggleNew" /><span>Novedades (7 días)</span></label>
          </fieldset>

          <fieldset v-for="facet in facets" :key="facet.name" class="rz-filter-group">
            <legend>{{ facet.name }}</legend>
            <label v-for="value in facet.values" :key="value.value" class="rz-check">
              <input type="checkbox" :checked="isFeatureOn(facet.name, value.value)" @change="toggleFeature(facet.name, value.value)" />
              <span>{{ value.value }}</span>
              <em>{{ value.count }}</em>
            </label>
          </fieldset>

          <p v-if="!catalog.categories.length && !catalog.brands.length && !facets.length" class="rz-filter-hint">
            Los atributos (ej. Talle, Color) aparecen acá al elegir una categoría.
          </p>

          <button type="button" class="rz-btn rz-filters-apply" @click="filtersOpen = false">Ver resultados</button>
        </aside>

        <!-- Resultados -->
        <section class="rz-results" aria-labelledby="rz-results-title">
          <div class="rz-results-head">
            <h2 id="rz-results-title">{{ catalog.products.length }} {{ catalog.products.length === 1 ? 'producto' : 'productos' }}</h2>
            <label class="rz-sort">
              <span>Ordenar por</span>
              <select v-model="sort">
                <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>

          <ul v-if="activeTags.length" class="rz-tags">
            <li v-for="tag in activeTags" :key="tag.key">
              <button type="button" @click="tag.remove()">{{ tag.label }} <AppIcon name="x" :size="12" /></button>
            </li>
          </ul>

          <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="rz-grid" aria-busy="true">
            <span v-for="n in 6" :key="n" class="rz-skel" aria-hidden="true"></span>
          </div>

          <div v-else-if="catalogStatus === 'error'" class="rz-empty">
            <AppIcon name="circle-alert" :size="26" />
            <strong>No pudimos cargar el catálogo</strong>
            <p>Revisá tu conexión e intentá de nuevo.</p>
            <button type="button" class="rz-btn ghost" @click="loadCatalog">Reintentar</button>
          </div>

          <div v-else-if="catalog.products.length" class="rz-grid">
            <TplProductCard
              v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60"
              class="rz-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
              :stars="custom.show_reviews" stars-icon="star" quick="Ver producto"
              go-label="Ver más" @open="openProduct">
              <template v-if="productDiscount(p)" #tags>
                <p class="rz-card-promo">{{ productDiscount(p).name }}<span v-if="offerEndsLabel(productDiscount(p))"> · {{ offerEndsLabel(productDiscount(p)) }}</span></p>
              </template>
            </TplProductCard>
          </div>

          <div v-else class="rz-empty">
            <AppIcon name="package" :size="26" />
            <strong>{{ hasFilters ? 'Sin resultados' : 'Todavía no hay productos publicados' }}</strong>
            <p>{{ hasFilters ? 'Ningún producto coincide con esos filtros. Probá con otra búsqueda o quitá alguno.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
            <button v-if="hasFilters" type="button" class="rz-btn ghost" @click="clearFilters">Limpiar filtros</button>
          </div>

          <div v-if="hasMoreProducts && catalogStatus !== 'error'" class="rz-more">
            <p>{{ shownLabel }}</p>
            <button type="button" class="rz-btn" @click="showMore"><AppIcon name="plus" :size="16" /> Ver más productos</button>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
