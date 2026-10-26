<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import '../../assets/store-facets.css'

// Chips de filtros activos compartidos por las plantillas que no tienen
// una fila de tags propia (Clásico, Tienda Pro, Riso y Bloque ya muestran
// las suyas). Muestra una etiqueta removible por filtro aplicado + el
// reset total — cada diseño las viste desde store-facets.css con el mismo
// idioma de sus controles (.cf-tag / .cf-tag.clear / .cf-tag-x).
const { hasFilters, activeTags, clearFilters } = useStoreCatalog()
</script>

<template>
<div v-if="hasFilters" class="cf-tags" role="group" aria-label="Filtros activos">
  <button
    v-for="t in activeTags" :key="t.key" type="button" class="cf-tag"
    :aria-label="`Quitar filtro ${t.label}`" @click="t.remove()"
  >
    <span>{{ t.label }}</span><i class="cf-tag-x" aria-hidden="true">×</i>
  </button>
  <button type="button" class="cf-tag clear" @click="clearFilters">Limpiar todo</button>
</div>
</template>
