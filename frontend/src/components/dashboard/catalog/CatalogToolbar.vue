<script setup>
import AppIcon from '../../AppIcon.vue'

// Barra del inventario en una sola fila: búsqueda + categoría + marca +
// solo-ofertas + orden + toggle de vista (tabla densa / grilla). El título
// "Inventario · n de m" y el botón "Actualizar precios" viven en la card,
// arriba de esta barra. Solo presentación: el estado vive en DashboardView.
defineProps({
  query: { type: String, default: '' },
  category: { type: [Number, String], default: '' },
  brand: { type: [Number, String], default: '' },
  onlyOffers: { type: Boolean, default: false },
  sort: { type: String, default: 'newest' },
  view: { type: String, default: 'table' },
  categories: { type: Array, default: () => [] },
  brands: { type: Array, default: () => [] }
})
const emit = defineEmits([
  'update:query', 'update:category', 'update:brand',
  'update:onlyOffers', 'update:sort', 'update:view'
])

const SORTS = [
  { value: 'newest', label: 'Más nuevos' },
  { value: 'name', label: 'Nombre (A-Z)' },
  { value: 'price', label: 'Menor precio' },
  { value: 'discount', label: 'Mayor descuento' }
]
</script>

<template>
  <div class="ctoolbar" role="search">
    <div class="ctoolbar-row">
      <label class="ctoolbar-search">
        <AppIcon name="search" :size="16" aria-hidden="true" />
        <input
          :value="query" type="search" placeholder="Buscar por nombre, categoría o marca"
          aria-label="Buscar productos" @input="emit('update:query', $event.target.value)"
        />
      </label>
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
      <select
        class="select ctoolbar-sel ctoolbar-sort" :value="sort" aria-label="Ordenar productos"
        @change="emit('update:sort', $event.target.value)"
      >
        <option v-for="s in SORTS" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <button
        type="button" class="ctoolbar-toggle" :class="{ on: onlyOffers }"
        :aria-pressed="onlyOffers" title="Ver solo productos en oferta"
        @click="emit('update:onlyOffers', !onlyOffers)"
      >
        <AppIcon name="percent" :size="14" aria-hidden="true" />
      </button>
      <span class="ctoolbar-views" role="group" aria-label="Cambiar vista">
        <button
          type="button" class="ctoolbar-view" :class="{ on: view === 'table' }"
          :aria-pressed="view === 'table'" title="Vista lista" @click="emit('update:view', 'table')"
        ><AppIcon name="list" :size="16" /></button>
        <button
          type="button" class="ctoolbar-view" :class="{ on: view === 'list' }"
          :aria-pressed="view === 'list'" title="Vista grilla" @click="emit('update:view', 'list')"
        ><AppIcon name="layout-grid" :size="16" /></button>
      </span>
    </div>
  </div>
</template>

<style scoped>
.ctoolbar { display: grid; gap: 8px; margin-bottom: 10px; }
.ctoolbar-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ctoolbar-search {
  flex: 1 1 200px; display: flex; align-items: center; gap: 8px; height: 38px;
  padding: 0 12px; border: 1px solid var(--line); border-radius: var(--radius-sm);
  background: var(--card); color: var(--muted);
}
.ctoolbar-search:focus-within { border-color: var(--brand-500); box-shadow: var(--ring); }
.ctoolbar-search input { flex: 1; min-width: 0; border: none; background: transparent; padding: 0; font: inherit; font-size: 13.5px; color: var(--ink); }
.ctoolbar-search input:focus { outline: none; }
.ctoolbar-search input::-webkit-search-cancel-button { -webkit-appearance: none; }
.ctoolbar-sel { flex: 0 1 170px; min-height: 38px; padding: 7px 12px; font-size: 13px; }
.ctoolbar-sort { flex: 0 1 150px; }
.ctoolbar-toggle {
  display: inline-grid; place-items: center; width: 38px; height: 38px;
  border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--card);
  color: var(--ink-2); cursor: pointer;
}
.ctoolbar-toggle.on { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.ctoolbar-views { display: inline-flex; border: 1px solid var(--line); border-radius: var(--radius-sm); overflow: hidden; margin-left: auto; }
.ctoolbar-view {
  display: grid; place-items: center; width: 38px; height: 38px; border: none;
  background: var(--card); color: var(--muted); cursor: pointer;
}
.ctoolbar-view + .ctoolbar-view { border-left: 1px solid var(--line); }
.ctoolbar-view.on { background: var(--brand-soft); color: var(--brand-ink); }
.ctoolbar-view:focus-visible, .ctoolbar-toggle:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
@media (max-width: 640px) {
  .ctoolbar-sel, .ctoolbar-sort { flex: 1 1 calc(50% - 4px); }
  .ctoolbar-views { margin-left: 0; }
}
</style>
