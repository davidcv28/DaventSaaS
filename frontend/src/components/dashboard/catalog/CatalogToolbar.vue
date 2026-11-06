<script setup>
import { ref, computed } from 'vue'
import AppIcon from '../../AppIcon.vue'

// Barra del inventario en una sola fila: búsqueda + categoría + marca +
// solo-ofertas + orden. El título "Inventario · n de m" y el botón
// "Actualizar precios" viven en la card, arriba de esta barra.
// Solo presentación: el estado vive en DashboardView.
const props = defineProps({
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
  'update:onlyOffers', 'update:sort', 'prices'
])

const SORTS = [
  { value: 'newest', label: 'Más nuevos' },
  { value: 'name', label: 'Nombre (A-Z)' },
  { value: 'price', label: 'Menor precio' },
  { value: 'discount', label: 'Mayor descuento' }
]

// Móvil: los filtros colapsan en un ícono que abre una hoja.
const filtersOpen = ref(false)
const activeFilters = computed(() => Number(!!props.category) + Number(!!props.brand) + Number(props.onlyOffers))
function clearFilters() {
  emit('update:category', '')
  emit('update:brand', '')
  emit('update:onlyOffers', false)
}
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
      <button
        type="button" class="ctoolbar-filterbtn" :aria-expanded="filtersOpen"
        title="Filtros" @click="filtersOpen = true"
      >
        <AppIcon name="arrow-down-wide-narrow" :size="15" aria-hidden="true" />
        <span v-if="activeFilters" class="ctoolbar-count">{{ activeFilters }}</span>
      </button>
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
      <button type="button" class="ctoolbar-prices" @click="emit('prices')">
        <AppIcon name="tag" :size="14" aria-hidden="true" /> Actualizar precios
      </button>
    </div>
    <Teleport to="body">
      <div v-if="filtersOpen" class="cfilters-overlay" @click.self="filtersOpen = false">
        <div class="cfilters-sheet" role="dialog" aria-modal="true" aria-label="Filtros">
          <div class="cfilters-head">
            <strong>Filtros</strong>
            <button type="button" class="cfilters-x" aria-label="Cerrar" @click="filtersOpen = false"><AppIcon name="x" :size="16" /></button>
          </div>
          <label class="cfilters-field">
            <span>Categoría</span>
            <select class="select" :value="category" @change="emit('update:category', $event.target.value)">
              <option value="">Todas las categorías</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </label>
          <label class="cfilters-field">
            <span>Marca</span>
            <select class="select" :value="brand" @change="emit('update:brand', $event.target.value)">
              <option value="">Todas las marcas</option>
              <option v-for="b in brands" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
          </label>
          <label class="cfilters-field">
            <span>Ordenar</span>
            <select class="select" :value="sort" @change="emit('update:sort', $event.target.value)">
              <option v-for="s in SORTS" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </label>
          <label class="cfilters-offers">
            <input type="checkbox" :checked="onlyOffers" @change="emit('update:onlyOffers', $event.target.checked)" />
            <span>Solo productos en oferta</span>
          </label>
          <div class="cfilters-actions">
            <button type="button" class="cfilters-clear" :disabled="!activeFilters" @click="clearFilters">Limpiar</button>
            <button type="button" class="btn btn-auto" @click="filtersOpen = false">Ver resultados</button>
          </div>
        </div>
      </div>
    </Teleport>
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
.ctoolbar-prices {
  display: inline-flex; align-items: center; gap: 7px; flex: none; height: 38px;
  padding: 0 14px; border: 1px solid var(--line); border-radius: var(--radius-sm);
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 13px;
  font-weight: 600; cursor: pointer; white-space: nowrap;
  transition: color .15s, border-color .15s, background .15s;
}
.ctoolbar-prices:hover { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
/* Botón de filtros: solo en móvil, con contador de filtros activos. */
.ctoolbar-filterbtn { display: none; position: relative; }
.ctoolbar-count {
  position: absolute; top: -5px; right: -5px; display: grid; place-items: center;
  min-width: 16px; height: 16px; padding: 0 4px; border-radius: 999px;
  background: var(--brand-600); color: #fff; font-size: 10px; font-weight: 700;
}
@media (max-width: 720px) {
  .ctoolbar-sel, .ctoolbar-sort, .ctoolbar-toggle { display: none; }
  .ctoolbar-filterbtn {
    display: inline-grid; place-items: center; flex: none; width: 38px; height: 38px;
    border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface);
    color: var(--ink-2); cursor: pointer;
  }
  .ctoolbar-filterbtn:hover { border-color: var(--brand-500); color: var(--brand-ink); }
  .ctoolbar-search { flex: 1 1 auto; }
  .ctoolbar-prices { flex: 1 1 auto; justify-content: center; }
}
/* Hoja de filtros (móvil). */
.cfilters-overlay {
  position: fixed; inset: 0; z-index: 60; display: flex; align-items: flex-end;
  background: rgba(10, 8, 30, .45);
}
.cfilters-sheet {
  width: 100%; max-height: 82vh; overflow-y: auto; padding: 16px 16px 20px;
  border-radius: 16px 16px 0 0; background: var(--card);
  box-shadow: 0 -12px 40px rgba(10, 8, 30, .3);
}
.cfilters-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.cfilters-head strong { font-size: 15.5px; color: var(--ink); }
.cfilters-x {
  display: grid; place-items: center; width: 30px; height: 30px; border: none;
  border-radius: 50%; background: var(--surface); color: var(--muted); cursor: pointer;
}
.cfilters-field { display: grid; gap: 6px; margin-bottom: 12px; }
.cfilters-field span { font-size: 12.5px; font-weight: 600; color: var(--muted); }
.cfilters-offers {
  display: flex; align-items: center; gap: 9px; margin: 4px 0 16px; padding: 10px 12px;
  border: 1px solid var(--line-soft); border-radius: var(--radius-sm);
  font-size: 13.5px; font-weight: 550; color: var(--ink-2); cursor: pointer;
}
.cfilters-offers input { width: 16px; height: 16px; accent-color: var(--brand-600); }
.cfilters-actions { display: flex; gap: 10px; }
.cfilters-actions .btn { flex: 1; }
.cfilters-clear {
  flex: none; padding: 0 14px; border: none; background: transparent; cursor: pointer;
  font: inherit; font-size: 13px; font-weight: 600; color: var(--muted);
}
.cfilters-clear:disabled { opacity: .45; cursor: default; }
</style>
