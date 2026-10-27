<script setup>
// Bloque 'testimonials': citas de clientes en tarjetas de alto igualado
// (el grid solo estira por fila, así que se mide la tarjeta más alta y
// se iguala el resto con min-height — offsetHeight ignora el transform
// de la animación de entrada). props.title pisa el título de la sección.
import { ref, computed, inject, watch, nextTick, onBeforeUnmount } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const testimonials = computed(() => (Array.isArray(custom.value.testimonials) ? custom.value.testimonials : []))
const show = computed(() => custom.value.show_testimonials !== false && testimonials.value.length > 0)
const testimonialsTitle = computed(() => props.block?.props?.title?.trim() || custom.value.testimonials_title?.trim() || 'Lo que dicen nuestros clientes')
const eyebrowUnless = (label, title) => (String(title || '').trim().toLowerCase() === label.toLowerCase() ? '' : label)
const testimonialsEyebrow = computed(() => eyebrowUnless('Clientes', testimonialsTitle.value))

const testiGrid = ref(null)
let testiRO = null
function equalizeTestimonials() {
  const grid = testiGrid.value
  if (!grid) return
  const cards = grid.querySelectorAll('.sp-testimonial')
  cards.forEach((c) => { c.style.minHeight = '' })
  const max = Math.ceil(Math.max(0, ...[...cards].map((c) => c.offsetHeight)))
  if (max) cards.forEach((c) => { c.style.minHeight = `${max}px` })
}
watch(testiGrid, (el) => {
  testiRO?.disconnect()
  testiRO = null
  if (el && 'ResizeObserver' in window) { testiRO = new ResizeObserver(equalizeTestimonials); testiRO.observe(el) }
  nextTick(equalizeTestimonials)
})
watch(testimonials, () => nextTick(equalizeTestimonials))
onBeforeUnmount(() => testiRO?.disconnect())
</script>

<template>
  <section v-if="show" class="sp-testimonials" aria-labelledby="sp-testimonials-title">
    <div class="sp-container">
      <p v-if="testimonialsEyebrow" class="sp-eyebrow">{{ testimonialsEyebrow }}</p>
      <h2 id="sp-testimonials-title" v-reveal class="sp-section-title">{{ testimonialsTitle }}</h2>
      <div ref="testiGrid" class="sp-testimonials-grid">
        <figure v-for="(t, i) in testimonials" :key="i" v-reveal="(i % 3) * 80" class="sp-testimonial">
          <span class="sp-testimonial-quote" aria-hidden="true"><AppIcon name="quote" :size="20" /></span>
          <blockquote class="sp-testimonial-text">{{ t.text }}</blockquote>
          <figcaption class="sp-testimonial-by">
            <strong>{{ t.name }}</strong>
            <span v-if="t.detail">{{ t.detail }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </section>
</template>
