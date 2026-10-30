<script setup>
// "¿Qué extintor necesito?" — grilla A/B/C/K de clases de fuego. Se alimenta
// del bloque generativo 'aigrid' del layout (items con título y texto que
// arma el motor de IA). Sin ítems el bloque no se monta: la sección nunca
// aparece vacía ni con contenido de relleno.
import { computed } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const LETTERS = ['A', 'B', 'C', 'K']
const items = computed(() => {
  const raw = props.block?.props?.items
  if (!Array.isArray(raw)) return []
  return raw
    .map((item) => ({
      title: String(item?.title || '').trim().slice(0, 60),
      text: String(item?.text || '').trim().slice(0, 160)
    }))
    .filter((item) => item.title || item.text)
    .slice(0, LETTERS.length)
})
const title = computed(() => props.block?.props?.title?.trim() || '¿Qué extintor necesito?')
</script>

<template>
  <section v-if="items.length" class="sg-classes" aria-labelledby="sg-classes-title">
    <div class="sg-wrap">
      <h2 id="sg-classes-title" v-reveal class="sg-sec-title">{{ title }}</h2>
      <ul class="sg-classes-grid">
        <li v-for="(item, i) in items" :key="`${i}-${item.title}`" v-reveal="(i % 4) * 70" class="sg-class">
          <span class="sg-class-letter" aria-hidden="true">{{ LETTERS[i] }}</span>
          <strong v-if="item.title" class="sg-class-title">{{ item.title }}</strong>
          <span v-if="item.text" class="sg-class-text">{{ item.text }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
