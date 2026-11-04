<script setup>
// Cinta firma de MOVIMIENTO: marquesina tipográfica editorial — palabras
// grandes condensadas separadas por una marca de acento, pista duplicada
// al 50% para un loop sin costura. Solo transform (compositor); pausa al
// hover y se apaga con prefers-reduced-motion.
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  speed: { type: Number, default: 40 },
  tone: { type: String, default: 'line' } // line (borde) | ink (tinta) | accent
})

const list = computed(() => props.items.map((i) => String(i || '').trim()).filter(Boolean))
// Cuatro copias: -50% equivale a dos pistas completas, así el loop nunca
// muestra un hueco aunque la lista sea corta.
const track = computed(() => [...list.value, ...list.value, ...list.value, ...list.value])
</script>

<template>
  <div
    v-if="list.length"
    class="mv-ribbon" :class="`is-${tone}`"
    :style="{ '--mv-ribbon-dur': `${speed}s` }"
    aria-hidden="true"
  >
    <div class="mv-ribbon-track">
      <span v-for="(item, i) in track" :key="i" class="mv-ribbon-item">
        {{ item }}<i class="mv-ribbon-mark"></i>
      </span>
    </div>
  </div>
</template>
