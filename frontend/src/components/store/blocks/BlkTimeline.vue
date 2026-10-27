<script setup>
// Bloque 'timeline' (Hitos del negocio): filas {label, text} dibujadas
// como línea de tiempo — fundación, local nuevo, hitos de ventas. Se
// apaga con show_timeline y se oculta solo sin ítems. props.title pisa
// el título de la sección.
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const items = computed(() => (Array.isArray(custom.value.timeline) ? custom.value.timeline : []))
const show = computed(() => custom.value.show_timeline !== false && items.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Nuestra trayectoria')
</script>

<template>
  <section v-if="show" class="sp-timeline" aria-labelledby="sp-timeline-title">
    <div class="sp-container">
      <h2 id="sp-timeline-title" v-reveal class="sp-section-title">{{ title }}</h2>
      <ol class="sp-tl-list">
        <li v-for="(t, i) in items" :key="i" v-reveal="i * 80" class="sp-tl-item">
          <strong class="sp-tl-label">{{ t.label }}</strong>
          <span v-if="t.text" class="sp-tl-text">{{ t.text }}</span>
        </li>
      </ol>
    </div>
  </section>
</template>
