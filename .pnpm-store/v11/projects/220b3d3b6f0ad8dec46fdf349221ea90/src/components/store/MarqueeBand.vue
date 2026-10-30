<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'

// Franja continua bajo el hero: texto repetido (nombre de tienda,
// colección, ciudad). Solo transform; se pausa fuera de pantalla y con
// prefers-reduced-motion. items: strings u {icon, text}.
const props = defineProps({
  items: { type: Array, default: () => [] },
  speed: { type: Number, default: 26 }, // segundos por vuelta
  tall: { type: Boolean, default: false } // 56px en vez de 40
})
const norm = computed(() => props.items.map((it) => (typeof it === 'string' ? { text: it } : it)).filter((it) => it.text))
// Una sola secuencia puede ser corta: se repite hasta cubrir ~2 pantallas
// y la copia exacta para el loop -50%.
const seq = computed(() => {
  const base = norm.value.length ? norm.value : [{ text: '' }]
  const reps = Math.max(1, Math.ceil(10 / base.length))
  const half = Array.from({ length: reps }, () => base).flat()
  return [...half, ...half]
})
const root = ref(null)
const visible = ref(true)
let io = null
onMounted(() => {
  if ('IntersectionObserver' in window && root.value) {
    io = new IntersectionObserver(([e]) => { visible.value = e.isIntersecting }, { rootMargin: '80px' })
    io.observe(root.value)
  }
})
onBeforeUnmount(() => io?.disconnect())
</script>

<template>
  <div ref="root" class="mband" :class="{ tall, off: !visible }" :style="{ '--mband-speed': `${speed}s` }" aria-hidden="true">
    <div class="mband-track">
      <span v-for="(it, i) in seq" :key="i" class="mband-item">
        <AppIcon v-if="it.icon" :name="it.icon" :size="14" />
        {{ it.text }}<i class="mband-dot"></i>
      </span>
    </div>
  </div>
</template>

<style scoped>
.mband { overflow: hidden; height: 44px; display: flex; align-items: center; border-block: 1px solid color-mix(in srgb, currentColor 18%, transparent); }
.mband.tall { height: 56px; }
.mband-track { display: flex; align-items: center; flex: none; white-space: nowrap; animation: mband-run var(--mband-speed, 26s) linear infinite; will-change: transform; }
.mband.off .mband-track { animation-play-state: paused; }
.mband-item { display: inline-flex; align-items: center; gap: 12px; padding-inline: 14px; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; }
.mband-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--store-accent, currentColor); flex: none; }
@keyframes mband-run { to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) {
  .mband-track { animation: none; transform: none; }
  .mband { overflow-x: auto; }
}
</style>
