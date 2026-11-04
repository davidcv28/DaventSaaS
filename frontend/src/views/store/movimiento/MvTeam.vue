<script setup>
// Equipo del estudio: fila editorial de coaches — índice, nombre en
// condensada y rol, con placa de iniciales en contorno. Sin equipo
// cargado no se pinta la sección.
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
const title = computed(() => props.block?.props?.title?.trim() || 'Los coaches')
const initialsOf = (name) => String(name || '')
  .split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
</script>

<template>
  <section v-if="show" class="mv-team" aria-labelledby="mv-team-title">
    <div class="mv-wrap">
      <header v-reveal class="mv-team-head">
        <div>
          <p class="mv-eyebrow"><span class="mv-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Equipo</p>
          <h2 id="mv-team-title">{{ title }}</h2>
        </div>
        <p class="mv-team-lead">{{ custom.about_specialties?.trim() || 'El equipo que acompaña cada sesión.' }}</p>
      </header>
      <ol class="mv-team-grid">
        <li v-for="(m, i) in members" :key="i" v-reveal="(i % 4) * 70" class="mv-coach">
          <span class="mv-coach-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="mv-coach-initial" aria-hidden="true">{{ initialsOf(m.name) }}</span>
          <strong class="mv-coach-name">{{ m.name }}</strong>
          <span v-if="m.role" class="mv-coach-role">{{ m.role }}</span>
        </li>
      </ol>
    </div>
  </section>
</template>
