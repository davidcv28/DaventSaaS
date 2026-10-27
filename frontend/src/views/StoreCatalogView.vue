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
const { on } = useLayout('catalog')
const catalogNote = computed(() => (ctx?.custom?.value?.catalog_note || '').trim())
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'catalog'))
</script>

<template>
  <div class="cv-outer">
    <p v-if="catalogNote && on('note')" class="cv-note" role="note"><AppIcon name="megaphone" :size="15" />{{ catalogNote }}</p>
    <component :is="component" />
  </div>
</template>
