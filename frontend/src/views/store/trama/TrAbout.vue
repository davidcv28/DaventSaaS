<script setup>
// «Sobre nosotros» de TRAMA: editorial a dos columnas (imagen + copy) con la
// historia real del negocio y una fila de hasta 3 cifras. Los campos salen de
// Mi empresa (about_*); se oculta entera si el dueño no cargó nada o apagó
// show_about. La imagen es la decoración premium, la galería o la portada; sin
// foto el panel muestra la línea de prenda con un chip. Los años cargados van
// como primera cifra y no se repiten si el dueño los puso también en Tus
// números.
import { computed, inject } from 'vue'
import GarmentLine from './GarmentLine.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, shopName, hasAbout, hasDesignAdvanced } = ctx

const show = computed(() => hasAbout.value)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || shopName.value)
const text = computed(() => custom.value.about_text?.trim() || '')
const mission = computed(() => custom.value.about_mission?.trim() || '')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))

// Foto: decoración premium (primera del pool) → galería → portada premium.
const media = computed(() => {
  const decor = hasDesignAdvanced.value ? (custom.value.decor || []) : []
  const gallery = custom.value.gallery || []
  const cover = hasDesignAdvanced.value ? custom.value.cover || '' : ''
  return decor[0]?.url || gallery[0]?.url || cover || ''
})
const chip = computed(() => (media.value ? shopName.value : 'Foto del local'))

const stats = computed(() => {
  const rows = Array.isArray(custom.value.stats) ? custom.value.stats : []
  const list = []
  if (custom.value.about_years) {
    list.push({ value: `+${custom.value.about_years}`, label: Number(custom.value.about_years) === 1 ? 'Año de trayectoria' : 'Años de trayectoria' })
  }
  const rest = rows
    .filter((s) => s?.value && s?.label)
    .filter((s) => !(custom.value.about_years && /años?/i.test(String(s.label))))
  list.push(...rest.map((s) => ({ value: String(s.value), label: String(s.label) })))
  return list.slice(0, 3)
})
</script>

<template>
  <section v-if="show" id="nosotros" class="tr-about" aria-labelledby="tr-about-title">
    <div class="tr-about-media">
      <figure v-reveal class="tr-about-figure">
        <img v-if="media" :src="media" :alt="`Foto de ${shopName}`" loading="lazy" decoding="async" />
        <span v-else class="tr-about-garment" aria-hidden="true"><GarmentLine name="hoodie" /></span>
        <span class="tr-about-chip">{{ chip }}</span>
      </figure>
    </div>

    <div class="tr-about-copy">
      <p v-reveal class="tr-eyebrow">Sobre nosotros</p>
      <h2 id="tr-about-title" v-reveal="60" class="tr-about-title">{{ title }}</h2>
      <p v-if="text" v-reveal="110" class="tr-about-text">{{ text }}</p>
      <blockquote v-if="mission" v-reveal="150" class="tr-about-mission">{{ mission }}</blockquote>
      <ul v-if="specialties.length" v-reveal="180" class="tr-about-specialties">
        <li v-for="s in specialties" :key="s">{{ s }}</li>
      </ul>
      <div v-if="stats.length" v-reveal="210" class="tr-about-stats">
        <div v-for="(s, i) in stats" :key="i" class="tr-about-stat">
          <strong>{{ s.value }}</strong>
          <span>{{ s.label }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
