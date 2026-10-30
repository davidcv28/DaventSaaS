<script setup>
// Catálogo del diseño ALIMENTOS: encabezado con migas + contadores, franja de
// promociones vigentes, panel de filtros (categorías, marcas, precio,
// ofertas/novedades y atributos) y grilla de 3 columnas con la tarjeta firma
// (precio + CTA WhatsApp). Toda la lógica —filtros, orden, búsqueda, facetas y
// paginado— sale de useStoreCatalog: acá solo se pinta, igual que en el resto
// de la web pública. La piel vive en store-alimentos.css bajo `.al-cat`.
import { ref, computed } from 'vue'
import { formatARS } from '../../../api/billing.api.js'
import { offerEndsLabel } from '../../../api/catalog.api.js'
import { useStoreCatalog, SORT_OPTIONS } from '../../../composables/useStoreCatalog.js'
import AlProductCard from './AlProductCard.vue'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const c = useStoreCatalog({ pageSize: 12 })
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  activeCategories, activeBrands, onlyOffer, onlyNew, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, pickFeature,
  isFeatureOn, toggleOffer, toggleNew, clearFilters, hasFilters, activeTags, facets,
  brandNameOf, categoryNameOf, openProduct, shownLabel, askUrl, offerTotal, newTotal
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
  <div class="sp-page-root al-cat">
    <header class="al-cat-head">
      <div class="al-container">
        <nav class="al-crumbs" aria-label="Ruta">
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <span aria-hidden="true">/</span>
          <span aria-current="page">Catálogo</span>
        </nav>
        <div class="al-cat-head-row">
          <div>
            <p class="al-eyebrow">Para pedir hoy</p>
            <h1 class="al-cat-title">Catálogo</h1>
            <p class="al-cat-lead">Todo lo que {{ shopName }} tiene para ofrecerte, listo para pedir por WhatsApp.</p>
          </div>
          <ul class="al-cat-counts" aria-label="Contenido del catálogo">
            <li><strong>{{ catalog.products.length }}</strong><span>{{ catalog.products.length === 1 ? 'producto' : 'productos' }}</span></li>
            <li><strong>{{ catalog.categories.length }}</strong><span>{{ catalog.categories.length === 1 ? 'categoría' : 'categorías' }}</span></li>
            <li><strong>{{ offerTotal }}</strong><span>en oferta</span></li>
          </ul>
        </div>
      </div>
    </header>

    <main class="al-container al-cat-main">
      <div v-if="promotions.length" class="al-cat-promos" role="status">
        <strong class="al-cat-promos-label">Promociones vigentes</strong>
        <ul>
          <li v-for="promo in promotions" :key="promo.id || promo.name">
            {{ promo.name }} · -{{ promo.percent }}%
            <span v-if="offerEndsLabel(promo)"> · {{ offerEndsLabel(promo) }}</span>
          </li>
        </ul>
      </div>

      <div class="al-cat-body">
        <button
          type="button" class="al-filters-toggle" :aria-expanded="filtersOpen" aria-controls="al-filters"
          @click="filtersOpen = !filtersOpen"
        >
          <AppIcon name="sliders" :size="16" aria-hidden="true" /> Filtros
          <span v-if="activeTags.length" class="al-filters-count">{{ activeTags.length }}</span>
        </button>

        <aside id="al-filters" class="al-filters" :class="{ open: filtersOpen }" aria-label="Filtros del catálogo">
          <header class="al-filters-head">
            <strong>Filtros</strong>
            <button type="button" class="al-linkbtn" :disabled="!hasFilters" @click="clearFilters">Limpiar</button>
          </header>

          <fieldset v-if="catalog.categories.length" class="al-filter-group">
            <legend>Categoría</legend>
            <label v-for="cat in catalog.categories" :key="cat.id" class="al-check">
              <input type="checkbox" :checked="activeCategories.includes(cat.id)" @change="pickCategory(cat.id)" />
              <span>{{ cat.name }}</span>
              <em>{{ cat.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset v-if="catalog.brands.length" class="al-filter-group">
            <legend>Marca</legend>
            <label v-for="brand in catalog.brands" :key="brand.id" class="al-check">
              <input type="checkbox" :checked="activeBrands.includes(brand.id)" @change="pickBrand(brand.id)" />
              <span>{{ brand.name }}</span>
              <em>{{ brand.products_count ?? '' }}</em>
            </label>
          </fieldset>

          <fieldset class="al-filter-group">
            <legend>Precio</legend>
            <div class="al-price">
              <label><span class="sr-only">Precio mínimo</span><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mín." /></label>
              <label><span class="sr-only">Precio máximo</span><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máx." /></label>
            </div>
            <p v-if="priceBounds" class="al-filter-hint">{{ priceBounds }}</p>
          </fieldset>

          <fieldset class="al-filter-group al-filter-group--flags">
            <label class="al-check"><input type="checkbox" :checked="onlyOffer" @change="toggleOffer" /><span>Solo ofertas <em>{{ offerTotal }}</em></span></label>
            <label class="al-check"><input type="checkbox" :checked="onlyNew" @change="toggleNew" /><span>Novedades (7 días) <em>{{ newTotal }}</em></span></label>
          </fieldset>

          <fieldset v-for="facet in facets" :key="facet.name" class="al-filter-group">
            <legend>{{ facet.name }}</legend>
            <label v-for="value in facet.values" :key="value.value" class="al-check">
              <input type="checkbox" :checked="isFeatureOn(facet.name, value.value)" @change="toggleFeature(facet.name, value.value)" />
              <span>{{ value.value }}</span>
              <em>{{ value.count }}</em>
            </label>
          </fieldset>

          <p v-if="!catalog.categories.length && !catalog.brands.length && !facets.length" class="al-filter-hint">
            Los atributos (ej. presentación, relleno) aparecen acá al elegir una categoría.
          </p>

          <button type="button" class="al-btn al-btn--accent al-filters-apply" @click="filtersOpen = false">Ver resultados</button>
        </aside>

        <section class="al-cat-results" aria-labelledby="al-results-title">
          <div class="al-results-head">
            <div>
              <p class="al-eyebrow">{{ shownLabel }}</p>
              <h2 id="al-results-title" class="al-results-title">
                {{ hasFilters ? 'Resultados' : 'El menú completo' }}
              </h2>
            </div>
            <label class="al-sort">
              <span>Ordenar por</span>
              <select v-model="sort">
                <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>

          <ul v-if="activeTags.length" class="al-tags" aria-label="Filtros activos">
            <li v-for="tag in activeTags" :key="tag.key">
              <button type="button" @click="tag.remove()">{{ tag.label }} <AppIcon name="x" :size="12" aria-hidden="true" /></button>
            </li>
          </ul>

          <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="al-cat-grid" aria-busy="true">
            <span v-for="n in 6" :key="n" class="al-skel" aria-hidden="true"></span>
          </div>

          <div v-else-if="catalogStatus === 'error'" class="al-empty">
            <AppIcon name="circle-alert" :size="26" aria-hidden="true" />
            <strong>No pudimos cargar el catálogo</strong>
            <p>Revisá tu conexión e intentá de nuevo.</p>
            <button type="button" class="al-btn al-btn--ghost" @click="loadCatalog">Reintentar</button>
          </div>

          <div v-else-if="catalog.products.length" class="al-cat-grid">
            <AlProductCard
              v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 60"
              :p="p" :cat="categoryNameOf(p) || brandNameOf(p)" :href="askUrl(p)" @open="openProduct"
            />
          </div>

          <div v-else class="al-empty">
            <AppIcon name="package" :size="26" aria-hidden="true" />
            <strong>{{ hasFilters ? 'Sin resultados' : 'Todavía no hay productos publicados' }}</strong>
            <p>{{ hasFilters ? 'Ningún producto coincide con esos filtros. Probá con otra búsqueda o quitá alguno.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
            <button v-if="hasFilters" type="button" class="al-btn al-btn--ghost" @click="clearFilters">Limpiar filtros</button>
          </div>

          <div v-if="hasMoreProducts && catalogStatus !== 'error'" class="al-more">
            <button type="button" class="al-btn al-btn--dark" @click="showMore">
              <AppIcon name="plus" :size="16" aria-hidden="true" /> Ver más productos
            </button>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
