<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../../AppIcon.vue'

// Barra de herramientas del listado de productos, en dos niveles:
// fila principal = búsqueda + orden + toggle de filtros + vista;
// los filtros (categoría, marca, solo ofertas) quedan plegados detrás del
// botón "Filtros" para no abrumar a quien recién empieza.
// Solo presentación: el estado vive en DashboardView (v-model por prop).
const props = defineProps({
  query: { type: String, default: '' },
  category: { type: [Number, String], default: '' },
  brand: { type: [Number, String], default: '' },
  onlyOffers: { type: Boolean, default: false },
  sort: { type: String, default: 'newest' },
  view: { type: String, default: 'grid' },
  categories: { type: Array, default: () => [] },
  brands: { type: Array, default: () => [] },
  shown: { type: Number, default: 0 },
  total: { type: Number, default: 0 }
})
const emit = defineEmits([
  'update:query', 'update:category', 'update:brand',
  'update:onlyOffers', 'update:sort', 'update:view', 'new'
])

const SORTS = [
  { value: 'newest', label: 'Más nuevos' },
  { value: 'name', label: 'Nombre (A-Z)' },
  { value: 'price', label: 'Menor precio' },
  { value: 'discount', label: 'Mayor descuento' }
]

const filtersOpen = ref(false)
const activeFilters = computed(() =>
  [props.category, props.brand].filter(Boolean).length + (props.onlyOffers ? 1 : 0)
)
</script>

<template>
  <div class="ctoolbar" role="search">
    <div class="ctoolbar-row">
      <label class="ctoolbar-search">
        <AppIcon name="search" :size="16" aria-hidden="true" />
        <input
          :value="query" type="search" placeholder="Buscar producto…"
          aria-label="Buscar productos" @input="emit('update:query', $event.target.value)"
        />
      </label>
      <select
        class="select ctoolbar-sel ctoolbar-sort" :value="sort" aria-label="Ordenar productos"
        @change="emit('update:sort', $event.target.value)"
      >
        <option v-for="s in SORTS" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <button
        type="button" class="ctoolbar-toggle ctoolbar-filters" :class="{ on: filtersOpen || activeFilters }"
        :aria-expanded="filtersOpen" @click="filtersOpen = !filtersOpen"
      >
        <AppIcon name="sliders" :size="14" aria-hidden="true" /> Filtros
        <span v-if="activeFilters" class="ctoolbar-fbadge">{{ activeFilters }}</span>
      </button>
      <span class="ctoolbar-count" aria-live="polite">{{ shown }} de {{ total }}</span>
      <span class="ctoolbar-views" role="group" aria-label="Cambiar vista">
        <button
          type="button" class="ctoolbar-view" :class="{ on: view === 'grid' }"
          :aria-pressed="view === 'grid'" title="Vista en grilla" @click="emit('update:view', 'grid')"
        ><AppIcon name="layout-grid" :size="16" /></button>
        <button
          type="button" class="ctoolbar-view" :class="{ on: view === 'table' }"
          :aria-pressed="view === 'table'" title="Vista tabla" @click="emit('update:view', 'table')"
        ><AppIcon name="rows-3" :size="16" /></button>
      </span>
    </div>
    <div v-if="filtersOpen" class="ctoolbar-row ctoolbar-frow">
      <select
        class="select ctoolbar-sel" :value="category" aria-label="Filtrar por categoría"
        @change="emit('update:category', $event.target.value)"
      >
        <option value="">Todas las categorías</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <select
        class="select ctoolbar-sel" :value="brand" aria-label="Filtrar por marca"
        @change="emit('update:brand', $event.target.value)"
      >
        <option value="">Todas las marcas</option>
        <option v-for="b in brands" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
      <button
        type="button" class="ctoolbar-toggle" :class="{ on: onlyOffers }"
        :aria-pressed="onlyOffers" @click="emit('update:onlyOffers', !onlyOffers)"
      >
        <AppIcon name="percent" :size="14" aria-hidden="true" /> Solo en oferta
      </button>
    </div>
  </div>
</template>

<style scoped>
.ctoolbar {
  position: sticky; top: 0; z-index: 4;
  display: grid; gap: 8px;
  margin: -6px -6px 12px; padding: 10px 6px 8px;
  background: var(--card); border-bottom: 1px solid var(--line);
}
.ctoolbar-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ctoolbar-frow { padding-top: 2px; }
.ctoolbar-search {
  flex: 1 1 200px; display: flex; align-items: center; gap: 8px; height: 40px;
  padding: 0 12px; border: 1px solid var(--line); border-radius: var(--radius-sm);
  background: var(--card); color: var(--muted); box-shadow: var(--shadow-sm);
}
.ctoolbar-search:focus-within { border-color: var(--brand-500); box-shadow: var(--ring); }
.ctoolbar-search input { flex: 1; min-width: 0; border: none; background: transparent; padding: 0; font: inherit; font-size: 14px; color: var(--ink); }
.ctoolbar-search input:focus { outline: none; }
.ctoolbar-search input::-webkit-search-cancel-button { -webkit-appearance: none; }
.ctoolbar-count { font-size: 12px; color: var(--muted); white-space: nowrap; font-variant-numeric: var(--num); margin-left: auto; }
.ctoolbar-sort { flex: 0 1 170px; min-height: 40px; padding: 8px 12px; font-size: 13.5px; }
.ctoolbar-sel { flex: 1 1 140px; min-height: 40px; padding: 8px 12px; font-size: 13.5px; }
.ctoolbar-toggle {
  position: relative; display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 8px 14px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--card);
  font: inherit; font-size: 13px; font-weight: 600; color: var(--ink-2); cursor: pointer;
}
.ctoolbar-toggle.on { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.ctoolbar-fbadge {
  display: inline-grid; place-items: center; min-width: 18px; height: 18px; padding: 0 5px;
  border-radius: 999px; background: var(--brand-600); color: #fff;
  font-size: 11px; font-weight: 700;
}
.ctoolbar-views { display: inline-flex; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.ctoolbar-view {
  display: grid; place-items: center; width: 40px; height: 40px; border: none;
  background: var(--card); color: var(--muted); cursor: pointer;
}
.ctoolbar-view + .ctoolbar-view { border-left: 1px solid var(--line); }
.ctoolbar-view.on { background: var(--brand-soft); color: var(--brand-ink); }
.ctoolbar-view:focus-visible, .ctoolbar-toggle:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
@media (max-width: 640px) {
  .ctoolbar-row { flex-wrap: wrap; }
  .ctoolbar-count { margin-left: 0; }
  .ctoolbar-filters { flex: 1 1 auto; justify-content: center; }
}
</style>
