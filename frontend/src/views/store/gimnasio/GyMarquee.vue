<script setup>
// Cinta firma de GIMNASIO: pista duplicada al 50% para un loop sin costura.
// Solo transform (compositor); pausa al hover y se apaga con reduced-motion.
// `tone`: accent (lima sobre tinta) | ink (tinta sobre lima) | line (borde).
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  speed: { type: Number, default: 34 },
  tone: { type: String, default: 'accent' },
  icon: { type: String, default: '' }
})

const list = computed(() => props.items.map((i) => String(i || '').trim()).filter(Boolean))
// Cuatro copias: -50% equivale a dos pistas completas, así el loop nunca
// muestra un hueco aunque la lista sea corta.
const track = computed(() => [...list.value, ...list.value, ...list.value, ...list.value])
</script>

<template>
  <div
    v-if="list.length"
    class="gy-ribbon" :class="`is-${tone}`"
    :style="{ '--gy-ribbon-dur': `${speed}s` }"
    aria-hidden="true"
  >
    <div class="gy-ribbon-track">
      <span v-for="(item, i) in track" :key="i" class="gy-ribbon-item">
        <i class="gy-ribbon-mark"></i>{{ item }}
      </span>
    </div>
  </div>
</template>
