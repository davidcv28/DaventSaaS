<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

// Tarjeta "Calidad de tu web" del resumen (dashboard): score 0-100, barra
// de avance y los 3 checks fallidos de mayor peso con botón a la pestaña
// que lo resuelve. Se oculta cuando score = 100 o no hay reporte.
// Solo usa las clases/tokens del panel (ovh-*, --brand-*, --muted...).
const props = defineProps({
  report: { type: Object, default: null },   // {score, checks:[...]}
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate'])

const visible = computed(() => Boolean(props.report) && (props.report.score ?? 100) < 100)
const score = computed(() => props.report?.score ?? 0)
const missing = computed(() => props.report?.score != null ? 100 - props.report.score : 0)
const failed = computed(() =>
  (props.report?.checks || []).filter((c) => !c?.ok).sort((a, b) => (b.weight || 0) - (a.weight || 0)).slice(0, 3)
)

function go(tab) {
  emit('navigate', tab)
}
</script>

<template>
  <section v-if="visible" class="ovh ovh-card wqc" aria-label="Calidad de tu web">
    <div class="wqc-score">
      <span class="wqc-num">{{ score }}<small>/100</small></span>
      <div class="wqc-meta">
        <div class="ovh-prog wqc-prog" role="progressbar" aria-label="Calidad de tu web" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="score">
          <span :style="{ transform: `scaleX(${score / 100})` }"></span>
        </div>
        <small class="wqc-hint">Te faltan <strong>{{ missing }}</strong> {{ missing === 1 ? 'punto' : 'puntos' }} para una web profesional</small>
      </div>
    </div>
    <ul class="wqc-list">
      <li v-for="c in failed" :key="c.id">
        <div class="wqc-body">
          <strong>{{ c.label }}</strong>
          <small>{{ c.weight }} {{ c.weight === 1 ? 'punto' : 'puntos' }}</small>
        </div>
        <button type="button" class="ovh-link" @click="go(c.tab)">{{ c.action }} <AppIcon name="arrow-right" :size="13" /></button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.ovh.wqc { flex-direction: row; align-items: center; gap: 22px; margin-bottom: 14px; }
.wqc-score { flex: none; display: flex; align-items: center; gap: 14px; min-width: 0; }
.wqc-num { font-size: 30px; font-weight: 800; letter-spacing: -.04em; line-height: 1; font-variant-numeric: tabular-nums; color: var(--ink); }
.wqc-num small { font-size: 13px; font-weight: 650; color: var(--muted); letter-spacing: 0; }
.wqc-meta { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.wqc-prog { width: 150px; margin: 0; }
.wqc-hint { font-size: 11.5px; color: var(--muted); }
.wqc-list { flex: 1; min-width: 0; list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.wqc-list li { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-top: 1px solid var(--line-soft); }
.wqc-list li:first-child { border-top: none; padding-top: 0; }
.wqc-body { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.wqc-body strong { font-size: 13px; font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wqc-body small { font-size: 11.5px; color: var(--muted); }
@media (max-width: 900px) {
  .ovh.wqc { flex-direction: column; align-items: stretch; gap: 12px; }
  .wqc-prog { width: 100%; }
}
</style>
