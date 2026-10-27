<script setup>
// Bloque 'stats' (Tus números): banda de cifras destacadas. Variante
// 'band' (default) = franja de acento; 'cards' = tarjetas sueltas sobre
// el fondo de la página. props.title agrega un título visible arriba de
// la banda (ocupa la fila completa del grid; por defecto la sección no
// lleva título).
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const stats = computed(() => (Array.isArray(custom.value.stats) ? custom.value.stats : []))
const show = computed(() => custom.value.show_stats !== false && stats.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || '')
const isCards = computed(() => props.block?.variant === 'cards')
</script>

<template>
  <section v-if="show" class="sp-stats" :class="{ 'is-cards': isCards }" :aria-label="title || 'Cifras del negocio'">
    <div class="sp-container sp-stats-grid">
      <h2 v-if="title" v-reveal class="sp-stats-title">{{ title }}</h2>
      <div v-for="(s, i) in stats" :key="i" v-reveal="i * 80" class="sp-stat">
        <strong>{{ s.value }}</strong>
        <span>{{ s.label }}</span>
      </div>
    </div>
  </section>
</template>
