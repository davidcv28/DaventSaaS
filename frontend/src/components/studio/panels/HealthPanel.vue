<script setup>
// "Salud de tu web" — corre health.analyzeStudioHealth sobre el borrador
// (tema + layout de ensayo) y el contenido publicado. Cada hallazgo lleva
// un fix opcional que aplica el shell (tema/bloque) o navega a la sección
// dueña del contenido (Mis datos, Mi negocio, productos...).
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { analyzeStudioHealth, healthScore } from '../health.js'

const props = defineProps({
  theme: { type: Object, required: true },
  form: { type: Object, required: true },
  layout: { type: Object, default: null },
  ctx: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['navigate', 'fix'])

const issues = computed(() => analyzeStudioHealth({
  theme: props.theme,
  form: props.form,
  layout: props.layout,
  ...props.ctx
}))
const score = computed(() => healthScore(issues.value))
const warns = computed(() => issues.value.filter((i) => i.sev === 'warn').length)
const scoreLabel = computed(() => {
  if (score.value >= 90) return 'Tu web se ve muy bien'
  if (score.value >= 70) return 'Va bien, con detalles por pulir'
  return 'Hay cosas que conviene corregir'
})

function run(issue) {
  if (!issue.fix) return
  if (issue.fix.kind === 'nav') emit('navigate', issue.fix.target)
  else emit('fix', issue.fix)
}
</script>

<template>
  <div class="stp stp-health">
    <!-- Puntaje general -->
    <div class="sth-score" :data-warn="warns > 0" role="status">
      <span class="sth-score-n" aria-hidden="true">
        <svg viewBox="0 0 44 44" class="sth-ring" aria-hidden="true">
          <circle cx="22" cy="22" r="19" class="sth-ring-bg" />
          <circle cx="22" cy="22" r="19" class="sth-ring-fg" :stroke-dasharray="`${score * 1.194} 119.4`" />
        </svg>
        <b>{{ score }}</b>
      </span>
      <div class="sth-score-t">
        <strong>{{ scoreLabel }}</strong>
        <p>{{ issues.length ? `${issues.length} hallazgo${issues.length > 1 ? 's' : ''}${warns ? ` (${warns} importante${warns > 1 ? 's' : ''})` : ''}` : 'Sin hallazgos: contraste, imágenes, textos y secciones en orden.' }}</p>
      </div>
    </div>

    <!-- Estado vacío positivo -->
    <div v-if="!issues.length" class="stp-card sth-ok">
      <span class="stp-card-ico"><AppIcon name="circle-check" :size="22" /></span>
      <strong>Todo en orden</strong>
      <p>Revisamos contraste accesible, peso de imágenes, longitud de textos, secciones vacías, contacto y tamaños táctiles.</p>
    </div>

    <!-- Hallazgos -->
    <ul v-else class="sth-list">
      <li v-for="i in issues" :key="i.id" class="sth-item" :data-sev="i.sev">
        <span class="sth-item-ico"><AppIcon :name="i.icon" :size="16" /></span>
        <div class="sth-item-t">
          <strong>{{ i.title }}</strong>
          <p>{{ i.detail }}</p>
          <button v-if="i.fix" type="button" class="btn secondary btn-auto sth-fix" @click="run(i)">
            <AppIcon :name="i.fix.kind === 'nav' ? 'arrow-right' : 'sparkles'" :size="13" /> {{ i.fix.label }}
          </button>
        </div>
      </li>
    </ul>
    <p v-if="issues.length" class="stp-hint">Los arreglos del tema se aplican al borrador (se publican con “Publicar”); los de contenido abren la sección correspondiente.</p>
  </div>
</template>

<style scoped>
.sth-score { display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); }
.sth-score-n { position: relative; width: 52px; height: 52px; flex: none; display: grid; place-items: center; }
.sth-ring { position: absolute; inset: 0; transform: rotate(-90deg); }
.sth-ring-bg, .sth-ring-fg { fill: none; stroke-width: 4; }
.sth-ring-bg { stroke: var(--line-soft); }
.sth-ring-fg { stroke: var(--ok, #16a34a); stroke-linecap: round; transition: stroke-dasharray .5s ease; }
.sth-score[data-warn='true'] .sth-ring-fg { stroke: var(--warn, #d97706); }
.sth-score-n b { font-size: 15px; }
.sth-score-t strong { font-size: 13.5px; }
.sth-score-t p { margin: 2px 0 0; font-size: 12px; color: var(--muted); line-height: 1.4; }
.sth-ok { margin-top: 12px; }
.sth-list { list-style: none; margin: 12px 0 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.sth-item { display: flex; gap: 10px; padding: 11px 12px; border: 1px solid var(--line-soft); border-radius: 10px; background: var(--card); }
.sth-item-ico { flex: none; width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; background: var(--line-soft); color: var(--ink-2); }
.sth-item[data-sev='warn'] .sth-item-ico { background: color-mix(in srgb, var(--warn, #d97706) 14%, transparent); color: var(--warn, #b45309); }
.sth-item-t { min-width: 0; flex: 1; }
.sth-item-t strong { font-size: 12.5px; display: block; }
.sth-item-t p { margin: 3px 0 0; font-size: 12px; color: var(--muted); line-height: 1.45; }
.sth-fix { margin-top: 8px; }
</style>
