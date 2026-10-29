<script setup>
// Catálogo de TRAMA: hero de acento con migas y contadores, franja de
// promociones vigentes, sidebar de filtros de 280 px y grilla de 3 columnas
// con la tarjeta compartida. Toda la lógica (filtros, orden, búsqueda,
// facetas, paginado) sale de useStoreCatalog — acá solo se pinta, igual que
// en el resto de la web pública.
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
const promotions = computed(() => catalog.value.promotions || [])
const priceBounds = computed(() => {
  const max = Number(catalog.value.price_max || 0)
  return max > 0 ? `Hasta ${formatARS(max)}` : ''
})
const toggleFeature = (name, value) => pickFeature(name, value)
</script>

<template>
  <div class="sp-page-root tr-catalog">
    <!-- Hero de acento -->
    <section class="tr-cat-hero">
      <div class="tr-container">
        <nav class="tr-crumbs" aria-label="Ruta">
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <span aria-hidden="true">/</span>
          <span aria-current="page">Catálogo</span>
        </nav>
        <div class="tr-cat-hero-row">
          <div>
            <h1>Catálogo</h1>
            <p class="tr-cat-sub">Todo lo que {{ shopName }} tiene para ofrecerte, en un solo lugar.</p>
          </div>
          <ul class="tr-cat-counters">
            <li><strong>{{ catalog.products.length }}</strong><span>{{ catalog.products.length === 1 ? 'producto' : 'productos' }}</span></li>
            <li><strong>{{ catalog.categories.length }}</strong><span>{{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</span></li>
            <li><strong>{{ catalog.brands.length }}</strong><span>{{ catalog.brands.length === 1 ? 'marca' : 'marcas' }}</span></li>
          </ul>
        </div>
      </div>
    </section>

    <main class="tr-container tr-cat-main">
      <!-- Promociones vigentes -->
      <div v-if="promotions.length" class="tr-promos" role="status">
        <span class="tr-promos-label">Promociones vigentes</span>
        <ul>
          <li v-for="promo in promotions" :key="promo.id || promo.name">
            {{ promo.name }} · -{{ promo.percent }}%
            <span v-if="offerEndsLabel(promo)"> · {{ offerEndsLabel(promo) }}</span>
          </li>
        </ul>
      </div>

      <div class="tr-cat-body">
        <!-- Filtros -->
        <button type="button" class="tr-filters-toggle" :aria-expanded="filtersOpen" aria-controls="tr-filters" @click="filtersOpen = !filtersOpen">
          <AppIcon name="sliders" :size="16" /> Filtros
          <span v-if="activeTags.length" class="tr-filters-count">{{ activeTags.length }}</span>
        </button>

        <aside id="tr-filters" class="tr-filters" :class="{ open: filtersOpen }" aria-label="Filtros del catálogo">
          <header class="tr-filters-head">
            <strong>Filtros</strong>
            <button type="button" class="tr-linkbtn" @click="clearFilters">Limpiar</button>
          </header>

          <fieldset v-if="catalog.categories.length" class="tr-filter-group">
            <legend>Categoría</legend>
            <label v-for="cat in catalog.categories" :key="cat.id" class="tr-check">
              <input type="checkbox" :checked="activeCategories.includes(cat.id)" @change="pickCategory(cat.id)" />
              <span>{{ cat.name }}</span>
              <em>{{ cat.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset v-if="catalog.brands.length" class="tr-filter-group">
            <legend>Marca</legend>
            <label v-for="brand in catalog.brands" :key="brand.id" class="tr-check">
              <input type="checkbox" :checked="activeBrands.includes(brand.id)" @change="pickBrand(brand.id)" />
              <span>{{ brand.name }}</span>
              <em>{{ brand.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset class="tr-filter-group">
            <legend>Precio</legend>
            <div class="tr-price">
              <label><span class="sr-only">Precio mínimo</span><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mín." /></label>
              <label><span class="sr-only">Precio máximo</span><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máx." /></label>
            </div>
            <p v-if="priceBounds" class="tr-filter-hint">{{ priceBounds }}</p>
          </fieldset>

          <fieldset class="tr-filter-group">
            <label class="tr-check"><input type="checkbox" :checked="onlyOffer" @change="toggleOffer" /><span>Solo ofertas</span></label>
            <label class="tr-check"><input type="checkbox" :checked="onlyNew" @change="toggleNew" /><span>Novedades (7 días)</span></label>
          </fieldset>

          <fieldset v-for="facet in facets" :key="facet.name" class="tr-filter-group">
            <legend>{{ facet.name }}</legend>
            <label v-for="value in facet.values" :key="value.value" class="tr-check">
              <input type="checkbox" :checked="isFeatureOn(facet.name, value.value)" @change="toggleFeature(facet.name, value.value)" />
              <span>{{ value.value }}</span>
              <em>{{ value.count }}</em>
            </label>
          </fieldset>

          <p v-if="!catalog.categories.length && !catalog.brands.length && !facets.length" class="tr-filter-hint">
            Los atributos (ej. Talle, Color) aparecen acá al elegir una categoría.
          </p>

          <button type="button" class="tr-btn tr-filters-apply" @click="filtersOpen = false">Ver resultados</button>
        </aside>

        <!-- Resultados -->
        <section class="tr-results" aria-labelledby="tr-results-title">
          <div class="tr-results-head">
            <h2 id="tr-results-title">{{ catalog.products.length }} {{ catalog.products.length === 1 ? 'producto' : 'productos' }}</h2>
            <label class="tr-sort">
              <span>Ordenar por</span>
              <select v-model="sort">
                <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>

          <ul v-if="activeTags.length" class="tr-tags">
            <li v-for="tag in activeTags" :key="tag.key">
              <button type="button" @click="tag.remove()">{{ tag.label }} <AppIcon name="x" :size="12" /></button>
            </li>
          </ul>

          <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="tr-grid" aria-busy="true">
            <span v-for="n in 6" :key="n" class="tr-skel" aria-hidden="true"></span>
          </div>

          <div v-else-if="catalogStatus === 'error'" class="tr-empty">
            <AppIcon name="circle-alert" :size="26" />
            <strong>No pudimos cargar el catálogo</strong>
            <p>Revisá tu conexión e intentá de nuevo.</p>
            <button type="button" class="tr-btn tr-btn--ghost" @click="loadCatalog">Reintentar</button>
          </div>

          <div v-else-if="catalog.products.length" class="tr-grid">
            <TplProductCard
              v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60"
              class="tr-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
              :stars="custom.show_reviews" stars-icon="star" seal-shape=""
              quick="Ver producto" go-label="Ver más" @open="openProduct">
              <template v-if="productDiscount(p)" #tags>
                <p class="tr-card-promo">{{ productDiscount(p).name }}<span v-if="offerEndsLabel(productDiscount(p))"> · {{ offerEndsLabel(productDiscount(p)) }}</span></p>
              </template>
            </TplProductCard>
          </div>

          <div v-else class="tr-empty">
            <AppIcon name="package" :size="26" />
            <strong>{{ hasFilters ? 'Sin resultados' : 'Todavía no hay productos publicados' }}</strong>
            <p>{{ hasFilters ? 'Ningún producto coincide con esos filtros. Probá con otra búsqueda o quitá alguno.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
            <button v-if="hasFilters" type="button" class="tr-btn tr-btn--ghost" @click="clearFilters">Limpiar filtros</button>
          </div>

          <div v-if="hasMoreProducts && catalogStatus !== 'error'" class="tr-more">
            <p>{{ shownLabel }}</p>
            <button type="button" class="tr-btn" @click="showMore"><AppIcon name="plus" :size="16" /> Ver más productos</button>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
