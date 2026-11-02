<script setup>
// Catálogo del diseño CIRCUITO: consola HUD de búsqueda avanzada siempre
// visible, panel de filtros (precio, ofertas, novedades, categorías, marcas y
// facetas), promociones vigentes y grilla de productos con sus
// especificaciones. Toda la lógica de filtros, orden, búsqueda y paginado la
// resuelve useStoreCatalog (misma API que el resto de la web): acá solo se pinta.
import { ref, computed, nextTick, watch, onBeforeUnmount, inject } from 'vue'
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
  ui, catalog, catalogStatus, loadCatalog, activeCategories, activeBrands,
  onlyOffer, onlyNew, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, pickFeature, isFeatureOn,
  toggleOffer, toggleNew, clearFilters, hasFilters, activeTags, facets, priceRangeLabel,
  offerTotal, newTotal, productCount, activeFilterCount,
  brandNameOf, categoryNameOf, openProduct, shownLabel
} = c

const filtersOpen = ref(false)
const filtersToggle = ref(null)
const filtersPanel = ref(null)
const searchInput = ref(null)
const note = computed(() => (custom.value.show_catalog !== false ? custom.value.catalog_note || '' : ''))
const promotions = computed(() => catalog.value.promotions || [])
const priceBounds = computed(() => {
  const max = Number(catalog.value.price_max || 0)
  return max > 0 ? `Techo del catálogo: ${formatARS(max)}` : ''
})
const toggleFeature = (name, value) => pickFeature(name, value)
// Chips de specs de la tarjeta: los primeros pares cargados por el dueño.
const specChips = (p) => Object.entries(p?.features || {}).slice(0, 2).map(([k, v]) => `${k} ${v}`)
const clearSearch = () => {
  ui.search = ''
  nextTick(() => searchInput.value?.focus())
}
// Drawer móvil: cerrar devuelve el foco al botón que lo abrió (teclado) y el
// fondo no scrollea mientras el panel está superpuesto.
const isDrawer = () => typeof window !== 'undefined' && window.matchMedia('(max-width: 1100px)').matches
let bodyLocked = false
function lockBody(lock) {
  if (typeof document === 'undefined') return
  if (lock && !bodyLocked) {
    document.body.style.overflow = 'hidden'
    bodyLocked = true
  } else if (!lock && bodyLocked) {
    document.body.style.overflow = ''
    bodyLocked = false
  }
}
watch(filtersOpen, (open) => {
  lockBody(open && isDrawer())
  if (open && isDrawer()) nextTick(() => filtersPanel.value?.focus())
})
onBeforeUnmount(() => lockBody(false))

function toggleFilters() {
  if (filtersOpen.value) { closeFilters(); return }
  filtersOpen.value = true
}
function closeFilters() {
  if (!filtersOpen.value) return
  filtersOpen.value = false
  nextTick(() => filtersToggle.value?.focus())
}
</script>

<template>
  <div class="sp-page-root ci-catalog">
    <section class="ci-cat-hero">
      <div class="ci-container">
        <nav class="ci-crumbs" aria-label="Ruta">
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <span aria-hidden="true">/</span>
          <span aria-current="page">Catálogo</span>
        </nav>
        <div class="ci-cat-hero-row">
          <div class="ci-cat-hero-copy">
            <p class="ci-label">Catálogo</p>
            <h1>Todo el equipamiento</h1>
            <p class="ci-cat-sub">Precios, stock y especificaciones de {{ shopName }}, en un solo lugar.</p>
          </div>
          <ul class="ci-cat-counters" aria-label="Resumen del catálogo">
            <li>
              <strong aria-live="polite">{{ catalog.products.length }}</strong>
              <span>{{ catalog.products.length === 1 ? 'resultado' : 'resultados' }}</span>
            </li>
            <li><strong>{{ catalog.categories.length }}</strong><span>{{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</span></li>
            <li><strong>{{ catalog.brands.length }}</strong><span>{{ catalog.brands.length === 1 ? 'marca' : 'marcas' }}</span></li>
          </ul>
        </div>
      </div>
    </section>

    <p v-if="note" class="ci-cat-note">{{ note }}</p>

    <main class="ci-container ci-cat-main">
      <!-- Promociones vigentes -->
      <div v-if="promotions.length" class="ci-promos" role="status">
        <span class="ci-promos-label"><AppIcon name="percent" :size="13" aria-hidden="true" /> Promos activas</span>
        <ul>
          <li v-for="promo in promotions" :key="promo.id || promo.name">
            {{ promo.name }} · -{{ promo.percent }}%
            <span v-if="offerEndsLabel(promo)"> · {{ offerEndsLabel(promo) }}</span>
          </li>
        </ul>
      </div>

      <!-- Búsqueda avanzada: SIEMPRE visible, también con el catálogo vacío -->
      <form class="ci-searchbar" role="search" @submit.prevent>
        <div class="ci-search-field">
          <AppIcon class="ci-search-ico" name="search" :size="18" aria-hidden="true" />
          <label class="sr-only" for="ci-cat-search">Buscar productos por nombre, marca o especificación</label>
          <input
            id="ci-cat-search" ref="searchInput" v-model="ui.search" type="search"
            placeholder="Buscar producto, marca o especificación…" autocomplete="off" spellcheck="false"
            aria-controls="ci-results" @keydown.esc="ui.search = ''">
          <button v-if="ui.search" type="button" class="ci-search-clear" aria-label="Borrar búsqueda" @click.prevent="clearSearch">
            <AppIcon name="x" :size="15" />
          </button>
          <span class="ci-search-scan" aria-hidden="true"></span>
        </div>
        <p class="ci-search-hint">
          <span aria-hidden="true">//</span> Busca en nombre, descripción, categoría, marca y características
        </p>
        <button
          ref="filtersToggle" type="button" class="ci-filters-toggle"
          :aria-expanded="filtersOpen" aria-controls="ci-filters" @click="toggleFilters">
          <AppIcon name="sliders" :size="16" aria-hidden="true" /> Filtros
          <span v-if="activeFilterCount" class="ci-filters-count">{{ activeFilterCount }}</span>
        </button>
      </form>

      <div class="ci-cat-body">
        <!-- Filtros -->
        <div v-if="filtersOpen" class="ci-filters-backdrop" aria-hidden="true" @click="closeFilters"></div>
        <aside
          id="ci-filters" ref="filtersPanel" class="ci-filters" :class="{ open: filtersOpen }"
          tabindex="-1" aria-label="Filtros del catálogo" @keydown.esc="closeFilters">
          <header class="ci-filters-head">
            <strong><span aria-hidden="true">//</span> Filtros</strong>
            <button type="button" class="ci-linkbtn" :disabled="!hasFilters" @click="clearFilters">Limpiar todo</button>
            <button type="button" class="ci-iconbtn ci-filters-close" aria-label="Cerrar filtros" @click="closeFilters">
              <AppIcon name="x" :size="16" />
            </button>
          </header>

          <!-- En móvil el panel repite la búsqueda para operarlo completo desde el drawer -->
          <div class="ci-filter-search">
            <label class="sr-only" for="ci-cat-search-panel">Buscar productos</label>
            <input id="ci-cat-search-panel" v-model="ui.search" type="search" placeholder="Buscar…" autocomplete="off" aria-controls="ci-results">
          </div>

          <fieldset v-if="catalog.categories.length" class="ci-filter-group">
            <legend>Categoría</legend>
            <div class="ci-filter-list">
              <label v-for="cat in catalog.categories" :key="cat.id" class="ci-check">
                <input type="checkbox" :checked="activeCategories.includes(cat.id)" @change="pickCategory(cat.id)">
                <span>{{ cat.name }}</span>
                <em>{{ cat.products_count ?? '' }}</em>
              </label>
            </div>
          </fieldset>

          <fieldset v-if="catalog.brands.length" class="ci-filter-group">
            <legend>Marca</legend>
            <div class="ci-filter-list">
              <label v-for="brand in catalog.brands" :key="brand.id" class="ci-check">
                <input type="checkbox" :checked="activeBrands.includes(brand.id)" @change="pickBrand(brand.id)">
                <span>{{ brand.name }}</span>
                <em>{{ brand.products_count ?? '' }}</em>
              </label>
            </div>
          </fieldset>

          <fieldset class="ci-filter-group">
            <legend>Precio</legend>
            <div class="ci-price">
              <label><span class="sr-only">Precio mínimo</span><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mín."></label>
              <label><span class="sr-only">Precio máximo</span><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máx."></label>
            </div>
            <p v-if="hasFilters && (priceMin || priceMax) && priceRangeLabel" class="ci-filter-hint">{{ priceRangeLabel }}</p>
            <p v-else-if="priceBounds" class="ci-filter-hint">{{ priceBounds }}</p>
          </fieldset>

          <fieldset class="ci-filter-group">
            <legend>Disponibilidad</legend>
            <label class="ci-check">
              <input type="checkbox" :checked="onlyOffer" @change="toggleOffer">
              <span>Solo ofertas</span>
              <em v-if="offerTotal">{{ offerTotal }}</em>
            </label>
            <label class="ci-check">
              <input type="checkbox" :checked="onlyNew" @change="toggleNew">
              <span>Novedades (7 días)</span>
              <em v-if="newTotal">{{ newTotal }}</em>
            </label>
          </fieldset>

          <fieldset v-for="facet in facets" :key="facet.name" class="ci-filter-group">
            <legend>{{ facet.name }}</legend>
            <div class="ci-filter-list">
              <label v-for="value in facet.values" :key="value.value" class="ci-check">
                <input type="checkbox" :checked="isFeatureOn(facet.name, value.value)" @change="toggleFeature(facet.name, value.value)">
                <span>{{ value.value }}</span>
                <em>{{ value.count }}</em>
              </label>
            </div>
          </fieldset>

          <p v-if="!catalog.categories.length && !catalog.brands.length && !facets.length" class="ci-filter-hint ci-filter-hint-empty">
            <AppIcon name="terminal" :size="13" aria-hidden="true" />
            Los atributos (RAM, pantalla, etc.) aparecen acá al elegir una categoría.
          </p>

          <button type="button" class="ci-btn ci-filters-apply" @click="closeFilters">Ver resultados</button>
        </aside>

        <!-- Resultados -->
        <section id="ci-results" class="ci-results" aria-labelledby="ci-results-title">
          <div class="ci-results-head">
            <h2 id="ci-results-title" aria-live="polite">{{ productCount }}</h2>
            <label class="ci-sort">
              <span>Ordenar por</span>
              <select v-model="sort">
                <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>

          <ul v-if="activeTags.length" class="ci-tags">
            <li v-for="tag in activeTags" :key="tag.key">
              <button type="button" :aria-label="`Quitar filtro ${tag.label}`" @click="tag.remove()">{{ tag.label }} <AppIcon name="x" :size="12" /></button>
            </li>
            <li class="ci-tags-clear">
              <button type="button" class="ci-tags-clear-btn" @click="clearFilters">Limpiar todo</button>
            </li>
          </ul>

          <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="ci-grid" aria-busy="true">
            <span v-for="n in 6" :key="n" class="ci-skel" aria-hidden="true"></span>
          </div>

          <div v-else-if="catalogStatus === 'error'" class="ci-empty">
            <AppIcon name="circle-alert" :size="26" />
            <strong>No pudimos cargar el catálogo</strong>
            <p>Revisá tu conexión e intentá de nuevo.</p>
            <button type="button" class="ci-btn ghost" @click="loadCatalog">Reintentar</button>
          </div>

          <div v-else-if="catalog.products.length" class="ci-grid">
            <TplProductCard
              v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60"
              class="ci-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
              :index="'#' + String(i + 1).padStart(2, '0')"
              :stars="custom.show_reviews" stars-icon="star" seal-shape="" quick="Ver producto"
              go-label="Ver más" @open="openProduct">
              <template #tags>
                <ul v-if="specChips(p).length" class="ci-card-specs">
                  <li v-for="chip in specChips(p)" :key="chip">{{ chip }}</li>
                </ul>
                <p v-if="productDiscount(p)" class="ci-card-promo">
                  <AppIcon name="tag" :size="11" aria-hidden="true" />
                  {{ productDiscount(p).name }}<span v-if="offerEndsLabel(productDiscount(p))"> · {{ offerEndsLabel(productDiscount(p)) }}</span>
                </p>
              </template>
            </TplProductCard>
          </div>

          <div v-else class="ci-empty">
            <AppIcon :name="hasFilters ? 'search' : 'package'" :size="26" />
            <strong>{{ hasFilters ? 'Sin resultados' : 'Todavía no hay productos publicados' }}</strong>
            <p>{{ hasFilters ? 'Ningún producto coincide con esos filtros. Probá con otra búsqueda o quitá alguno.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
            <button v-if="hasFilters" type="button" class="ci-btn ghost" @click="clearFilters">Limpiar filtros</button>
          </div>

          <div v-if="hasMoreProducts && catalogStatus !== 'error'" class="ci-more">
            <p>{{ shownLabel }}</p>
            <button type="button" class="ci-btn" @click="showMore"><AppIcon name="plus" :size="16" /> Ver más productos</button>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
