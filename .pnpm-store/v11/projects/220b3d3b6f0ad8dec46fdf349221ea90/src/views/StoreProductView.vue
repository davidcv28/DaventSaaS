<script setup>
// Ficha de producto de la web pública (/<slug>/producto/<id>): el diseño
// configurado (pageTemplate) elige la composición declarada en su Template
// Definition (templates/<id>/index.js) sobre el mismo contexto `storePage`
// que provee StorePublicLayout.
import { computed, inject } from 'vue'
import { surfaceComponent } from '../templates/index.js'

const ctx = inject('storePage')
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'product'))
</script>

<template>
  <component :is="component" />
</template>
