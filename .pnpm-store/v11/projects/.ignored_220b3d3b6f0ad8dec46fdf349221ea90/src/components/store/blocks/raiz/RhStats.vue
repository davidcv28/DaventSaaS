<script setup>
// Cifras (§6.5-7): banda de papel con numerales gigantes y label, SIN
// tarjetas. Datos reales de "Tus números" ({value,label}, máx 4), separados
// por reglas hairline.
import { computed } from 'vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx } = useRhLinks()
const { custom } = ctx

const stats = computed(() => (Array.isArray(custom.value.stats) ? custom.value.stats : []))
const show = computed(() => custom.value.show_stats !== false && stats.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'En números')
</script>

<template>
  <section v-if="show" class="rz-section rh-numbered rh-stats" :aria-label="title">
    <div class="rh-wrap">
      <p class="rz-eyebrow rh-stats-eyebrow">
        <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
        {{ title }}
      </p>
      <div class="rh-stats-grid">
        <div v-for="(s, i) in stats" :key="i" v-reveal="60 * i" class="rh-stat">
          <span class="rh-stat-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <strong class="rh-stat-value">{{ s.value }}</strong>
          <span class="rh-stat-label">{{ s.label }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
