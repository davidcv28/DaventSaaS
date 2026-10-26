<script setup>
import { computed } from 'vue'

// Fila de valoración (web pública): el score sale del ratio likes/votos y el
// relleno parcial se resuelve con una fila clara recortada al % sobre la fila
// base. El glifo es un archivo .ico por plantilla (frontend/public/ratings/ —
// estrella en clásico, rayo en urbano, diamante en lookbook…), con placa y
// fondo propios de cada estilo; la fila base se apaga con filtro CSS.
const props = defineProps({
  avg: { type: Number, default: null },
  count: { type: Number, default: 0 },
  size: { type: Number, default: 13 },
  showValue: { type: Boolean, default: false },
  icon: { type: String, default: 'star' },
})

const src = computed(() => `/ratings/${props.icon}.ico`)
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
        <img v-for="i in 5" :key="i" class="pstars-ico" :src="src" :width="size" :height="size" alt="" loading="lazy" />
      </span>
      <span class="pstars-fill" :style="{ width: `${pct}%` }">
        <img v-for="i in 5" :key="i" class="pstars-ico" :src="src" :width="size" :height="size" alt="" loading="lazy" />
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
.pstars-base { display: inline-flex; gap: 2px; }
.pstars-base .pstars-ico { filter: grayscale(1) opacity(.28); }
.pstars-fill {
  position: absolute;
  inset: 0 auto 0 0;
  display: inline-flex;
  gap: 2px;
  overflow: hidden;
  white-space: nowrap;
}
.pstars-ico { display: block; }
.pstars-num { font-size: .8em; font-weight: 700; }
.pstars-count { font-size: .72em; opacity: .65; }
</style>
