<script setup>
// Portada de la web pública: el diseño configurado (pageTemplate) elige la
// composición — 'duo' renderiza la landing a dos columnas de
// StorePublicAltView, cada familia por categoría (atelier/street,
// circuit/lab, mercado/carta, studio/proceso) monta su propia vista y el
// resto cae en la portada estándar (StorePublicView), que resuelve sus
// propias variantes internas por template. Todas consumen el contexto
// `storePage` que provee StorePublicLayout, así que el wrapper no
// reimplementa resolución de tienda.
import { computed, inject, defineAsyncComponent } from 'vue'
import StorePublicView from './StorePublicView.vue'
import StorePublicAltView from './StorePublicAltView.vue'
import StoreBloqueView from './StoreBloqueView.vue'
import StoreRisoView from './StoreRisoView.vue'
import StoreTerraView from './StoreTerraView.vue'

const ctx = inject('storePage')
const FAMILY_VIEWS = {
  atelier: defineAsyncComponent(() => import('./StoreAtelierView.vue')),
  street: defineAsyncComponent(() => import('./StoreAtelierView.vue')),
  circuit: defineAsyncComponent(() => import('./StoreCircuitView.vue')),
  lab: defineAsyncComponent(() => import('./StoreCircuitView.vue')),
  mercado: defineAsyncComponent(() => import('./StoreMercadoView.vue')),
  carta: defineAsyncComponent(() => import('./StoreMercadoView.vue')),
  studio: defineAsyncComponent(() => import('./StoreStudioView.vue')),
  proceso: defineAsyncComponent(() => import('./StoreStudioView.vue')),
  promo: defineAsyncComponent(() => import('./StoreOfertasView.vue')),
  shop: defineAsyncComponent(() => import('./StoreOfertasView.vue'))
}
const component = computed(() => {
  const tpl = ctx?.pageTemplate?.value
  if (tpl === 'duo') return StorePublicAltView
  if (tpl === 'bloque') return StoreBloqueView
  if (tpl === 'riso') return StoreRisoView
  if (tpl === 'terra') return StoreTerraView
  return FAMILY_VIEWS[tpl] || StorePublicView
})
</script>

<template>
  <component :is="component" />
</template>
