<script setup>
import AppIcon from '../../components/AppIcon.vue'

// Estados vacíos compartidos por los catálogos de cada diseño: carga
// (esqueletos), error con reintento y "sin resultados". Sin estilo propio más
// allá de lo estructural — cada diseño lo viste desde su contenedor.
defineProps({
  status: { type: String, required: true },
  empty: { type: Boolean, default: false },
  hasFilters: { type: Boolean, default: false },
  skeletons: { type: Number, default: 8 }
})
defineEmits(['retry', 'clear'])
</script>

<template>
  <div v-if="status === 'loading' && empty" class="cv-skels" aria-busy="true" aria-label="Cargando productos">
    <span v-for="n in skeletons" :key="n" class="cv-skel" aria-hidden="true"></span>
  </div>
  <div v-else-if="status === 'error'" class="cv-state" role="alert">
    <span class="cv-state-icon"><AppIcon name="circle-alert" :size="26" /></span>
    <strong>No pudimos cargar el catálogo</strong>
    <p>Revisá tu conexión e intentá de nuevo.</p>
    <button type="button" class="cv-state-btn" @click="$emit('retry')"><AppIcon name="refresh" :size="15" /> Reintentar</button>
  </div>
  <div v-else-if="empty && status === 'success'" class="cv-state">
    <span class="cv-state-icon"><AppIcon name="package" :size="26" /></span>
    <strong>{{ hasFilters ? 'No hay productos con esos filtros' : 'Todavía no hay productos publicados' }}</strong>
    <p>{{ hasFilters ? 'Probá con otra búsqueda o quitá los filtros.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
    <button v-if="hasFilters" type="button" class="cv-state-btn" @click="$emit('clear')">Ver todo</button>
  </div>
</template>
