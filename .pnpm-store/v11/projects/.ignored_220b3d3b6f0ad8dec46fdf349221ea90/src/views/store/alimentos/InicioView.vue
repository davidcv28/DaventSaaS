<script setup>
// Inicio del diseño ALIMENTOS (gastronomía / almacén / panadería, nivel base).
// Render GENERATIVO: monta los bloques del layout efectivo de la portada
// (default de la plantilla ∪ layout_config guardado) en su orden, respetando
// enabled/variant/props. Mapa id -> componente: las piezas firma del diseño
// (AlHero, AlFeatured, AlSteps, AlHistory), los Blk* compartidos que se
// re-skinean desde store-alimentos.css y los bloques AI/extra que el motor
// puede proponer (aiquote…aimosaic, offers, video, timeline, team). Un id sin
// componente se descarta (compare no tiene componente compartido); un bloque
// sin datos se auto-oculta en su propio v-if.
// `stats` no tiene componente: el diseño fusiona las cifras dentro de
// "Nuestra historia" (AlHistory), igual que la referencia visual.
import { computed } from 'vue'
import { useLayout } from '../../../composables/useLayout.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import BlkOffers from '../../../components/store/blocks/BlkOffers.vue'
import BlkServices from '../../../components/store/blocks/BlkServices.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkVideo from '../../../components/store/blocks/BlkVideo.vue'
import BlkTimeline from '../../../components/store/blocks/BlkTimeline.vue'
import BlkTeam from '../../../components/store/blocks/BlkTeam.vue'
import BlkAiQuote from '../../../components/store/blocks/BlkAiQuote.vue'
import BlkAiStrip from '../../../components/store/blocks/BlkAiStrip.vue'
import BlkAiCheck from '../../../components/store/blocks/BlkAiCheck.vue'
import BlkAiGrid from '../../../components/store/blocks/BlkAiGrid.vue'
import BlkAiBand from '../../../components/store/blocks/BlkAiBand.vue'
import BlkAiPricing from '../../../components/store/blocks/BlkAiPricing.vue'
import BlkAiMosaic from '../../../components/store/blocks/BlkAiMosaic.vue'
import AlHero from './AlHero.vue'
import AlFeatured from './AlFeatured.vue'
import AlSteps from './AlSteps.vue'
import AlHistory from './AlHistory.vue'

const { blocks } = useLayout('landing')

const MAP = {
  announcements: BlkAnnouncements,
  hero: AlHero,
  highlights: BlkHighlights,
  categories: BlkCategories,
  featured: AlFeatured,
  steps: AlSteps,
  aiprocess: AlSteps,
  countdown: BlkCountdown,
  benefits: BlkBenefits,
  about: AlHistory,
  stats: null, // las cifras van dentro de AlHistory (sección "Nuestra historia")
  testimonials: BlkTestimonials,
  faq: BlkFaq,
  offers: BlkOffers,
  services: BlkServices,
  brands: BlkBrands,
  gallery: BlkGallery,
  video: BlkVideo,
  timeline: BlkTimeline,
  team: BlkTeam,
  cta: BlkCta,
  contact: BlkContact,
  // Bloques solo-IA (has_ai_design): el motor los propone con su id propio.
  aiquote: BlkAiQuote,
  aistrip: BlkAiStrip,
  aicheck: BlkAiCheck,
  aigrid: BlkAiGrid,
  aiband: BlkAiBand,
  aipricing: BlkAiPricing,
  aimosaic: BlkAiMosaic
}

// La cinta de anuncios de este diseño es fija (una sola secuencia centrada)
// cuando el layout no eligió variante: el default 'marquee' se montaba triple
// y en móvil se apilaba en varias líneas.
const blockOf = (b) => (b.id === 'announcements' && !b.variant ? { ...b, variant: 'static' } : b)

const visible = computed(() => blocks.value
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map((b) => ({ ...blockOf(b), comp: MAP[b.id] })))
</script>

<template>
  <div class="sp-page-root al-home">
    <component
      :is="b.comp" v-for="b in visible" :key="b.id"
      :block="b" :data-blk="b.id"
    />
  </div>
</template>
