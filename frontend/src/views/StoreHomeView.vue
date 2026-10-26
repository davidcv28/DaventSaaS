<script setup>
// Portada de la web pública: el diseño configurado (pageTemplate) elige la
// composición — 'duo' renderiza la landing a dos columnas de
// StorePublicAltView y el resto cae en la portada estándar
// (StorePublicView), que resuelve sus propias variantes internas por
// template. Ambas consumen el contexto `storePage` que provee
// StorePublicLayout, así que el wrapper no reimplementa resolución de tienda.
import { computed, inject } from 'vue'
import StorePublicView from './StorePublicView.vue'
import StorePublicAltView from './StorePublicAltView.vue'
import StoreBloqueView from './StoreBloqueView.vue'
import StoreRisoView from './StoreRisoView.vue'

const ctx = inject('storePage')
const component = computed(() => {
  const tpl = ctx?.pageTemplate?.value
  if (tpl === 'duo') return StorePublicAltView
  if (tpl === 'bloque') return StoreBloqueView
  if (tpl === 'riso') return StoreRisoView
  return StorePublicView
})
</script>

<template>
  <component :is="component" />
</template>
