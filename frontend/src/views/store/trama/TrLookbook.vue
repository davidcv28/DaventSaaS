<script setup>
// Banda "lookbook" de TRAMA: placa oscura a dos tintas con la foto de la
// galería (o la portada premium) y el contenido de "Sobre nosotros" + las
// cifras reales del negocio. Se oculta entera si el dueño no cargó ninguno
// de esos campos (misma regla que hasAbout del layout).
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { custom, shopName, initial, hasDesignAdvanced } = ctx

const hasAbout = computed(() => custom.value.show_about !== false && Boolean(
  custom.value.about_title?.trim()
  || custom.value.about_text?.trim()
  || custom.value.about_mission?.trim()
  || custom.value.about_specialties?.trim()
))
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))
const image = computed(() => (
  (custom.value.gallery || [])[0]?.url
  || (hasDesignAdvanced.value ? custom.value.cover || '' : '')
))
const title = computed(() => custom.value.about_title?.trim() || shopName.value)
const stats = computed(() => {
  const rows = Array.isArray(custom.value.stats) ? custom.value.stats : []
  // "12 años" ya va como primera cifra: no repetir la fila de años cargada
  // en Tus números (evita 12 AÑOS / 12 AÑOS DE TRAYECTORIA).
  const filtered = rows.filter((s) => !(custom.value.about_years && /años?/i.test(String(s.label || ''))))
  return filtered.slice(0, custom.value.about_years ? 2 : 3)
})
const years = computed(() => custom.value.about_years || '')
</script>

<template>
  <section v-if="hasAbout" id="nosotros" class="tr-look" aria-labelledby="tr-look-title">
    <figure class="tr-look-media">
      <img v-if="image" :src="image" :alt="`Lookbook de ${shopName}`" loading="lazy" decoding="async" />
      <span v-else class="tr-look-ph" aria-hidden="true">{{ initial }}</span>
    </figure>
    <div class="tr-look-copy">
      <p v-reveal class="tr-eyebrow tr-eyebrow--accent">Sobre nosotros</p>
      <h2 id="tr-look-title" v-reveal="60" class="tr-look-title">{{ title }}</h2>
      <p v-if="custom.about_text" v-reveal="120" class="tr-look-text">{{ custom.about_text }}</p>
      <p v-if="custom.about_mission" v-reveal="160" class="tr-look-mission">{{ custom.about_mission }}</p>
      <ul v-if="specialties.length" v-reveal="180" class="tr-look-specialties">
        <li v-for="s in specialties" :key="s">{{ s }}</li>
      </ul>
      <ul v-if="stats.length || years" v-reveal="200" class="tr-look-stats">
        <li v-if="years">
          <strong>{{ years }}</strong>
          <span>{{ Number(years) === 1 ? 'año' : 'años' }}</span>
        </li>
        <li v-for="(s, i) in stats" :key="i">
          <strong>{{ s.value }}</strong>
          <span>{{ s.label }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
