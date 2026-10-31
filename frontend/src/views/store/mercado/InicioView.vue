<script setup>
// Inicio del diseño MERCADO (marketplace, nivel plus).
// Render GENERATIVO: monta los bloques del layout efectivo de la portada.
// Piezas firma: McHero (banda amarilla + oferta destacada), McCategories
// (departamentos circulares), McOffers (riel de descuentos), McFeatured
// (grilla densa) y McBenefits (franja de confianza). El resto son los bloques
// compartidos, re-skineados desde store-mercado.css.
import { computed, ref } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { useStorePage } from '../../../composables/useStorePage.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkAbout from '../../../components/store/blocks/BlkAbout.vue'
import BlkServices from '../../../components/store/blocks/BlkServices.vue'
import BlkStats from '../../../components/store/blocks/BlkStats.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import BlkVideo from '../../../components/store/blocks/BlkVideo.vue'
import BlkTimeline from '../../../components/store/blocks/BlkTimeline.vue'
import BlkTeam from '../../../components/store/blocks/BlkTeam.vue'
import BlkAiQuote from '../../../components/store/blocks/BlkAiQuote.vue'
import BlkAiStrip from '../../../components/store/blocks/BlkAiStrip.vue'
import BlkAiCheck from '../../../components/store/blocks/BlkAiCheck.vue'
import BlkAiGrid from '../../../components/store/blocks/BlkAiGrid.vue'
import BlkAiBand from '../../../components/store/blocks/BlkAiBand.vue'
import BlkAiProcess from '../../../components/store/blocks/BlkAiProcess.vue'
import BlkAiPricing from '../../../components/store/blocks/BlkAiPricing.vue'
import BlkAiMosaic from '../../../components/store/blocks/BlkAiMosaic.vue'
import McHero from './McHero.vue'
import McCategories from './McCategories.vue'
import McOffers from './McOffers.vue'
import McFeatured from './McFeatured.vue'
import McBenefits from './McBenefits.vue'
import { useCardTitles } from './useCardTitles.js'

const { pageTemplate } = useStorePage()
const pageEl = ref(null)
useCardTitles(pageEl)

const MAP = {
  announcements: BlkAnnouncements,
  hero: McHero,
  categories: McCategories,
  offers: McOffers,
  featured: McFeatured,
  highlights: McBenefits,
  benefits: McBenefits,
  about: BlkAbout,
  services: BlkServices,
  stats: BlkStats,
  brands: BlkBrands,
  countdown: BlkCountdown,
  gallery: BlkGallery,
  testimonials: BlkTestimonials,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact,
  // Extras que propone el motor generativo.
  video: BlkVideo,
  timeline: BlkTimeline,
  team: BlkTeam,
  aiquote: BlkAiQuote,
  aistrip: BlkAiStrip,
  aicheck: BlkAiCheck,
  aigrid: BlkAiGrid,
  aiband: BlkAiBand,
  aiprocess: BlkAiProcess,
  aipricing: BlkAiPricing,
  aimosaic: BlkAiMosaic,
  steps: BlkAiProcess
}

function withDefaults(block) {
  if (block.id === 'announcements') return { ...block, variant: block.variant || 'static' }
  if (block.id === 'featured') return { ...block, variant: block.variant || 'grid', props: { title: 'Destacados', ...(block.props || {}) } }
  if (block.id === 'gallery') return { ...block, variant: block.variant || 'grid', props: { title: 'Galería', ...(block.props || {}) } }
  if (block.id === 'hero') return { ...block, variant: block.variant || 'split' }
  if (block.id === 'contact') return { ...block, variant: block.variant || 'card', props: { title: 'Contacto', ...(block.props || {}) } }
  return block
}

const items = computed(() => templateBlocks(pageTemplate.value, 'landing')
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map(withDefaults))
</script>

<template>
  <div ref="pageEl" class="sp-page-root mc-home">
    <component
      :is="MAP[b.id]" v-for="b in items" :key="b.id"
      :block="b" :data-blk="b.id"
    />
  </div>
</template>
