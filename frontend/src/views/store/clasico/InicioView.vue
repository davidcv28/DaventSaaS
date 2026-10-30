<script setup>
// Inicio del diseño CLÁSICO (comercio y servicios con oficio).
// Portada GENERATIVA: monta el layout efectivo de useLayout('landing') — el
// default de templates/clasico/index.js ∪ layout_config guardado — respetando
// on/off, orden, variante y props. El default canónico es: cinta de anuncios
// static, hero asimétrico, garantías numeradas, categorías, destacados con
// tabs, editorial «nosotros», banda de cuenta regresiva, servicios numerados,
// marcas, testimonios, galería, FAQ, banda CTA y contacto. Las piezas firma
// (Cl*) viven en esta carpeta; el resto son los Blk* compartidos re-skineados
// por store-clasico.css. `landingExtras` sigue disponible: si el Studio o la
// IA suman un bloque extra (ofertas, video, equipo, aiquote…) también se
// monta. Cada sección se auto-oculta sin datos y un id sin componente se
// descarta (nunca deja un hueco).
import { computed, inject } from 'vue'
import { useLayout } from '../../../composables/useLayout.js'
import { landingExtras } from '../../../templates/_shared.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import ClHero from './ClHero.vue'
import ClCategories from './ClCategories.vue'
import ClFeatured from './ClFeatured.vue'
import ClAbout from './ClAbout.vue'

const ctx = inject('storePage')
const { custom } = ctx

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: ClHero,
  highlights: BlkHighlights,
  categories: ClCategories,
  featured: ClFeatured,
  about: ClAbout,
  benefits: BlkBenefits,
  // No vienen en landingExtras: son parte fija del default del diseño
  // (banda CTA de cierre y Contáctanos, que resolveLayout fuerza al final).
  cta: BlkCta,
  contact: BlkContact
}

// Copy por defecto del diseño. El layout manda: si el Studio o la IA ya
// fijaron variant/props se respetan; acá solo se completan los títulos que el
// SPEC define y el título propio del dueño tiene prioridad.
function withDefaults(block) {
  if (block.id === 'featured') {
    return { ...block, variant: block.variant || 'grid', props: { title: 'Destacados', ...(block.props || {}) } }
  }
  if (block.id === 'categories') {
    return { ...block, props: { title: 'Explorá el catálogo', ...(block.props || {}) } }
  }
  if (block.id === 'benefits') {
    return { ...block, props: { title: 'Por qué elegirnos', ...(block.props || {}) } }
  }
  if (block.id === 'services') {
    const own = custom.value.services_title?.trim()
    return { ...block, props: { title: own || 'Cómo trabajamos', ...(block.props || {}) } }
  }
  if (block.id === 'testimonials') {
    const own = custom.value.testimonials_title?.trim()
    return { ...block, props: { title: own || 'Lo que dicen nuestros clientes', ...(block.props || {}) } }
  }
  if (block.id === 'gallery') {
    return { ...block, variant: block.variant || 'grid', props: { title: 'Galería', ...(block.props || {}) } }
  }
  if (block.id === 'contact') {
    return { ...block, variant: block.variant || 'card', props: { title: 'Hablemos', ...(block.props || {}) } }
  }
  if (block.id === 'cta') {
    return { ...block, variant: block.variant || 'band' }
  }
  return block
}

const { blocks } = useLayout('landing')
const visible = computed(() => blocks.value
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map(withDefaults))
</script>

<template>
  <div class="sp-page-root cl-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" />
  </div>
</template>
