<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

// Fila de valoración (web pública + panel): el score sale del ratio
// likes/votos y el relleno parcial se resuelve con una capa dorada recortada
// al % sobre la fila de íconos base. El glifo depende de la plantilla de la
// web (prop `icon`): estrella en clásico, rayo en urbano, diamante en
// lookbook… cualquier ícono del catálogo sirve.
const props = defineProps({
  avg: { type: Number, default: null },
  count: { type: Number, default: 0 },
  size: { type: Number, default: 13 },
  showValue: { type: Boolean, default: false },
  icon: { type: String, default: 'star' },
})

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
        <AppIcon v-for="i in 5" :key="i" :name="icon" :size="size" />
      </span>
      <span class="pstars-fill" :style="{ width: `${pct}%` }">
        <AppIcon v-for="i in 5" :key="i" :name="icon" :size="size" />
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
