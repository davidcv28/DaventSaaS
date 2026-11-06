<script setup>
import AppIcon from '../../AppIcon.vue'

// Barra del inventario en una sola fila: búsqueda + categoría + marca +
// solo-ofertas + orden. El título "Inventario · n de m" y el botón
// "Actualizar precios" viven en la card, arriba de esta barra.
// Solo presentación: el estado vive en DashboardView.
defineProps({
  query: { type: String, default: '' },
  category: { type: [Number, String], default: '' },
  brand: { type: [Number, String], default: '' },
  onlyOffers: { type: Boolean, default: false },
  sort: { type: String, default: 'newest' },
  categories: { type: Array, default: () => [] },
  brands: { type: Array, default: () => [] }
})
const emit = defineEmits([
  'update:query', 'update:category', 'update:brand',
  'update:onlyOffers', 'update:sort'
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
    </div>
  </div>
</template>

<style scoped>
.ctoolbar { display: grid; gap: 8px; margin-bottom: 6px; }
.ctoolbar-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ctoolbar-search {
  flex: 1 1 220px; min-width: 0; display: flex; align-items: center; gap: 8px; height: 38px;
  padding: 0 12px; border: 1px solid var(--line); border-radius: var(--radius-sm);
  background: var(--surface); color: var(--muted); transition: border-color .15s, background .15s;
}
.ctoolbar-search:hover { border-color: var(--line-strong, var(--line)); }
.ctoolbar-search:focus-within { border-color: var(--brand-500); background: var(--card); box-shadow: var(--ring); }
.ctoolbar-search svg { flex: none; }
.ctoolbar-search input { flex: 1; min-width: 0; border: none; background: transparent; padding: 0; font: inherit; font-size: 13.5px; color: var(--ink); }
.ctoolbar-search input:focus { outline: none; }
.ctoolbar-search input::placeholder { color: var(--muted); }
.ctoolbar-search input::-webkit-search-cancel-button { -webkit-appearance: none; }
.ctoolbar-sel {
  flex: 0 1 170px; min-width: 120px; min-height: 38px; padding: 7px 30px 7px 12px;
  font-size: 13px; color: var(--ink-2); border-color: var(--line); background-color: var(--surface);
}
.ctoolbar-sel:hover { border-color: var(--line-strong, var(--line)); }
.ctoolbar-sort { flex: 0 1 145px; min-width: 110px; }
.ctoolbar-toggle {
  display: inline-grid; place-items: center; flex: none; width: 38px; height: 38px;
  border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface);
  color: var(--muted); cursor: pointer; transition: color .15s, border-color .15s, background .15s;
}
.ctoolbar-toggle:hover { color: var(--ink-2); }
.ctoolbar-toggle.on { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.ctoolbar-toggle:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
@media (max-width: 720px) {
  .ctoolbar-search { flex: 1 1 100%; }
  .ctoolbar-sel, .ctoolbar-sort { flex: 1 1 calc(50% - 4px); min-width: 0; }
}
</style>
