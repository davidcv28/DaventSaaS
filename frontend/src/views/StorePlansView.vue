<script setup>
// Página "Suscripciones" de la web pública (site_templates 'plans'): un
// diseño puede declarar su propia vista en surfaces.plans; el resto cae a
// la vista genérica compartida (PlanesView), esquinada por los tokens de
// la piel activa. Consume el contexto `storePage` del layout público.
import { computed, inject } from 'vue'
import { surfaceComponent } from '../templates/index.js'
import PlanesView from './store/PlanesView.vue'

const ctx = inject('storePage')
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'plans') || PlanesView)
</script>

<template>
  <component :is="component" />
</template>
