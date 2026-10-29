<script setup>
// Cifras del negocio en banda negra: 4 números condensados con regla
// amarilla superior (firma de la referencia). Consume stats reales del dueño
// y respeta el interruptor show_stats; sin números no se monta.
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const stats = computed(() => (Array.isArray(custom.value.stats) ? custom.value.stats : []))
const show = computed(() => custom.value.show_stats !== false && stats.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || '')
</script>

<template>
  <section v-if="show" class="sg-stats" :aria-label="title || 'Cifras del negocio'">
    <div class="sg-wrap">
      <h2 v-if="title" v-reveal class="sg-stats-title">{{ title }}</h2>
      <dl class="sg-stats-grid">
        <div v-for="(s, i) in stats" :key="i" v-reveal="i * 70" class="sg-stat">
          <dt class="sg-stat-label">{{ s.label }}</dt>
          <dd class="sg-stat-value">{{ s.value }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>
