<script setup>
// Inicio del diseño MOVIMIENTO (deporte / entrenamiento, nivel advanced).
// Render generativo: monta los bloques del layout efectivo de la portada
// en su orden. Piezas firma: MvHero (portada partida editorial),
// MvFeatured (vitrina revista), MvServices (lista numerada), MvMethod
// (método en pasos 01/02/03), MvPlans (membresías) y MvTeam (fila
// editorial); el resto son bloques compartidos re-skineados desde
// store-movimiento.css.
import { computed, ref } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { useStorePage } from '../../../composables/useStorePage.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import BlkOffers from '../../../components/store/blocks/BlkOffers.vue'
import BlkAbout from '../../../components/store/blocks/BlkAbout.vue'
import BlkStats from '../../../components/store/blocks/BlkStats.vue'
import BlkAiQuote from '../../../components/store/blocks/BlkAiQuote.vue'
import BlkAiStrip from '../../../components/store/blocks/BlkAiStrip.vue'
import BlkAiCheck from '../../../components/store/blocks/BlkAiCheck.vue'
import BlkAiGrid from '../../../components/store/blocks/BlkAiGrid.vue'
import BlkAiBand from '../../../components/store/blocks/BlkAiBand.vue'
import BlkAiProcess from '../../../components/store/blocks/BlkAiProcess.vue'
import BlkAiPricing from '../../../components/store/blocks/BlkAiPricing.vue'
import BlkAiMosaic from '../../../components/store/blocks/BlkAiMosaic.vue'
import MvHero from './MvHero.vue'
import MvFeatured from './MvFeatured.vue'
import MvServices from './MvServices.vue'
import MvMethod from './MvMethod.vue'
import MvPlans from './MvPlans.vue'
import MvTeam from './MvTeam.vue'

const { pageTemplate, custom } = useStorePage()
const pageEl = ref(null)

const MAP = {
  announcements: BlkAnnouncements,
  hero: MvHero,
  categories: BlkCategories,
  featured: MvFeatured,
  about: BlkAbout,
  services: MvServices,
  timeline: MvMethod,
  plans: MvPlans,
  stats: BlkStats,
  brands: BlkBrands,
  benefits: BlkBenefits,
  countdown: BlkCountdown,
  offers: BlkOffers,
  testimonials: BlkTestimonials,
  team: MvTeam,
  gallery: BlkGallery,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact,
  // Extras que puede proponer el motor generativo.
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

// Variantes firma por defecto (solo si el layout guardado no eligió otra).
function withDefaults(block) {
  if (block.id === 'announcements') return { ...block, variant: block.variant || 'static' }
  if (block.id === 'featured') return { ...block, variant: block.variant || 'grid' }
  if (block.id === 'categories') return { ...block, variant: block.variant || 'row' }
  if (block.id === 'brands') return { ...block, variant: block.variant || 'logos' }
  if (block.id === 'gallery') return { ...block, variant: block.variant || 'grid', props: { title: 'La sala', ...(block.props || {}) } }
  if (block.id === 'testimonials') return { ...block, variant: block.variant || 'cards' }
  if (block.id === 'team') return { ...block, variant: block.variant || 'grid', props: { title: 'Los coaches', ...(block.props || {}) } }
  if (block.id === 'timeline') return { ...block, props: { title: 'El método', ...(block.props || {}) } }
  if (block.id === 'plans') return { ...block, variant: block.variant || 'cards' }
  if (block.id === 'faq') return { ...block, variant: block.variant || 'accordion' }
  if (block.id === 'cta') return { ...block, variant: block.variant || 'band' }
  if (block.id === 'contact') return { ...block, variant: block.variant || 'card', props: { title: 'Contacto', ...(block.props || {}) } }
  return block
}

const items = computed(() => templateBlocks(pageTemplate.value, 'landing', custom.value?.layout_config)
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map(withDefaults))
</script>

<template>
  <div ref="pageEl" class="sp-page-root mv-home">
    <component
      :is="MAP[b.id]" v-for="(b, i) in items" :key="b.id"
      :block="b" :data-blk="b.id"
      :section-index="['featured', 'services', 'timeline', 'plans', 'team'].includes(b.id) ? i + 1 : undefined"
    />
  </div>
</template>
