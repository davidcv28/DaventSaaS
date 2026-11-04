<script setup>
// Bloque 'timeline' de MOVIMIENTO: el método del estudio como 3 pasos
// numerados (índice editorial gigante, título condensado, bajada). Lee
// custom.timeline {label, text}; sin ítems se auto-oculta.
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({
  block: { type: Object, default: null },
  sectionIndex: { type: Number, default: 0 }
})

const ctx = inject('storePage')
const { custom } = ctx

const items = computed(() => (Array.isArray(custom.value.timeline) ? custom.value.timeline : [])
  .filter((t) => String(t?.label || '').trim()).slice(0, 5))
const show = computed(() => custom.value.show_timeline !== false && items.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'El método')
</script>

<template>
  <section v-if="show" class="mv-method" aria-labelledby="mv-method-title">
    <div class="mv-wrap">
      <header v-reveal class="mv-method-head">
        <p class="mv-eyebrow"><span class="mv-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Cómo funciona</p>
        <h2 id="mv-method-title">{{ title }}</h2>
      </header>
      <ol class="mv-method-list">
        <li v-for="(t, i) in items" :key="i" v-reveal="i * 90" class="mv-step">
          <span class="mv-step-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <div class="mv-step-body">
            <strong class="mv-step-title">{{ t.label }}</strong>
            <p v-if="t.text" class="mv-step-text">{{ t.text }}</p>
          </div>
        </li>
      </ol>
    </div>
  </section>
</template>
