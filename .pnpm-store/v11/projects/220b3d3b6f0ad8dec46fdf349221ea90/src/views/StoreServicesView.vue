<script setup>
// Página "Servicios" de la web pública: el diseño activo (pageTemplate)
// resuelve su propia vista de servicios desde su Template Definition; todas
// consumen el contexto `storePage` y el payload público de la tienda.
import { computed, inject } from 'vue'
import { surfaceComponent } from '../templates/index.js'

const ctx = inject('storePage')
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'services'))
</script>

<template>
  <component :is="component" />
</template>
