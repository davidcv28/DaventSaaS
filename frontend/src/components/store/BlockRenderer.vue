<script setup>
// BlockRenderer: monta los bloques habilitados de una superficie pública
// en el orden del layout efectivo (default de la plantilla ∪
// layout_config). Cada id resuelve a un componente async del mapa
// `components` que recibe el Template Definition; los bloques apagados o
// sin componente no se montan, y los que quedan vacíos se auto-ocultan en
// su propio v-if (sin secciones vacías).
// Cada bloque recibe :block="{id, enabled, order, variant?, props?}" para
// aplicar su variante/props (p.ej. props.title = título alternativo).
import { computed, inject } from 'vue'
import { resolveLayout } from '../../templates/index.js'

const props = defineProps({
  surface: { type: String, required: true },
  components: { type: Object, required: true }
})

const ctx = inject('storePage')
const blocks = computed(() =>
  resolveLayout(
    ctx.pageTemplate.value,
    props.surface,
    ctx.custom.value?.layout_config
  ).filter((b) => b.enabled && props.components[b.id])
)
</script>

<template>
  <!-- data-blk marca cada bloque para el editor (scroll-sync); el wrapper
       con display:contents no toca el layout de la página. -->
  <div v-for="b in blocks" :key="b.id" :data-blk="b.id" style="display: contents">
    <component :is="components[b.id]" :block="b" />
  </div>
</template>
