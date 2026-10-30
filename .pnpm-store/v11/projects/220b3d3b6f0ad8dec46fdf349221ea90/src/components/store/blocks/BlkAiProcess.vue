<script setup>
// Bloque 'aiprocess' (solo IA): 3 a 5 pasos numerados con título y texto.
// Sin pasos no monta. Variantes: steps (por defecto) | rail.
import { computed } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const title = computed(() => String(props.block?.props?.title || '').trim().slice(0, 80))
const items = computed(() => {
  const raw = props.block?.props?.items
  if (!Array.isArray(raw)) return []
  return raw
    .map((i) => ({
      title: String(i?.title || '').trim().slice(0, 60),
      text: String(i?.text || '').trim().slice(0, 160)
    }))
    .filter((i) => i.title || i.text)
    .slice(0, 5)
})
const variant = computed(() => (props.block?.variant === 'rail' ? 'rail' : 'steps'))
</script>

<template>
  <section v-if="items.length >= 3" class="sp-aiprocess" :class="`is-${variant}`" :data-blk-variant="variant !== 'steps' ? variant : null">
    <div class="sp-container sp-aiprocess-inner">
      <h2 v-if="title" v-reveal class="sp-section-title sp-aiprocess-title">{{ title }}</h2>
      <ol class="sp-aiprocess-list">
        <li v-for="(step, i) in items" :key="`${i}-${step.title}`" v-reveal="(i % 4) * 70" class="sp-aiprocess-step">
          <span class="sp-aiprocess-num" aria-hidden="true">{{ i + 1 }}</span>
          <h3 v-if="step.title" class="sp-aiprocess-step-title">{{ step.title }}</h3>
          <p v-if="step.text" class="sp-aiprocess-text">{{ step.text }}</p>
        </li>
      </ol>
    </div>
  </section>
</template>
