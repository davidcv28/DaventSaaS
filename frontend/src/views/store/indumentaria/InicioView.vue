<script setup>
// Inicio del diseño INDUMENTARIA (8º, nivel plus): misma PIEL que Trama
// (store-trama.css, scopeada por data-skin='indumentaria') pero composición
// PROPIA. Reusa las piezas firma de trama (TrHero, TrCategories, TrFeatured,
// TrAbout, TrTrust) montadas desde ../trama/ — no se duplica CSS ni markup — y
// el resto de los bloques entra por landingExtras/Blk* compartidos y
// re-skineados por la piel común.
//
// Portada GENERATIVA: monta el layout efectivo de useLayout('landing') (default
// de templates/indumentaria ∪ layout_config guardado) respetando on/off, orden,
// variante y props. El default del SPEC es: announcements(static), hero,
// benefits, categories, featured, about, countdown(band), offers(grid),
// services, testimonials(cards), gallery(grid), faq, cta(band) y contact(card).
// Cada bloque se auto-oculta sin datos y un id sin componente se descarta.
import { computed, inject } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { landingExtras } from '../../../templates/_shared.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import TrHero from '../trama/TrHero.vue'
import TrTrust from '../trama/TrTrust.vue'
import TrCategories from '../trama/TrCategories.vue'
import TrFeatured from '../trama/TrFeatured.vue'
import TrAbout from '../trama/TrAbout.vue'

const ctx = inject('storePage')
const { custom } = ctx

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: TrHero,
  categories: TrCategories,
  featured: TrFeatured,
  about: TrAbout,
  benefits: TrTrust,
  // Banda CTA de cierre y Contáctanos (resolveLayout fuerza contact al final):
  // Blk* compartidos eskinados por la piel común.
  cta: BlkCta,
  contact: BlkContact
}

// Variantes firma del diseño. El layout manda: si el Studio o la IA ya fijaron
// variant/props se respetan; acá solo se completan los defaults del SPEC y los
// títulos propios del dueño (que tienen prioridad).
const FIRMA = {
  announcements: 'static',
  countdown: 'band',
  offers: 'grid',
  testimonials: 'cards',
  gallery: 'grid',
  faq: 'accordion',
  cta: 'band',
  contact: 'card'
}

function withDefaults(block) {
  if (block.id === 'featured') {
    return { ...block, variant: block.variant || 'grid', props: { title: 'Recién llegado', ...(block.props || {}) } }
  }
  if (block.id === 'services') {
    const own = custom.value.services_title?.trim()
    return { ...block, props: { title: own || 'Por qué elegirnos', ...(block.props || {}) } }
  }
  if (block.id === 'testimonials') {
    const own = custom.value.testimonials_title?.trim()
    return { ...block, props: { title: own || 'Opiniones de clientes', ...(block.props || {}) } }
  }
  if (block.id === 'gallery') {
    return { ...block, variant: block.variant || 'grid', props: { title: 'Galería', ...(block.props || {}) } }
  }
  if (block.id === 'contact') {
    return { ...block, variant: block.variant || 'card', props: { title: 'Hablemos', ...(block.props || {}) } }
  }
  return block
}

const visible = computed(() => templateBlocks(ctx.pageTemplate.value, 'landing')
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map((b) => {
    const next = b.variant ? b : { ...b, variant: FIRMA[b.id] }
    return withDefaults(next)
  }))
</script>

<template>
  <div class="sp-page-root tr-home in-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </div>
</template>
