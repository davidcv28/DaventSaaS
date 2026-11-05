<script setup>
import AppIcon from '../../AppIcon.vue'

// Barra de herramientas del listado de productos: búsqueda, filtros por
// categoría/marca, "solo en oferta", orden y vista grilla/lista.
// Solo presentación: el estado vive en DashboardView (v-model por prop).
const props = defineProps({
  query: { type: String, default: '' },
  category: { type: [Number, String], default: '' },
  brand: { type: [Number, String], default: '' },
  onlyOffers: { type: Boolean, default: false },
  sort: { type: String, default: 'newest' },
  view: { type: String, default: 'table' },
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
      <div class="ctoolbar-count" aria-live="polite">{{ shown }} de {{ total }}</div>
    </div>
    <div class="ctoolbar-row">
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
        class="select ctoolbar-sel" :value="sort" aria-label="Ordenar productos"
        @change="emit('update:sort', $event.target.value)"
      >
        <option v-for="s in SORTS" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
    </div>
    <div class="ctoolbar-row ctoolbar-row-end">
      <button
        type="button" class="ctoolbar-toggle" :class="{ on: onlyOffers }"
        :aria-pressed="onlyOffers" @click="emit('update:onlyOffers', !onlyOffers)"
      >
        <AppIcon name="percent" :size="14" aria-hidden="true" /> Solo en oferta
      </button>
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
      <button type="button" class="ctoolbar-new" @click="emit('new')">
        <AppIcon name="plus" :size="15" /> Cargar producto
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
.ctoolbar-row-end { justify-content: space-between; }
.ctoolbar-search {
  flex: 1 1 220px; display: flex; align-items: center; gap: 8px; height: 40px;
  padding: 0 12px; border: 1px solid var(--line); border-radius: var(--radius-sm);
  background: var(--card); color: var(--muted); box-shadow: var(--shadow-sm);
}
.ctoolbar-search:focus-within { border-color: var(--brand-500); box-shadow: var(--ring); }
.ctoolbar-search input { flex: 1; min-width: 0; border: none; background: transparent; padding: 0; font: inherit; font-size: 14px; color: var(--ink); }
.ctoolbar-search input:focus { outline: none; }
.ctoolbar-search input::-webkit-search-cancel-button { -webkit-appearance: none; }
.ctoolbar-count { font-size: 12px; color: var(--muted); white-space: nowrap; font-variant-numeric: var(--num); }
.ctoolbar-sel { flex: 1 1 140px; min-height: 40px; padding: 8px 12px; font-size: 13.5px; }
.ctoolbar-toggle {
  display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 8px 14px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--card);
  font: inherit; font-size: 13px; font-weight: 600; color: var(--ink-2); cursor: pointer;
}
.ctoolbar-toggle.on { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.ctoolbar-views { display: inline-flex; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.ctoolbar-view {
  display: grid; place-items: center; width: 40px; height: 40px; border: none;
  background: var(--card); color: var(--muted); cursor: pointer;
}
.ctoolbar-view + .ctoolbar-view { border-left: 1px solid var(--line); }
.ctoolbar-view.on { background: var(--brand-soft); color: var(--brand-ink); }
.ctoolbar-view:focus-visible, .ctoolbar-toggle:focus-visible, .ctoolbar-new:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.ctoolbar-new {
  display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 8px 16px;
  border: none; border-radius: 10px;
  background: linear-gradient(135deg, var(--brand-500), #8b5cf6 65%, #d946ef);
  color: #fff; font: inherit; font-size: 13.5px; font-weight: 600; cursor: pointer;
  box-shadow: 0 6px 14px rgba(99, 102, 241, .3);
  transition: transform .12s, box-shadow .15s, filter .15s;
}
.ctoolbar-new:hover { transform: translateY(-1px); filter: brightness(1.05); box-shadow: 0 9px 18px rgba(99, 102, 241, .42); }
@media (max-width: 640px) {
  .ctoolbar-row-end { flex-wrap: wrap; }
  .ctoolbar-new { flex: 1 1 100%; justify-content: center; }
}
</style>
