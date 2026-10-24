<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  value: { type: [Number, String], default: 0 },
  duration: { type: Number, default: 800 }
})

const shown = ref(typeof props.value === 'number' ? 0 : props.value)
let raf = 0

const reduce = () => window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

function run(to) {
  cancelAnimationFrame(raf)
  if (typeof to !== 'number' || reduce()) { shown.value = to; return }
  const from = typeof shown.value === 'number' ? shown.value : 0
  if (from === to) { shown.value = to; return }
  const t0 = performance.now()
  const tick = (now) => {
    const p = Math.min(1, (now - t0) / props.duration)
    const eased = 1 - Math.pow(1 - p, 3)
    shown.value = Math.round(from + (to - from) * eased)
    if (p < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}

onMounted(() => run(props.value))
watch(() => props.value, run)
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <span class="count-up">{{ typeof shown === 'number' ? shown.toLocaleString('es-AR') : shown }}</span>
</template>
