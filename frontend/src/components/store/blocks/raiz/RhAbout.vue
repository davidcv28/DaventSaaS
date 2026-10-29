<script setup>
// Nosotros (§6.5-6): dos columnas con la imagen solapada al bloque de texto
// (la tarjeta de papel monta sobre el borde de la foto, nunca texto sobre la
// foto). Cifras inline con hairlines y especialidades como lista con guiones.
// Conserva el ancla #nosotros que usa el chrome del layout.
import { computed } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx } = useRhLinks()
const { custom, shopName, hasAbout, hasDesignAdvanced } = ctx

const title = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || 'Sobre nosotros')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))
const hasCard = computed(() => Boolean(custom.value.about_years || custom.value.about_mission?.trim()))

// Imagen: decorativa premium → última foto real de la galería. Sin material
// la sección queda en una columna (nunca una silueta vacía ni una carga
// tardía que mueva el texto).
const image = computed(() => {
  if (hasDesignAdvanced.value && custom.value.decor?.[0]?.url) {
    return { url: custom.value.decor[0].url, alt: `Imagen de ${shopName.value}` }
  }
  const photos = Array.isArray(custom.value.gallery) ? custom.value.gallery : []
  const photo = photos.length > 1 ? photos[photos.length - 1] : null
  if (photo?.url) return { url: photo.url, alt: `Imagen de ${shopName.value}` }
  return null
})
</script>

<template>
  <section v-if="hasAbout" id="nosotros" class="rz-section rh-numbered rh-about" aria-labelledby="rh-about-title">
    <div class="rh-wrap rh-about-grid" :class="{ 'is-solo': !image }">
      <figure v-if="image" v-reveal class="rz-frame rh-about-media">
        <img :src="image.url" :alt="image.alt" loading="lazy" decoding="async" />
      </figure>

      <div v-reveal="80" class="rh-about-copy">
        <p v-reveal class="rz-eyebrow">
          <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
          Nosotros
        </p>
        <h2 id="rh-about-title" class="rh-title rh-about-title">{{ title }}</h2>
        <p v-if="custom.about_text" class="rh-about-text">{{ custom.about_text }}</p>

        <ul v-if="specialties.length" class="rh-about-specs">
          <li v-for="s in specialties" :key="s"><span aria-hidden="true">—</span> {{ s }}</li>
        </ul>

        <div v-if="hasCard" class="rh-about-facts">
          <div v-if="custom.about_years" class="rh-about-fact">
            <strong><span aria-hidden="true">+</span>{{ custom.about_years }}</strong>
            <span>años de trayectoria</span>
          </div>
          <blockquote v-if="custom.about_mission" class="rh-about-mission">
            <span class="rh-about-mission-label" aria-hidden="true"><AppIcon name="quote" :size="16" /> Nuestra misión</span>
            {{ custom.about_mission }}
          </blockquote>
        </div>
      </div>
    </div>
  </section>
</template>
