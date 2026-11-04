<script setup>
// Equipo del club: fichas de coach con iniciales en placa, índice y rol.
// Sin equipo cargado no se pinta la sección (cero huecos).
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({
  block: { type: Object, default: null },
  sectionIndex: { type: Number, default: 0 }
})

const ctx = inject('storePage')
const { custom } = ctx

const members = computed(() => (Array.isArray(custom.value.team) ? custom.value.team : [])
  .filter((m) => String(m?.name || '').trim()))
const show = computed(() => custom.value.show_team !== false && members.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'El equipo')
const initialsOf = (name) => String(name || '')
  .split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
</script>

<template>
  <section v-if="show" class="gy-team" aria-labelledby="gy-team-title">
    <div class="gy-wrap">
      <header v-reveal class="gy-team-head">
        <div>
          <p class="gy-eyebrow"><span class="gy-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Coaches</p>
          <h2 id="gy-team-title">{{ title }}</h2>
        </div>
        <p class="gy-team-lead">{{ custom.about_specialties?.trim() || 'El equipo que acompaña cada entrenamiento.' }}</p>
      </header>
      <div class="gy-team-grid">
        <figure v-for="(m, i) in members" :key="i" v-reveal="(i % 4) * 70" class="gy-coach">
          <span class="gy-coach-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="gy-coach-plate" aria-hidden="true">
            <span class="gy-coach-initial">{{ initialsOf(m.name) }}</span>
            <span class="gy-coach-lines"></span>
          </span>
          <figcaption>
            <strong>{{ m.name }}</strong>
            <span v-if="m.role" class="gy-coach-role">{{ m.role }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>
</template>
