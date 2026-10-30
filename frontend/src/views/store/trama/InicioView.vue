<script setup>
// Inicio del diseño TRAMA («Indumentaria · Profesional»).
// Portada GENERATIVA: monta los bloques del layout efectivo de useLayout
// ('landing' = default de la plantilla ∪ layout_config guardado) respetando
// on/off, orden, variante y props. El default es la composición del SPEC:
// utility bar, hero partido, franja de garantías, categorías con línea de
// prenda, Recién llegado con tabs, editorial + cifras, banda de cuenta
// regresiva, Por qué elegirnos, marcas, opiniones, galería, FAQ, banda CTA y
// contacto. Las piezas firma (Tr*) viven en esta carpeta; el resto son los
// Blk* compartidos re-skineados por store-trama.css. `highlights` NO está en
// el default pero el mapa lo sigue montando si una config guardada/IA lo pide;
// los extras del motor v8 (ofertas, video, trayectoria, equipo, aiquote…)
// también entran por landingExtras. Cada bloque se auto-oculta sin datos y un
// id sin componente se descarta (nunca deja un hueco).
import { computed, inject } from 'vue'
import { useLayout } from '../../../composables/useLayout.js'
import { landingExtras } from '../../../templates/_shared.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import TrHero from './TrHero.vue'
import TrTrust from './TrTrust.vue'
import TrCategories from './TrCategories.vue'
import TrFeatured from './TrFeatured.vue'
import TrAbout from './TrAbout.vue'

const ctx = inject('storePage')
const { custom } = ctx

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: TrHero,
  highlights: BlkHighlights,
  categories: TrCategories,
  featured: TrFeatured,
  about: TrAbout,
  benefits: TrTrust,
  // `landingExtras` no trae estos dos ids: son parte fija del default del
  // diseño (banda CTA de cierre y Contáctanos, que resolveLayout fuerza al
  // final), así que se montan con los Blk* compartidos eskinados por la piel.
  cta: BlkCta,
  contact: BlkContact
}

// Copy/estructura por defecto del diseño. El layout manda: si el Studio o la
// IA ya fijaron variant/props se respetan; acá solo se completan los títulos
// que el SPEC define (y el título propio del dueño tiene prioridad).
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

const { blocks } = useLayout('landing')
const visible = computed(() => blocks.value
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map(withDefaults))
</script>

<template>
  <div class="sp-page-root tr-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </div>
</template>
