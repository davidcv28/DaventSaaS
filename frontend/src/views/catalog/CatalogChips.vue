<script setup>
// Riel de filtros rápidos: la variante 'chips' del bloque 'filters' del
// layout de catálogo. Categorías y marcas como chips multi-selección,
// toggles de ofertas/novedades y un acceso al panel completo (el mismo
// bottom sheet de siempre, que además trae precio y facetas). Se monta
// dentro de CatalogToolbar, alineado con la grilla — la sidebar
// (CatalogFilters) se apaga en esta variante.
import { computed } from 'vue'
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { openFilters, hasAnyFilterGroup } from '../../composables/catalogFiltersUi.js'
import AppIcon from '../../components/AppIcon.vue'

const {
  catalog, activeCategories, activeBrands, onlyOffer, onlyNew,
  pickCategory, pickBrand, toggleOffer, toggleNew,
  clearCategories, clearBrands,
  priceCeiling, offerTotal, newTotal
} = useStoreCatalog()

const hasAny = hasAnyFilterGroup(catalog, priceCeiling, offerTotal, newTotal)
const brands = computed(() => (catalog.value.brands || []).slice(0, 6))
const taxActive = computed(() => Boolean(activeCategories.value.length || activeBrands.value.length))
const catOn = (id) => activeCategories.value.includes(id)
const brandOn = (id) => activeBrands.value.includes(id)
function pickAll() { clearCategories(); clearBrands() }
</script>

<template>
<div v-if="hasAny" class="cf-chipbar" role="group" aria-label="Filtros rápidos">
  <button
    type="button" class="cf-chip" :class="{ on: !taxActive }"
    :aria-pressed="!taxActive" @click="pickAll"
  >Todo</button>
  <button
    v-for="c in catalog.categories" :key="`c${c.id}`"
    type="button" class="cf-chip" :class="{ on: catOn(c.id) }"
    :aria-pressed="catOn(c.id)" @click="pickCategory(c.id)"
  >{{ c.name }}</button>
  <span v-if="brands.length" class="cf-chipbar-sep" aria-hidden="true"></span>
  <button
    v-for="b in brands" :key="`b${b.id}`"
    type="button" class="cf-chip" :class="{ on: brandOn(b.id) }"
    :aria-pressed="brandOn(b.id)" @click="pickBrand(b.id)"
  >{{ b.name }}</button>
  <span v-if="offerTotal || newTotal" class="cf-chipbar-sep" aria-hidden="true"></span>
  <button v-if="offerTotal" type="button" class="cf-chip" :class="{ on: onlyOffer }" :aria-pressed="onlyOffer" @click="toggleOffer">
    <AppIcon name="tag" :size="13" aria-hidden="true" />Ofertas
  </button>
  <button v-if="newTotal" type="button" class="cf-chip" :class="{ on: onlyNew }" :aria-pressed="onlyNew" @click="toggleNew">
    <AppIcon name="sparkles" :size="13" aria-hidden="true" />Novedades
  </button>
  <button type="button" class="cf-chip cf-chipbar-more" @click="openFilters">
    <AppIcon name="sliders" :size="13" aria-hidden="true" />Todos los filtros
  </button>
</div>
</template>
