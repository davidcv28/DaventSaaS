<script setup>
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { filtersUi, openFilters, hasAnyFilterGroup } from '../../composables/catalogFiltersUi.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogTags from './CatalogTags.vue'
import { useLayout } from '../../composables/useLayout.js'
import '../../assets/store-filters.css'

// Bloques 'filters' y 'sort' del layout de catálogo: el editor los apaga.
const { on } = useLayout('catalog')

// Barra de resultados del catálogo público, alineada con la grilla:
// botón "Filtros (n)" (solo móvil — abre el bottom sheet), contador de
// productos, buscador y selector de orden; debajo los chips removibles
// de filtros activos (CatalogTags). La viste cada plantilla vía tokens
// --cf-* igual que el panel.
const {
  ui, catalog, catalogStatus, priceCeiling, offerTotal, newTotal,
  sort, productCount, activeFilterCount
} = useStoreCatalog()

const hasAny = hasAnyFilterGroup(catalog, priceCeiling, offerTotal, newTotal)
</script>

<template>
<div class="cf-toolbar">
  <div class="cf-toolbar-row">
    <button
      v-if="hasAny && on('filters')"
      type="button" class="cf-open"
      :aria-expanded="filtersUi.open"
      aria-controls="cf-sheet"
      aria-haspopup="dialog"
      @click="openFilters"
    >
      <AppIcon name="sliders" :size="16" aria-hidden="true" />
      Filtros
      <span v-if="activeFilterCount" class="cf-open-n" aria-hidden="true">{{ activeFilterCount }}</span>
    </button>
    <p v-if="catalogStatus === 'success'" class="cf-count-line" role="status" aria-live="polite">{{ productCount }}</p>
    <label class="cf-search">
      <AppIcon name="search" :size="15" aria-hidden="true" />
      <input v-model="ui.search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" @keydown.esc.stop="ui.search = ''" />
      <button v-if="ui.search" type="button" class="cf-search-clear" aria-label="Borrar búsqueda" @click="ui.search = ''"><AppIcon name="x" :size="13" /></button>
    </label>
    <label v-if="on('sort')" class="cf-sort">
      <span class="cf-sort-label">Ordenar</span>
      <select v-model="sort" aria-label="Ordenar productos">
        <option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <AppIcon name="chevron-down" :size="14" class="cf-sort-caret" aria-hidden="true" />
    </label>
  </div>
  <CatalogTags v-if="on('filters')" />
</div>
</template>
