<script setup>
// Inicio del diseño ATELIER (indumentaria editorial, nivel plus).
// Render GENERATIVO: monta los bloques del layout efectivo de la portada en
// su orden. Piezas firma del diseño: AtHero (hero con placas) y AtFeatured
// (chips de categorías + grilla de prendas); el resto de los bloques son los
// compartidos, re-skineados desde store-atelier.css.
import { computed, ref } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { useStorePage } from '../../../composables/useStorePage.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkServices from '../../../components/store/blocks/BlkServices.vue'
import BlkStats from '../../../components/store/blocks/BlkStats.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import BlkOffers from '../../../components/store/blocks/BlkOffers.vue'
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
import AtHero from './AtHero.vue'
import AtFeatured from './AtFeatured.vue'
import BqHighlights from './BqHighlights.vue'
import BqAbout from './BqAbout.vue'
import BqQuote from './BqQuote.vue'
import { useCardTitles } from './useCardTitles.js'

const { pageTemplate } = useStorePage()
const pageEl = ref(null)
useCardTitles(pageEl)

const MAP = {
  announcements: BlkAnnouncements,
  hero: AtHero,
  highlights: BqHighlights,
  featured: AtFeatured,
  about: BqAbout,
  services: BlkServices,
  stats: BlkStats,
  brands: BlkBrands,
  countdown: BlkCountdown,
  benefits: BlkBenefits,
  testimonials: BqQuote,
  gallery: BlkGallery,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact,
  // Extras que propone el motor generativo (v8).
  offers: BlkOffers,
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

// Copy de estructura y variantes firma del diseño. El layout manda: si la IA
// o el Studio ya fijaron variant/props, se respetan (el default solo completa).
function withDefaults(block) {
  if (block.id === 'announcements') return { ...block, variant: block.variant || 'static' }
  if (block.id === 'featured') return { ...block, variant: block.variant || 'grid', props: { title: 'La colección', ...(block.props || {}) } }
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
  <div ref="pageEl" class="sp-page-root bq-home at-home">
    <component
      :is="MAP[b.id]" v-for="b in items" :key="b.id"
      :block="b" :data-blk="b.id"
    />
  </div>
</template>
