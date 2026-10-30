<script setup>
// Bloque 'about' (Sobre nosotros): contenido a la izquierda con la foto
// decorativa al costado; la tarjeta de trayectoria/misión baja a una
// banda a todo lo ancho. Se edita en "Mi empresa" del dashboard; el
// dueño la apaga con show_about y además se oculta sola si no cargó
// ningún contenido. props.title pisa el título de la sección.
import { computed, inject } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, shopName, hasAbout, hasDesignAdvanced } = ctx

const aboutSpecialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))
// Tarjeta destacada de la sección (columna derecha): solo existe si hay
// años de trayectoria o misión cargados; sin ellos la info va a una columna.
const hasAboutCard = computed(() => Boolean(custom.value.about_years || custom.value.about_mission?.trim()))
const aboutTitle = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || 'Sobre nosotros')
// Primera imagen ilustrativa de la portada (premium) enmarca la sección.
const decorAbout = computed(() => (hasAbout.value && hasDesignAdvanced.value ? (custom.value.decor || [])[0] || null : null))
</script>

<template>
  <section v-if="hasAbout" id="nosotros" class="sp-about" aria-labelledby="sp-about-title">
    <div class="sp-container sp-about-grid" :class="{ 'no-side': !decorAbout }">
      <div v-reveal class="sp-about-info">
        <p class="sp-eyebrow">Conócenos</p>
        <h2 id="sp-about-title" class="sp-about-heading">
          <span class="sp-about-heading-icon" aria-hidden="true"><AppIcon name="store" :size="26" /></span>
          {{ aboutTitle }}
        </h2>
        <p v-if="custom.about_text" class="sp-about-text">{{ custom.about_text }}</p>
        <ul v-if="aboutSpecialties.length" class="sp-about-list">
          <li v-for="s in aboutSpecialties" :key="s"><AppIcon name="check" :size="16" /> <span>{{ s }}</span></li>
        </ul>
      </div>
      <div v-if="decorAbout" class="sp-about-side">
        <figure v-reveal="140" class="sp-about-photo">
          <img :src="decorAbout.url" :alt="`Imagen de ${shopName}`" loading="lazy" />
        </figure>
      </div>
      <div v-if="hasAboutCard" v-reveal="140" class="sp-about-card">
        <p v-if="custom.about_years" class="sp-about-years">
          <strong>+{{ custom.about_years }}</strong>
          <span>años de trayectoria</span>
        </p>
        <blockquote v-if="custom.about_mission" class="sp-about-mission">
          <span class="sp-about-mission-label">Nuestra misión</span>
          {{ custom.about_mission }}
        </blockquote>
      </div>
    </div>
  </section>
</template>
