<script setup>
import { computed } from 'vue'

// Estrellas de valoración (web pública + panel): media luna no existe —
// el relleno parcial se resuelve con una capa dorada recortada al % del
// promedio sobre la fila de estrellas vacías. Se usa en las tarjetas del
// catálogo (compact), la ficha (showValue) y la lista de moderación.
const props = defineProps({
  avg: { type: Number, default: null },
  count: { type: Number, default: 0 },
  size: { type: Number, default: 13 },
  showValue: { type: Boolean, default: false },
})

const pct = computed(() => {
  const avg = Number(props.avg)
  return Number.isFinite(avg) ? Math.max(0, Math.min(100, (avg / 5) * 100)) : 0
})
const label = computed(() => {
  const avg = Number(props.avg)
  if (!Number.isFinite(avg)) return 'Sin valoraciones'
  const base = `${avg.toFixed(1)} de 5 estrellas`
  return props.count ? `${base} (${props.count} ${props.count === 1 ? 'valoración' : 'valoraciones'})` : base
})
</script>

<template>
  <span class="pstars" role="img" :aria-label="label" :title="label">
    <span class="pstars-row" aria-hidden="true">
      <span class="pstars-base">
        <svg v-for="i in 5" :key="i" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/></svg>
      </span>
      <span class="pstars-fill" :style="{ width: `${pct}%` }">
        <svg v-for="i in 5" :key="i" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/></svg>
      </span>
    </span>
    <span v-if="showValue && avg != null" class="pstars-num">{{ Number(avg).toFixed(1) }}</span>
    <span v-if="count" class="pstars-count">({{ count }})</span>
  </span>
</template>

<style scoped>
.pstars {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  line-height: 1;
}
.pstars-row { position: relative; display: inline-flex; }
.pstars-base { display: inline-flex; gap: 1px; color: var(--line, #d8d8d8); }
.pstars-fill {
  position: absolute;
  inset: 0 auto 0 0;
  display: inline-flex;
  gap: 1px;
  color: #e8a020;
  overflow: hidden;
  white-space: nowrap;
}
.pstars-num { font-size: .8em; font-weight: 700; }
.pstars-count { font-size: .72em; opacity: .65; }
</style>
