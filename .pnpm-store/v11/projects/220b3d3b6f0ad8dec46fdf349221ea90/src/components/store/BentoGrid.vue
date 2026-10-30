<script setup>
import { computed } from 'vue'

// Grilla bento 4 col desktop / 2 mobile, gap 12px. Orden determinista por
// prioridad: el primer ítem con offer ocupa 2x2, el primer destacado/nuevo
// 2x1, el resto 1x1. Cada celda mantiene aspect-ratio fijo. El contenido
// real lo dibuja el slot (card de producto de la familia).
const props = defineProps({
  items: { type: Array, default: () => [] },
  isOffer: { type: Function, default: () => false },
  isFeatured: { type: Function, default: () => false }
})
const cells = computed(() => {
  let bigUsed = false
  let wideUsed = false
  return props.items.map((item, i) => {
    let span = 'b1'
    if (!bigUsed && props.isOffer(item)) { span = 'b22'; bigUsed = true }
    else if (!wideUsed && props.isFeatured(item)) { span = 'b21'; wideUsed = true }
    return { item, span, i }
  })
})
</script>

<template>
  <div class="bento">
    <div v-for="c in cells" :key="c.item.id ?? c.i" class="bento-cell" :class="c.span">
      <slot :item="c.item" :span="c.span" />
    </div>
  </div>
</template>

<style scoped>
.bento { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.bento-cell { min-width: 0; aspect-ratio: 1; position: relative; }
.bento-cell.b22 { grid-column: span 2; grid-row: span 2; }
.bento-cell.b21 { grid-column: span 2; aspect-ratio: 2 / 1; }
@media (min-width: 768px) {
  .bento { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .bento-cell.b21 { aspect-ratio: 2 / 1; }
  .bento-cell.b22 { aspect-ratio: auto; }
}
</style>
