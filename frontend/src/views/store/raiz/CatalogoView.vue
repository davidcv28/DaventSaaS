<script setup>
// Catálogo del diseño RAÍZ v2: encabezado editorial integrado (migas + h1 +
// contadores en una fila), riel de filtros sticky con secciones hairline,
// grilla 3-up 4:5 y estados coherentes. Toda la lógica de filtros/orden/
// búsqueda/paginado la resuelve useStoreCatalog (misma API que el resto de
// la web): acá solo se pinta.
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
  onlyOffer, onlyNew, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, pickFeature, isFeatureOn,
  toggleOffer, toggleNew, clearFilters, hasFilters, activeTags, facets,
  brandNameOf, categoryNameOf, openProduct, shownLabel, shownPct,
  offerTotal, newTotal
} = c

// Panel de filtros plegable (móvil/tablet): conserva los mismos controles
// nativos —checkbox, inputs de precio— para que el teclado y los lectores de
// pantalla funcionen igual que en desktop.
const filtersOpen = ref(false)
const promotions = computed(() => catalog.value.promotions || [])
const priceBounds = computed(() => {
  const max = Number(catalog.value.price_max || 0)
  return max > 0 ? `Hasta ${formatARS(max)}` : ''
})
const productLabel = computed(() => `${catalog.value.products.length} ${catalog.value.products.length === 1 ? 'producto' : 'productos'}`)
const toggleFeature = (name, value) => pickFeature(name, value)
</script>

<template>
  <div class="sp-page-root rz-cat-page">
    <!-- Encabezado: migas, título y contadores en una sola fila editorial -->
    <header class="rz-cat-head">
      <div class="rz-cat-wrap">
        <nav class="rz-cat-crumbs" aria-label="Ruta">
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <span aria-hidden="true">/</span>
          <span aria-current="page">Catálogo</span>
        </nav>
        <div class="rz-cat-head-row">
          <div class="rz-cat-head-copy">
            <p class="rz-eyebrow rz-cat-kicker"><span class="rz-eyebrow-num">01</span> Catálogo</p>
            <h1 class="rz-cat-title">Catálogo<span aria-hidden="true">.</span></h1>
            <p class="rz-cat-lead">Todo lo que {{ shopName }} tiene para ofrecerte, en un solo lugar.</p>
          </div>
          <dl class="rz-cat-counts" aria-label="Contenido del catálogo">
            <div>
              <dt>Productos</dt>
              <dd>{{ catalog.products.length }}</dd>
            </div>
            <div>
              <dt>Categorías</dt>
              <dd>{{ catalog.categories.length }}</dd>
            </div>
            <div>
              <dt>Marcas</dt>
              <dd>{{ catalog.brands.length }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </header>

    <!-- Promociones vigentes: tira hairline, no tarjeta flotante -->
    <div v-if="promotions.length" class="rz-cat-promos" role="status">
      <div class="rz-cat-wrap rz-cat-promos-inner">
        <span class="rz-cat-promos-label">Promociones vigentes</span>
        <ul>
          <li v-for="promo in promotions" :key="promo.id || promo.name">
            <strong>{{ promo.name }}</strong> · -{{ promo.percent }}%
            <span v-if="offerEndsLabel(promo)"> · {{ offerEndsLabel(promo) }}</span>
          </li>
        </ul>
      </div>
    </div>

    <main class="rz-cat-wrap rz-cat-main">
      <div class="rz-cat-body">
        <!-- Filtros: riel sticky de 280 con secciones hairline -->
        <button
          type="button" class="rz-cat-filters-toggle" :aria-expanded="filtersOpen"
          aria-controls="rz-cat-filters" @click="filtersOpen = !filtersOpen"
        >
          <AppIcon name="sliders" :size="16" aria-hidden="true" /> Filtros
          <span v-if="activeTags.length" class="rz-cat-filters-count">{{ activeTags.length }}</span>
        </button>

        <aside
          id="rz-cat-filters" class="rz-cat-rail" :class="{ 'is-open': filtersOpen }"
          aria-label="Filtros del catálogo" @keydown.esc="filtersOpen = false"
        >
          <div class="rz-cat-rail-head">
            <p class="rz-eyebrow"><span class="rz-eyebrow-num">02</span> Filtrar</p>
            <div class="rz-cat-rail-actions">
              <button type="button" class="rz-cat-linkbtn" :disabled="!hasFilters" @click="clearFilters">Limpiar</button>
              <button type="button" class="rz-cat-rail-close" aria-label="Cerrar filtros" @click="filtersOpen = false">
                <AppIcon name="x" :size="16" />
              </button>
            </div>
          </div>

          <fieldset v-if="catalog.categories.length" class="rz-cat-group">
            <legend>Categoría</legend>
            <label v-for="cat in catalog.categories" :key="cat.id" class="rz-cat-check">
              <input type="checkbox" :checked="activeCategories.includes(cat.id)" @change="pickCategory(cat.id)" />
              <span class="rz-cat-check-label">{{ cat.name }}</span>
              <em>{{ cat.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset v-if="catalog.brands.length" class="rz-cat-group">
            <legend>Marca</legend>
            <label v-for="brand in catalog.brands" :key="brand.id" class="rz-cat-check">
              <input type="checkbox" :checked="activeBrands.includes(brand.id)" @change="pickBrand(brand.id)" />
              <span class="rz-cat-check-label">{{ brand.name }}</span>
              <em>{{ brand.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset class="rz-cat-group">
            <legend>Precio</legend>
            <div class="rz-cat-prices">
              <label class="rz-cat-pricelabel">
                <span class="rz-cat-pricetag" aria-hidden="true">Mín.</span>
                <span class="sr-only">Precio mínimo</span>
                <input v-model="priceMin" class="rz-field" type="text" inputmode="decimal" placeholder="0" />
              </label>
              <label class="rz-cat-pricelabel">
                <span class="rz-cat-pricetag" aria-hidden="true">Máx.</span>
                <span class="sr-only">Precio máximo</span>
                <input v-model="priceMax" class="rz-field" type="text" inputmode="decimal" placeholder="—" />
              </label>
            </div>
            <p v-if="priceBounds" class="rz-cat-hint">{{ priceBounds }}</p>
          </fieldset>

          <fieldset class="rz-cat-group rz-cat-group--flags">
            <legend>Selección</legend>
            <label class="rz-cat-check">
              <input type="checkbox" :checked="onlyOffer" @change="toggleOffer" />
              <span class="rz-cat-check-label">Solo ofertas</span>
              <em v-if="offerTotal">{{ offerTotal }}</em>
            </label>
            <label class="rz-cat-check">
              <input type="checkbox" :checked="onlyNew" @change="toggleNew" />
              <span class="rz-cat-check-label">Novedades (7 días)</span>
              <em v-if="newTotal">{{ newTotal }}</em>
            </label>
          </fieldset>

          <fieldset v-for="facet in facets" :key="facet.name" class="rz-cat-group">
            <legend>{{ facet.name }}</legend>
            <label v-for="value in facet.values" :key="value.value" class="rz-cat-check">
              <input type="checkbox" :checked="isFeatureOn(facet.name, value.value)" @change="toggleFeature(facet.name, value.value)" />
              <span class="rz-cat-check-label">{{ value.value }}</span>
              <em>{{ value.count }}</em>
            </label>
          </fieldset>

          <p v-if="!catalog.categories.length && !catalog.brands.length && !facets.length" class="rz-cat-hint">
            Los atributos (ej. Talle, Color) aparecen acá al elegir una categoría.
          </p>

          <button type="button" class="rz-btn rz-cat-apply" @click="filtersOpen = false">Ver resultados</button>
        </aside>

        <!-- Resultados -->
        <section class="rz-cat-results" aria-labelledby="rz-cat-results-title">
          <div class="rz-cat-res-head">
            <div class="rz-cat-res-copy">
              <p class="rz-eyebrow"><span class="rz-eyebrow-num">03</span> Resultados</p>
              <h2 id="rz-cat-results-title">{{ productLabel }}</h2>
            </div>
            <label class="rz-cat-sort">
              <span>Ordenar</span>
              <select v-model="sort">
                <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>

          <ul v-if="activeTags.length" class="rz-cat-tags" aria-label="Filtros activos">
            <li v-for="tag in activeTags" :key="tag.key">
              <button type="button" @click="tag.remove()">{{ tag.label }} <AppIcon name="x" :size="12" aria-hidden="true" /></button>
            </li>
          </ul>

          <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="rz-cat-products" aria-busy="true">
            <span v-for="n in 6" :key="n" class="rz-cat-skel" aria-hidden="true">
              <span class="rz-cat-skel-media"></span>
              <span class="rz-cat-skel-line"></span>
              <span class="rz-cat-skel-line short"></span>
            </span>
          </div>

          <div v-else-if="catalogStatus === 'error'" class="rz-cat-empty">
            <span class="rz-cat-empty-ico" aria-hidden="true"><AppIcon name="circle-alert" :size="26" /></span>
            <strong>No pudimos cargar el catálogo</strong>
            <p>Revisá tu conexión e intentá de nuevo.</p>
            <button type="button" class="rz-btn rz-btn--ghost" @click="loadCatalog">Reintentar</button>
          </div>

          <div v-else-if="catalog.products.length" class="rz-cat-products">
            <TplProductCard
              v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60"
              class="rz-cat-card" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
              :stars="custom.show_reviews" stars-icon="star" quick="Ver producto"
              go-label="Ver" seal-shape="" @open="openProduct"
            >
              <template v-if="productDiscount(p)" #tags>
                <p class="rz-cat-card-promo">{{ productDiscount(p).name }}<span v-if="offerEndsLabel(productDiscount(p))"> · {{ offerEndsLabel(productDiscount(p)) }}</span></p>
              </template>
            </TplProductCard>
          </div>

          <div v-else class="rz-cat-empty">
            <span class="rz-cat-empty-ico" aria-hidden="true"><AppIcon :name="hasFilters ? 'search' : 'package'" :size="26" /></span>
            <strong>{{ hasFilters ? 'Sin resultados' : 'Todavía no hay productos publicados' }}</strong>
            <p>{{ hasFilters ? 'Ningún producto coincide con esos filtros. Probá con otra búsqueda o quitá alguno.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
            <button v-if="hasFilters" type="button" class="rz-btn rz-btn--ghost" @click="clearFilters">Limpiar filtros</button>
          </div>

          <div v-if="hasMoreProducts && catalogStatus !== 'error'" class="rz-cat-more">
            <p class="rz-cat-more-label">{{ shownLabel }}</p>
            <div class="rz-cat-more-bar" aria-hidden="true"><span :style="{ width: shownPct }"></span></div>
            <button type="button" class="rz-btn" @click="showMore"><AppIcon name="plus" :size="16" aria-hidden="true" /> Ver más productos</button>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
