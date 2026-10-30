<script setup>
// Testimonios (§6.5-14): un testimonio DESTACADO grande (cita en display,
// atribución con hairline) + fila de hasta 3 testimonios secundarios, nunca
// tres tarjetas iguales. Datos reales de "Testimonios".
import { computed } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx } = useRhLinks()
const { custom } = ctx

const testimonials = computed(() => (Array.isArray(custom.value.testimonials) ? custom.value.testimonials : []))
const show = computed(() => custom.value.show_testimonials !== false && testimonials.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.testimonials_title?.trim() || 'Lo que dicen nuestros clientes')
const featured = computed(() => testimonials.value[0] || null)
const rest = computed(() => testimonials.value.slice(1, 4))
</script>

<template>
  <section v-if="show" class="rz-section rh-numbered rh-testimonials" aria-labelledby="rh-testi-title">
    <div class="rh-wrap">
      <header class="rh-head">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Clientes
          </p>
          <h2 id="rh-testi-title" v-reveal class="rh-title">{{ title }}</h2>
        </div>
      </header>

      <div class="rh-testi-grid" :class="{ 'is-solo': !rest.length }">
        <figure v-reveal class="rh-testi-main">
          <span class="rh-testi-quote" aria-hidden="true"><AppIcon name="quote" :size="26" /></span>
          <blockquote class="rh-testi-text">{{ featured.text }}</blockquote>
          <figcaption class="rh-testi-by">
            <strong>{{ featured.name }}</strong>
            <span v-if="featured.detail">{{ featured.detail }}</span>
          </figcaption>
        </figure>

        <div v-if="rest.length" class="rh-testi-row">
          <figure v-for="(t, i) in rest" :key="i" v-reveal="80 * (i + 1)" class="rh-testi-item">
            <blockquote class="rh-testi-item-text">{{ t.text }}</blockquote>
            <figcaption class="rh-testi-item-by">
              <strong>{{ t.name }}</strong>
              <span v-if="t.detail">{{ t.detail }}</span>
            </figcaption>
          </figure>
        </div>
      </div>
    </div>
  </section>
</template>
