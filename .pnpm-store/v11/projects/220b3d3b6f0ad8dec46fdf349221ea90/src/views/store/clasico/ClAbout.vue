<script setup>
// «Sobre nosotros» de CLÁSICO: editorial de dos columnas con la historia real
// del negocio. Izquierda: eyebrow numerado, h2 serif, texto y hasta 3 cifras
// en serif 40 con reglas superiores de 1 px. Derecha: foto enmarcada
// (passe-partout) con pie de foto. Los campos salen de Mi empresa (about_*);
// se oculta entera si el dueño no cargó nada o apagó show_about. La foto es
// la decoración avanzada, la galería o la portada; sin foto el marco muestra
// el monograma serif del comercio. Los años cargados van como primera cifra y
// no se repiten si el dueño los puso también en Tus números.
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, shopName, hasAbout, hasDesignAdvanced, location } = ctx

const show = computed(() => hasAbout.value)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || shopName.value)
const text = computed(() => custom.value.about_text?.trim() || '')
const mission = computed(() => custom.value.about_mission?.trim() || '')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 6))
const initial = computed(() => (shopName.value || '·').trim().charAt(0).toUpperCase())

// Foto: decoración premium (primera del pool) → galería → portada premium.
const media = computed(() => {
  const decor = hasDesignAdvanced.value ? (custom.value.decor || []) : []
  const gallery = custom.value.gallery || []
  const cover = hasDesignAdvanced.value ? custom.value.cover || '' : ''
  return decor[0]?.url || gallery[0]?.url || cover || ''
})
const caption = computed(() => {
  const bits = [shopName.value, location.value].filter(Boolean).join(' · ')
  return media.value ? (bits || 'Nuestro local') : ''
})

const stats = computed(() => {
  const rows = Array.isArray(custom.value.stats) ? custom.value.stats : []
  const list = []
  if (custom.value.about_years) {
    list.push({
      value: `+${custom.value.about_years}`,
      label: Number(custom.value.about_years) === 1 ? 'Año de trayectoria' : 'Años de trayectoria'
    })
  }
  const rest = rows
    .filter((s) => s?.value && s?.label)
    .filter((s) => !(custom.value.about_years && /años?/i.test(String(s.label))))
  list.push(...rest.map((s) => ({ value: String(s.value), label: String(s.label) })))
  return list.slice(0, 3)
})
</script>

<template>
  <section v-if="show" id="nosotros" class="cl-about" aria-labelledby="cl-about-title">
    <div class="cl-container cl-about-grid">
      <div class="cl-about-copy">
        <p v-reveal class="cl-eyebrow cl-eyebrow--num"><span class="cl-eyebrow-num" aria-hidden="true"></span>Sobre nosotros</p>
        <h2 id="cl-about-title" v-reveal="60" class="cl-sec-title cl-about-title">{{ title }}</h2>
        <p v-if="text" v-reveal="110" class="cl-about-text">{{ text }}</p>
        <blockquote v-if="mission" v-reveal="150" class="cl-about-mission">{{ mission }}</blockquote>
        <ul v-if="specialties.length" v-reveal="180" class="cl-about-specialties">
          <li v-for="s in specialties" :key="s">{{ s }}</li>
        </ul>
        <dl v-if="stats.length" v-reveal="210" class="cl-about-stats">
          <div v-for="(s, i) in stats" :key="i" class="cl-about-stat">
            <dt>{{ s.label }}</dt>
            <dd>{{ s.value }}</dd>
          </div>
        </dl>
      </div>

      <figure v-reveal="120" class="cl-about-media">
        <div class="cl-about-frame">
          <img v-if="media" :src="media" :alt="`Foto de ${shopName}`" loading="lazy" decoding="async" />
          <span v-else class="cl-about-mono" aria-hidden="true">{{ initial }}</span>
        </div>
        <figcaption v-if="caption" class="cl-about-caption">{{ caption }}</figcaption>
      </figure>
    </div>
  </section>
</template>
