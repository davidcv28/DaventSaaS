<script setup>
// Portada de la web pública: el diseño configurado (pageTemplate) elige la
// composición declarada en su Template Definition (templates/<id>/index.js)
// — cada familia monta su propia vista y las servidas por StorePublicView
// resuelven sus variantes internas. Todas consumen el contexto `storePage`
// que provee StorePublicLayout, así que el wrapper no reimplementa
// resolución de tienda.
import { computed, inject } from 'vue'
import { surfaceComponent } from '../templates/index.js'

const ctx = inject('storePage')
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'landing'))
</script>

<template>
  <component :is="component" />
</template>
