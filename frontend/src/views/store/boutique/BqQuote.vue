<script setup>
// Testimonio único centrado de BOUTIQUE: cita en serif itálica con comillas
// grandes y la firma en versalitas. Se auto-oculta sin testimonios y respeta
// show_testimonials. El diseño muestra la primera opinión; el resto sigue
// disponible en los datos de la tienda (no se inventa copy).
// Jerarquía: eyebrow "Testimonios" con regla, cita y firma separadas por un
// hairline; el marco y las comillas entran animados (ver motion sheet).
import { computed, inject } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const testimonial = computed(() => {
  const list = Array.isArray(custom.value.testimonials) ? custom.value.testimonials : []
  return list.find((t) => String(t?.text || '').trim()) || null
})
const show = computed(() => custom.value.show_testimonials !== false && Boolean(testimonial.value))
</script>

<template>
  <section v-if="show" class="bq-quote" aria-label="Testimonios de clientes">
    <div class="bq-container bq-quote-inner">
      <p v-reveal class="bq-quote-eyebrow">
        <span class="bq-eyebrow">Testimonios</span>
        <span class="bq-eyebrow-rule" aria-hidden="true"></span>
      </p>
      <span class="bq-quote-mark" aria-hidden="true">“</span>
      <blockquote v-reveal class="bq-quote-text">{{ testimonial.text }}</blockquote>
      <p v-reveal="80" class="bq-quote-by">
        <strong>{{ testimonial.name }}</strong>
        <span v-if="testimonial.detail">{{ testimonial.detail }}</span>
      </p>
    </div>
  </section>
</template>
