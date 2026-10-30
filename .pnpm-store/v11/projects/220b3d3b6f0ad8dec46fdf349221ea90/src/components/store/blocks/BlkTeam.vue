<script setup>
// Bloque 'team' (Equipo): filas {name, role} dibujadas como tarjetas con
// iniciales sobre círculo de acento. Se apaga con show_team y se oculta
// solo sin miembros. props.title pisa el título de la sección.
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const members = computed(() => (Array.isArray(custom.value.team) ? custom.value.team : []))
const show = computed(() => custom.value.show_team !== false && members.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Nuestro equipo')
const initialsOf = (name) => String(name || '')
  .split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
</script>

<template>
  <section v-if="show" class="sp-team" aria-labelledby="sp-team-title">
    <div class="sp-container">
      <h2 id="sp-team-title" v-reveal class="sp-section-title">{{ title }}</h2>
      <div class="sp-team-grid">
        <figure v-for="(m, i) in members" :key="i" v-reveal="(i % 4) * 70" class="sp-member">
          <span class="sp-member-initial" aria-hidden="true">{{ initialsOf(m.name) }}</span>
          <figcaption>
            <strong>{{ m.name }}</strong>
            <span v-if="m.role" class="sp-member-role">{{ m.role }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>
</template>
