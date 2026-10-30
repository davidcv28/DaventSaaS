<script setup>
// AlHistory — "Nuestra historia": texto real de "Mi empresa" a la izquierda y
// las cifras del negocio en serif acento a la derecha (la franja que en la
// referencia comparte la sección). Fusiona el bloque `stats` dentro de
// `about` (por eso 'stats' no tiene componente propio en el mapa del Inicio).
// Se auto-oculta sin contenido ni cifras.
import { computed } from 'vue'
import AppIcon from '../../../components/AppIcon.vue'
import { useStorePage } from '../../../composables/useStorePage.js'
import { useLayout } from '../../../composables/useLayout.js'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const { custom, hasAbout, stats, aboutSpecialties } = useStorePage()
// El bloque `stats` se fusiona acá (la referencia pone las cifras al lado de
// la historia): se respeta su on/off aunque no tenga componente propio.
const { on } = useLayout('landing')

const title = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || 'Nuestra historia')
const showStats = computed(() => on('stats') && stats.value.length > 0)
const show = computed(() => hasAbout.value || showStats.value)
const specialtyList = computed(() => aboutSpecialties.value.slice(0, 8))
</script>

<template>
  <section v-if="show" id="nosotros" class="al-history" aria-labelledby="al-history-title">
    <div class="al-container al-history-grid">
      <div v-reveal class="al-history-copy">
        <p class="al-eyebrow">Conócenos</p>
        <h2 id="al-history-title" class="al-sec-title">{{ title }}</h2>
        <p v-if="custom.about_text" class="al-history-text">{{ custom.about_text }}</p>
        <ul v-if="specialtyList.length" class="al-history-specs">
          <li v-for="s in specialtyList" :key="s">
            <span class="al-history-check" aria-hidden="true"><AppIcon name="check" :size="14" :stroke="2.6" /></span>{{ s }}
          </li>
        </ul>
        <p v-if="custom.about_years" class="al-history-years">
          <strong>+{{ custom.about_years }}</strong> años de trayectoria
        </p>
      </div>
      <div v-if="showStats" v-reveal="140" class="al-history-stats">
        <div v-for="(s, i) in stats" :key="i" class="al-history-stat">
          <strong>{{ s.value }}</strong>
          <span>{{ s.label }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
