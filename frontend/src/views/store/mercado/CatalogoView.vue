<script setup>
// Catálogo del diseño BAZAR (mercado): migas, riel de filtros tipo
// marketplace (categorías, marcas, precio con "Aplicar" y ofertas), barra de
// resultados con orden y vista lista/grilla, y paginado por páginas.
// La lógica de filtros/orden/búsqueda la resuelve useStoreCatalog (misma API
// que el resto de la web): acá se pinta y se pagina en el cliente, porque el
// catálogo público llega completo en una sola respuesta.
import { ref, computed, inject, nextTick, watch } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { productDiscount, offerEndsLabel, offerPct } from '../../../api/catalog.api.js'
import { useStoreCatalog, SORT_OPTIONS } from '../../../composables/useStoreCatalog.js'
import { templateBlock } from '../../../templates/index.js'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import AppIcon from '../../../components/AppIcon.vue'
import { useCardTitles } from './useCardTitles.js'

const ctx = inject('storePage')
const { custom, shopName, slug, ui } = ctx
// enabled de cada bloque del catálogo según layout_config (editor "Qué mostrar").
const blkOn = (id) => templateBlock(ctx.pageTemplate.value, 'catalog', id, ctx.custom.value?.layout_config).enabled !== false
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const c = useStoreCatalog({ pageSize: 24 })
const {
  catalog, catalogStatus, loadCatalog, activeCategories, activeBrands,
  onlyOffer, onlyNew, onlyEvent, priceMin, priceMax, sort, hasFilters,
  pickCategory, pickBrand, toggleOffer, toggleNew, toggleEvent, clearFilters, clearCategories,
  brandNameOf, categoryNameOf, openProduct, activeCategoryName, eventTotal
} = c

const pageEl = ref(null)
useCardTitles(pageEl)

// ===== Paginado (páginas de 24, como el listado del marketplace) =====
const perPage = 24
const page = ref(1)
const resultsTop = ref(null)
const total = computed(() => catalog.value.products.length)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))
const pagedProducts = computed(() => catalog.value.products.slice((page.value - 1) * perPage, page.value * perPage))
const countLabel = computed(() => `${total.value} ${total.value === 1 ? 'resultado' : 'resultados'}`)
watch(() => catalog.value, () => { page.value = 1 })
watch([activeCategories, activeBrands, onlyOffer, onlyNew, onlyEvent], () => { page.value = 1 })
const pageItems = computed(() => {
  const n = totalPages.value
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1)
  const cur = page.value
  const items = [1]
  if (cur > 3) items.push('…')
  for (let p = Math.max(2, cur - 1); p <= Math.min(n - 1, cur + 1); p++) items.push(p)
  if (cur < n - 2) items.push('…')
  items.push(n)
  return items
})
function goPage(next) {
  const p = Number(next)
  if (!Number.isInteger(p) || p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  nextTick(() => resultsTop.value?.scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' }))
}

// ===== Precio: el rango se confirma con "Aplicar" (no en cada tecla) =====
const minDraft = ref(priceMin.value || '')
const maxDraft = ref(priceMax.value || '')
watch([priceMin, priceMax], ([min, max]) => {
  minDraft.value = min || ''
  maxDraft.value = max || ''
})
function applyPrice() {
  priceMin.value = minDraft.value
  priceMax.value = maxDraft.value
}

// ===== Filtros en móvil: panel plegable arriba de los resultados =====
const filtersOpen = ref(false)
const filtersToggle = ref(null)
const filtersCount = computed(() =>
  activeCategories.value.length + activeBrands.value.length + (onlyOffer.value ? 1 : 0) +
  (onlyNew.value ? 1 : 0) + (onlyEvent.value ? 1 : 0) +
  ((priceMin.value !== '' || priceMax.value !== '') ? 1 : 0) + (ui.search.trim() ? 1 : 0)
)
function closeFilters() {
  if (!filtersOpen.value) return
  filtersOpen.value = false
  nextTick(() => filtersToggle.value?.focus())
}
function clearAll() {
  clearFilters()
  minDraft.value = ''
  maxDraft.value = ''
}

// ===== Marcas: las primeras 6 y "Ver todas" =====
const brandsOpen = ref(false)
const visibleBrands = computed(() => {
  const rows = catalog.value.brands
  return brandsOpen.value ? rows : rows.slice(0, 6)
})

// ===== Vista lista / grilla =====
const view = ref('grid')
const crumb = computed(() => activeCategoryName.value || ui.search.trim() || 'Todos los productos')
const promoOf = (p) => productDiscount(p)
const pctOf = (p) => offerPct(p)

// ===== Chips de filtros activos (misma lectura que el documento del diseño) =====
const activeChips = computed(() => {
  const chips = []
  for (const id of activeCategories.value) {
    const cat = catalog.value.categories.find((c) => c.id === id)
    chips.push({ key: `c-${id}`, tag: 'Categoría', label: cat?.name || 'Categoría', remove: () => pickCategory(id) })
  }
  for (const id of activeBrands.value) {
    const brand = catalog.value.brands.find((b) => b.id === id)
    chips.push({ key: `b-${id}`, tag: 'Marca', label: brand?.name || 'Marca', remove: () => pickBrand(id) })
  }
  if (onlyOffer.value) chips.push({ key: 'offer', tag: 'Oferta', label: 'Solo ofertas', remove: () => toggleOffer() })
  if (onlyNew.value) chips.push({ key: 'new', tag: 'Novedad', label: 'Novedades', remove: () => toggleNew() })
  if (onlyEvent.value) chips.push({ key: 'event', tag: 'Evento', label: 'En evento', remove: () => toggleEvent() })
  if (priceMin.value !== '' || priceMax.value !== '') {
    chips.push({
      key: 'price', tag: 'Precio',
      label: `${priceMin.value === '' ? '0' : priceMin.value} – ${priceMax.value === '' ? '∞' : priceMax.value}`,
      remove: () => { priceMin.value = ''; priceMax.value = ''; minDraft.value = ''; maxDraft.value = '' }
    })
  }
  if (ui.search.trim()) {
    chips.push({ key: 'q', tag: 'Búsqueda', label: `“${ui.search.trim()}”`, remove: () => { ui.search = '' } })
  }
  return chips
})
</script>

<template>
  <div ref="pageEl" class="sp-page-root mc-catpage">
    <div class="mc-wrap">
      <nav class="mc-cat-crumbs" aria-label="Ruta">
        <RouterLink :to="homeTo">Inicio</RouterLink>
        <span aria-hidden="true">›</span>
        <span>Catálogo</span>
        <span aria-hidden="true">›</span>
        <strong aria-current="page">{{ crumb }}</strong>
      </nav>

      <div class="mc-cat-layout">
        <button
          v-if="blkOn('filters')"
          ref="filtersToggle" type="button" class="mc-cat-filters-toggle"
          :aria-expanded="filtersOpen" aria-controls="mc-cat-filters" @click="filtersOpen = !filtersOpen"
        >
          <AppIcon name="sliders" :size="16" aria-hidden="true" /> Filtros
          <span v-if="filtersCount" class="mc-cat-filters-count">{{ filtersCount }}</span>
        </button>

        <aside v-if="blkOn('filters')" id="mc-cat-filters" class="mc-cat-aside" :class="{ 'is-open': filtersOpen }" aria-label="Filtros del catálogo">
          <div class="mc-cat-aside-head">
            <strong>Filtros</strong>
            <button type="button" class="mc-cat-aside-close" aria-label="Cerrar filtros" @click="closeFilters">
              <AppIcon name="x" :size="18" />
            </button>
          </div>

          <section class="mc-f-group">
            <h2 class="mc-f-title">Categorías</h2>
            <div class="mc-f-list">
              <button
                type="button" class="mc-f-cat" :class="{ 'is-active': !activeCategories.length }"
                :aria-pressed="!activeCategories.length" @click="clearCategories()"
              >
                <span>Todas las categorías</span>
              </button>
              <button
                v-for="cat in catalog.categories" :key="cat.id" type="button" class="mc-f-cat"
                :class="{ 'is-active': activeCategories.includes(cat.id) }"
                :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)"
              >
                <span>{{ cat.name }}</span><em>{{ cat.products_count ?? '' }}</em>
              </button>
            </div>
          </section>

          <section v-if="catalog.brands.length" class="mc-f-group">
            <h2 class="mc-f-title">Marcas</h2>
            <div class="mc-f-list">
              <label v-for="brand in visibleBrands" :key="brand.id" class="mc-f-check">
                <input type="checkbox" :checked="activeBrands.includes(brand.id)" @change="pickBrand(brand.id)" />
                <span>{{ brand.name }}</span><em>{{ brand.products_count ?? '' }}</em>
              </label>
            </div>
            <button v-if="catalog.brands.length > 6" type="button" class="mc-f-more" @click="brandsOpen = !brandsOpen">
              {{ brandsOpen ? 'Ver menos' : 'Ver todas las marcas' }}
            </button>
          </section>

          <section class="mc-f-group">
            <h2 class="mc-f-title">Precio</h2>
            <div class="mc-f-price">
              <label class="mc-f-price-field">
                <span class="sr-only">Precio mínimo</span>
                <input v-model="minDraft" type="text" inputmode="decimal" placeholder="Desde" @keydown.enter.prevent="applyPrice" />
              </label>
              <span class="mc-f-price-dash" aria-hidden="true">—</span>
              <label class="mc-f-price-field">
                <span class="sr-only">Precio máximo</span>
                <input v-model="maxDraft" type="text" inputmode="decimal" placeholder="Hasta" @keydown.enter.prevent="applyPrice" />
              </label>
            </div>
            <button type="button" class="mc-f-apply" @click="applyPrice">Aplicar</button>
          </section>

          <section class="mc-f-group">
            <h2 class="mc-f-title">Ofertas</h2>
            <label class="mc-f-check">
              <input type="checkbox" :checked="onlyOffer" @change="toggleOffer" />
              <span>Solo ofertas</span>
            </label>
            <label v-if="eventTotal" class="mc-f-check">
              <input type="checkbox" :checked="onlyEvent" @change="toggleEvent" />
              <span>En evento<em v-if="eventTotal">{{ eventTotal }}</em></span>
            </label>
          </section>

          <div class="mc-cat-aside-foot">
            <button type="button" class="mc-f-clear" :disabled="!hasFilters" @click="clearAll">Limpiar filtros</button>
            <button type="button" class="mc-f-done" @click="closeFilters">Aplicar</button>
          </div>
        </aside>

        <section class="mc-cat-results" aria-labelledby="mc-cat-count">
          <div ref="resultsTop" class="mc-cat-bar">
            <h1 id="mc-cat-count" class="mc-cat-count" aria-live="polite">{{ countLabel }}</h1>
            <div class="mc-cat-view" role="group" aria-label="Vista de resultados">
              <button type="button" :aria-pressed="view === 'list'" aria-label="Ver como lista" title="Vista de lista" @click="view = 'list'">
                <AppIcon name="rows-3" :size="16" aria-hidden="true" />
              </button>
              <button type="button" :aria-pressed="view === 'grid'" aria-label="Ver como grilla" title="Vista de grilla" @click="view = 'grid'">
                <AppIcon name="layout-grid" :size="16" aria-hidden="true" />
              </button>
            </div>
            <label v-if="blkOn('sort')" class="mc-cat-sort">
              <span>Ordenar por</span>
              <select v-model="sort">
                <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </label>
          </div>

          <div v-if="activeChips.length" class="mc-cat-chips">
            <button
              v-for="chip in activeChips" :key="chip.key" type="button" class="mc-chip"
              :aria-label="`Quitar filtro ${chip.tag}: ${chip.label}`" @click="chip.remove()"
            >
              <b>{{ chip.tag }}</b><span>{{ chip.label }}</span><i aria-hidden="true">×</i>
            </button>
            <button v-if="activeChips.length > 1" type="button" class="mc-chip-clear" @click="clearAll">Limpiar todo</button>
          </div>

          <div v-if="(catalogStatus === 'loading' || catalogStatus === 'idle') && !total" class="mc-cat-list" aria-busy="true">
            <span v-for="n in 4" :key="n" class="mc-cat-skel" aria-hidden="true">
              <span class="mc-cat-skel-media"></span>
              <span class="mc-cat-skel-copy">
                <span class="mc-cat-skel-line short"></span>
                <span class="mc-cat-skel-line"></span>
                <span class="mc-cat-skel-line price"></span>
              </span>
            </span>
          </div>

          <div v-else-if="catalogStatus === 'error'" class="mc-cat-empty">
            <span class="mc-cat-empty-ico" aria-hidden="true"><AppIcon name="circle-alert" :size="26" /></span>
            <strong>No pudimos cargar el catálogo</strong>
            <p>Revisá tu conexión e intentá de nuevo.</p>
            <button type="button" class="mc-btn mc-btn--ghost" @click="loadCatalog">Reintentar</button>
          </div>

          <div v-else-if="total" class="mc-cat-list" :data-view="view">
            <TplProductCard
              v-for="p in pagedProducts" :key="p.id" class="mc-cat-card"
              :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)" :desc="p.description || ''"
              :layout="view === 'list' ? 'row' : 'card'"
              :stars="custom.show_reviews" stars-icon="star" stars-value stars-always
              seal-shape="" @open="openProduct"
            >
              <template #foot="{ p, price, oldPrice, offer }">
                <span class="tpc-price-wrap mc-price">
                  <s v-if="offer != null" class="mc-price-old">{{ oldPrice }}</s>
                  <span class="mc-price-line">
                    <strong :class="{ deal: offer != null }">{{ price }}</strong>
                    <em v-if="offer != null" class="mc-off">{{ pctOf(p) }}% OFF</em>
                  </span>
                </span>
              </template>
              <template #tags="{ p }">
                <span v-if="brandNameOf(p)" class="mc-brand">{{ brandNameOf(p) }} <i aria-hidden="true">✓</i></span>
                <p v-if="promoOf(p) && blkOn('promo')" class="mc-cat-promo">{{ promoOf(p).name }}<span v-if="offerEndsLabel(promoOf(p))"> · {{ offerEndsLabel(promoOf(p)) }}</span></p>
              </template>
            </TplProductCard>
          </div>

          <div v-else class="mc-cat-empty">
            <span class="mc-cat-empty-ico" aria-hidden="true"><AppIcon :name="hasFilters ? 'search' : 'package'" :size="26" /></span>
            <strong>{{ hasFilters ? 'No hay publicaciones que coincidan con tu búsqueda' : 'Todavía no hay productos publicados' }}</strong>
            <p>{{ hasFilters ? 'Probá con otras palabras o quitá algunos filtros.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
            <button v-if="hasFilters" type="button" class="mc-btn mc-btn--ghost" @click="clearAll">Limpiar filtros</button>
          </div>

          <nav v-if="totalPages > 1" class="mc-cat-pager" aria-label="Paginación">
            <button type="button" class="mc-pager-arrow" :disabled="page === 1" aria-label="Página anterior" @click="goPage(page - 1)">
              <AppIcon name="chevron-left" :size="16" aria-hidden="true" />
            </button>
            <template v-for="(item, i) in pageItems" :key="`${item}-${i}`">
              <span v-if="item === '…'" class="mc-pager-gap" aria-hidden="true">…</span>
              <button
                v-else type="button" class="mc-pager-num" :class="{ 'is-current': item === page }"
                :aria-current="item === page ? 'page' : null" @click="goPage(item)"
              >{{ item }}</button>
            </template>
            <button type="button" class="mc-pager-arrow" :disabled="page === totalPages" aria-label="Página siguiente" @click="goPage(page + 1)">
              <AppIcon name="chevron-right" :size="16" aria-hidden="true" />
            </button>
          </nav>

          <p v-if="totalPages > 1" class="mc-cat-range">
            Mostrando {{ (page - 1) * perPage + 1 }}–{{ Math.min(page * perPage, total) }} de {{ total }}
          </p>
        </section>
      </div>
    </div>
  </div>
</template>
