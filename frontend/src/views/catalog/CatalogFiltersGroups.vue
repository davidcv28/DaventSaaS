<script setup>
import { computed, reactive } from 'vue'
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import AppIcon from '../../components/AppIcon.vue'

// Lista de grupos de filtros (acordeones) compartida por la sidebar de
// escritorio y el bottom sheet móvil de CatalogFilters: Categorías,
// Marcas, Precio, Estado y un grupo por cada atributo dinámico (Talle,
// Color, Material...). Solo presentación — consume la misma instancia
// de useStoreCatalog que crea la página.
const {
  catalog, facets, activeCategories, activeBrands,
  pickCategory, pickBrand, pickFeature, isFeatureOn,
  onlyOffer, onlyNew, toggleOffer, toggleNew,
  priceMin, priceMax, priceCeiling,
  offerTotal, newTotal
} = useStoreCatalog()

// Acordeón nativo <details>: el estado inicial se aplica una sola vez
// (mounted) — si se bindeara :open, cada recarga del catálogo volvería a
// plegar lo que el visitante abrió.
const vOpenOnce = {
  mounted(el, binding) { el.open = !!binding.value }
}

// Orden fijo de los grupos: taxonomías primero, precio y estado después,
// atributos dinámicos al final. Si hay más de 4 grupos solo el primero
// arranca abierto; con menos quedan todos desplegados.
const groups = computed(() => {
  const list = []
  if (catalog.value.categories?.length) list.push({ key: 'cats', name: 'Categorías', kind: 'cats', items: catalog.value.categories })
  if (catalog.value.brands?.length) list.push({ key: 'brands', name: 'Marcas', kind: 'brands', items: catalog.value.brands })
  if (priceCeiling.value > 0) list.push({ key: 'price', name: 'Precio', kind: 'price' })
  if (offerTotal.value || newTotal.value) list.push({ key: 'status', name: 'Estado', kind: 'status' })
  for (const f of facets.value) list.push({ key: `f-${f.name}`, name: f.name, kind: 'facet', facet: f })
  return list
})
const startsOpen = (index) => groups.value.length <= 4 || index === 0

// Listas largas: se muestran los primeros 6 valores y el resto se
// despliega con "Ver N más" (estado local por grupo, no filtra datos).
const expanded = reactive({})
const COLLAPSED = 6
const shownItems = (group) => {
  const items = group.items || group.facet?.values || []
  return expanded[group.key] ? items : items.slice(0, COLLAPSED)
}
const hiddenCount = (group) => {
  const items = group.items || group.facet?.values || []
  return Math.max(0, items.length - COLLAPSED)
}

// Faceta de color: los valores se dibujan como swatches. Mapa de
// nombres frecuentes en es-AR a hex; lo que no matchea usa el acento.
const isColorFacet = (name) => /colou?r/i.test(String(name || ''))
const COLOR_HEX = {
  negro: '#17171c', blanco: '#f7f7f4', gris: '#8b8b93', plata: '#c9c9cf', plateado: '#c9c9cf',
  azul: '#2f5fd0', celeste: '#6cb8e8', marino: '#1d2d50', turquesa: '#2ba8a0', cian: '#3cc3d9',
  verde: '#2e8b57', oliva: '#6b7f3a', militar: '#55603c', esmeralda: '#14966b',
  rojo: '#c73a3a', bordo: '#7d2438', burdeo: '#7d2438', vino: '#6e2b42', coral: '#e8674d', ladrillo: '#a5502f',
  rosa: '#e58bb0', fucsia: '#c9359c', violeta: '#7b4fb3', lila: '#b79ad9', purpura: '#6d3fa0',
  amarillo: '#e7c93f', dorado: '#c9a227', mostaza: '#cfa23c', ocre: '#b8862f',
  naranja: '#d9762c', terracota: '#b5654a',
  marron: '#7a5230', camel: '#b78d5e', beige: '#d9c9a8', crema: '#f0e6cf', havana: '#8a6a48',
  denim: '#4a6a96', jean: '#4a6a96', crudo: '#e4dcc9', natural: '#ddd3bd'
}
const swatchHex = (value) => COLOR_HEX[String(value || '').trim().toLowerCase()] || null
const isCatOn = (id) => activeCategories.value.includes(id)
const isBrandOn = (id) => activeBrands.value.includes(id)

// Pista de descubrimiento: categorías con feature_schema pero sin elegir.
const hasSchemaCategories = computed(() => catalog.value.categories?.some((c) => (c.feature_schema || []).length))
const showHint = computed(() => !activeCategories.value.length && hasSchemaCategories.value)
</script>

<template>
<div class="cf-groups">
  <details
    v-for="(g, i) in groups" :key="g.key"
    v-open-once="startsOpen(i)"
    class="cf-group"
  >
    <summary class="cf-gname">
      <span>{{ g.name }}</span>
      <AppIcon name="chevron-down" :size="15" class="cf-gcaret" aria-hidden="true" />
    </summary>

    <!-- Categorías -->
    <div v-if="g.kind === 'cats'" class="cf-opts" role="group" :aria-label="g.name">
      <button
        v-for="c in shownItems(g)" :key="c.id" type="button"
        class="cf-opt" :class="{ on: isCatOn(c.id) }"
        :aria-pressed="isCatOn(c.id)"
        @click="pickCategory(c.id)"
      ><span class="cf-opt-label">{{ c.name }}</span><span class="cf-n" aria-hidden="true">{{ c.products_count ?? 0 }}</span></button>
    </div>

    <!-- Marcas -->
    <div v-else-if="g.kind === 'brands'" class="cf-opts" role="group" :aria-label="g.name">
      <button
        v-for="b in shownItems(g)" :key="b.id" type="button"
        class="cf-opt" :class="{ on: isBrandOn(b.id) }"
        :aria-pressed="isBrandOn(b.id)"
        @click="pickBrand(b.id)"
      ><span class="cf-opt-label">{{ b.name }}</span><span class="cf-n" aria-hidden="true">{{ b.products_count ?? 0 }}</span></button>
    </div>

    <!-- Precio -->
    <div v-else-if="g.kind === 'price'" class="cf-opts" role="group" aria-label="Rango de precios">
      <div class="cf-price">
        <label class="cf-price-field">
          <span class="cf-price-sign" aria-hidden="true">$</span>
          <input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mínimo" aria-label="Precio mínimo" />
        </label>
        <span class="cf-price-sep" aria-hidden="true">–</span>
        <label class="cf-price-field">
          <span class="cf-price-sign" aria-hidden="true">$</span>
          <input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máximo" aria-label="Precio máximo" />
        </label>
      </div>
      <p v-if="priceCeiling" class="cf-price-hint">Hasta {{ priceCeiling.toLocaleString('es-AR') }} en el catálogo</p>
    </div>

    <!-- Estado: oferta / novedades -->
    <div v-else-if="g.kind === 'status'" class="cf-opts" role="group" :aria-label="g.name">
      <button v-if="offerTotal" type="button" class="cf-opt" :class="{ on: onlyOffer }" :aria-pressed="onlyOffer" @click="toggleOffer">
        <span class="cf-opt-label">En oferta</span><span class="cf-n" aria-hidden="true">{{ offerTotal }}</span>
      </button>
      <button v-if="newTotal" type="button" class="cf-opt" :class="{ on: onlyNew }" :aria-pressed="onlyNew" @click="toggleNew">
        <span class="cf-opt-label">Novedades</span><span class="cf-n" aria-hidden="true">{{ newTotal }}</span>
      </button>
    </div>

    <!-- Atributo dinámico (Talle, Color, Material...) -->
    <div v-else class="cf-opts" :class="{ 'cf-opts-chips': isColorFacet(g.name) }" role="group" :aria-label="g.name">
      <template v-if="isColorFacet(g.name)">
        <button
          v-for="opt in shownItems(g)" :key="opt.value" type="button"
          class="cf-opt cf-opt-sw" :class="{ on: isFeatureOn(g.name, opt.value) }"
          :aria-pressed="isFeatureOn(g.name, opt.value)"
          :title="opt.value"
          @click="pickFeature(g.name, opt.value)"
        >
          <span class="cf-sw" :style="{ background: swatchHex(opt.value) || 'var(--cf-accent)' }" aria-hidden="true"></span>
          <span class="cf-opt-label">{{ opt.value }}</span><span class="cf-n" aria-hidden="true">{{ opt.count }}</span>
        </button>
      </template>
      <button
        v-else
        v-for="opt in shownItems(g)" :key="opt.value" type="button"
        class="cf-opt" :class="{ on: isFeatureOn(g.name, opt.value) }"
        :aria-pressed="isFeatureOn(g.name, opt.value)"
        @click="pickFeature(g.name, opt.value)"
      ><span class="cf-opt-label">{{ opt.value }}</span><span class="cf-n" aria-hidden="true">{{ opt.count }}</span></button>
    </div>

    <button
      v-if="hiddenCount(g)" type="button" class="cf-more"
      :aria-expanded="Boolean(expanded[g.key])"
      @click="expanded[g.key] = !expanded[g.key]"
    >{{ expanded[g.key] ? 'Ver menos' : `Ver ${hiddenCount(g)} más` }}</button>
  </details>
  <p v-if="showHint" class="cf-hint">Elegí una categoría para filtrar por sus características.</p>
</div>
</template>
