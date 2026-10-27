<script setup>
// Ficha de producto de la web pública (/<slug>/producto/<id>): el diseño
// configurado (pageTemplate) elige la composición. Las plantillas clásicas
// comparten la ficha marketplace de product/ProductClassic.vue y cada
// familia por categoría trae la suya (talle/spec/pedido/presupuesto) sobre
// el mismo contexto `storePage` que provee StorePublicLayout.
import { computed, inject, defineAsyncComponent } from 'vue'
import ProductClassic from './product/ProductClassic.vue'

const ctx = inject('storePage')
const VARIANTS = {
  atelier: defineAsyncComponent(() => import('./product/ProductAtelier.vue')),
  street: defineAsyncComponent(() => import('./product/ProductAtelier.vue')),
  circuit: defineAsyncComponent(() => import('./product/ProductCircuit.vue')),
  lab: defineAsyncComponent(() => import('./product/ProductCircuit.vue')),
  mercado: defineAsyncComponent(() => import('./product/ProductMercado.vue')),
  carta: defineAsyncComponent(() => import('./product/ProductMercado.vue')),
  studio: defineAsyncComponent(() => import('./product/ProductStudio.vue')),
  proceso: defineAsyncComponent(() => import('./product/ProductStudio.vue')),
  promo: defineAsyncComponent(() => import('./product/ProductOfertas.vue')),
  shop: defineAsyncComponent(() => import('./product/ProductOfertas.vue')),
  arena: defineAsyncComponent(() => import('./product/ProductGamer.vue')),
  terminal: defineAsyncComponent(() => import('./product/ProductGamer.vue')),
  calma: defineAsyncComponent(() => import('./product/ProductBelleza.vue')),
  signature: defineAsyncComponent(() => import('./product/ProductBelleza.vue'))
}
const component = computed(() => VARIANTS[ctx?.pageTemplate?.value] || ProductClassic)
</script>

<template>
  <component :is="component" />
</template>
