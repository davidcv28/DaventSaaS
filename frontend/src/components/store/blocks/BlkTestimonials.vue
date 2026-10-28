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
const variant = computed(() => props.block?.variant || 'cards')

// Carrusel: riel con scroll-snap y flechas (scrollBy respeta la dirección
// y la cantidad visible del contenedor).
const testiGrid = ref(null)
function railBy(dir) {
  const el = testiGrid.value
  if (el) el.scrollBy({ left: dir * el.clientWidth * 0.85, behavior: 'smooth' })
}
let testiRO = null
function equalizeTestimonials() {
  const grid = testiGrid.value
  if (!grid) return
  // Solo la grilla 'cards' iguala alturas: en carrusel y masonry cada
  // tarjeta conserva su alto natural.
  if (variant.value !== 'cards') { grid.querySelectorAll('.sp-testimonial').forEach((c) => { c.style.minHeight = '' }); return }
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
  <section v-if="show" class="sp-testimonials" :class="`is-${variant}`" :data-blk-variant="variant !== 'cards' ? variant : null" aria-labelledby="sp-testimonials-title">
    <div class="sp-container">
      <p v-if="testimonialsEyebrow" class="sp-eyebrow">{{ testimonialsEyebrow }}</p>
      <div class="sp-testimonials-head">
        <h2 id="sp-testimonials-title" v-reveal class="sp-section-title">{{ testimonialsTitle }}</h2>
        <div v-if="variant === 'carousel' && testimonials.length > 1" class="sp-rail-nav">
          <button type="button" class="sp-rail-btn" aria-label="Testimonios anteriores" @click="railBy(-1)"><AppIcon name="chevron-left" :size="18" /></button>
          <button type="button" class="sp-rail-btn" aria-label="Testimonios siguientes" @click="railBy(1)"><AppIcon name="chevron-right" :size="18" /></button>
        </div>
      </div>
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
