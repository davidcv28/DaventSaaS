<script setup>
import { computed } from 'vue'

// Fila de valoración (web pública): el score sale del ratio likes/votos y el
// relleno parcial se resuelve con una fila dorada recortada al % sobre la fila
// base. Una sola estrella SVG vectorial para todas las plantillas (nítida a
// cualquier tamaño, sin placas ni fondos); `icon` se conserva por compatibilidad.
const props = defineProps({
  avg: { type: Number, default: null },
  count: { type: Number, default: 0 },
  size: { type: Number, default: 13 },
  showValue: { type: Boolean, default: false },
  icon: { type: String, default: 'star' },
})

const STAR = 'M12 2.5l2.95 6.05 6.65.95-4.8 4.7 1.15 6.6L12 17.65 6.05 20.8l1.15-6.6-4.8-4.7 6.65-.95z'
const pct = computed(() => {
  const avg = Number(props.avg)
  return Number.isFinite(avg) ? Math.max(0, Math.min(100, (avg / 5) * 100)) : 0
})
const label = computed(() => {
  const avg = Number(props.avg)
  if (!Number.isFinite(avg)) return 'Sin valoraciones'
  const base = `${avg.toFixed(1)} de 5`
  return props.count ? `${base} (${props.count} ${props.count === 1 ? 'valoración' : 'valoraciones'})` : base
})
</script>

<template>
  <span class="pstars" role="img" :aria-label="label" :title="label">
    <span class="pstars-row" aria-hidden="true">
      <span class="pstars-base">
        <svg v-for="i in 5" :key="i" class="pstars-ico" :width="size" :height="size" viewBox="0 0 24 24"><path :d="STAR" /></svg>
      </span>
      <span class="pstars-fill" :style="{ width: `${pct}%` }">
        <svg v-for="i in 5" :key="i" class="pstars-ico" :width="size" :height="size" viewBox="0 0 24 24"><path :d="STAR" /></svg>
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
  gap: 6px;
  line-height: 1;
}
.pstars-row { position: relative; display: inline-flex; flex: none; }
.pstars-base, .pstars-fill { display: inline-flex; gap: 1px; }
.pstars-base { color: currentColor; }
.pstars-base .pstars-ico { fill: currentColor; opacity: .2; }
.pstars-fill {
  position: absolute;
  inset: 0 auto 0 0;
  overflow: hidden;
  white-space: nowrap;
}
.pstars-fill .pstars-ico { fill: #f5a623; flex: none; }
.pstars-ico { display: block; flex: none; }
.pstars-num { font-size: .8em; font-weight: 700; }
.pstars-count { font-size: .72em; opacity: .65; }
</style>
