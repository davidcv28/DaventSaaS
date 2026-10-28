<script setup>
// Página de catálogo de la web pública (/<slug>/catalogo). El diseño
// configurado (pageTemplate) elige la composición completa: 'classic' es el
// catálogo estándar y cada otro diseño trae su propia página (layout, filtros
// y tarjetas propios) sobre el mismo estado (composables/useStoreCatalog).
// Como StoreHomeView, solo consume el contexto `storePage` del layout.
import { computed, inject } from 'vue'
import { surfaceComponent } from '../templates/index.js'
import AppIcon from '../components/AppIcon.vue'
import { useLayout } from '../composables/useLayout.js'
import '../assets/store-catalog.css'
import '../assets/store-catalog-responsive.css'
import '../assets/store-catalog-polish.css'

const ctx = inject('storePage')
// Aviso configurable del dueño: tira informativa arriba del catálogo
// (envíos, medios de pago, retiro). Vacío -> no se muestra. Es un bloque
// del layout del catálogo ('note'): el editor puede apagarlo.
const { on, st } = useLayout('catalog')
const catalogNote = computed(() => (ctx?.custom?.value?.catalog_note || '').trim())
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'catalog'))
// Las variantes de composición de 'grid' y 'filters' viajan como
// data-attrs de la página: la hoja de catálogo las aplica sobre cualquier
// vista (la grilla se marca con :has(> .tpc)) sin tocar cada plantilla.
const gridVariant = computed(() => st('grid').variant || 'auto')
const filtersVariant = computed(() => st('filters').variant || 'panel')
</script>

<template>
  <div class="cv-outer" :data-cv-grid="gridVariant" :data-cv-filters="filtersVariant">
    <p v-if="catalogNote && on('note')" data-blk="note" class="cv-note" role="note"><AppIcon name="megaphone" :size="15" />{{ catalogNote }}</p>
    <component :is="component" />
  </div>
</template>
