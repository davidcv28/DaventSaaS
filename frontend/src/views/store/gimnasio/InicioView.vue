<script setup>
// Inicio del diseño GIMNASIO (deporte / fitness, nivel plus).
// Render generativo: monta los bloques del layout efectivo de la portada en
// su orden. Piezas firma: GyHero (portada oscura con cinta opcional de disciplinas)
// y GyFeatured (productos/planes en tarjetas de pista numeradas); el resto
// son los bloques compartidos re-skineados desde store-gimnasio.css.
import { computed, ref } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { useStorePage } from '../../../composables/useStorePage.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkServices from '../../../components/store/blocks/BlkServices.vue'
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
import BlkAiQuote from '../../../components/store/blocks/BlkAiQuote.vue'
import BlkAiStrip from '../../../components/store/blocks/BlkAiStrip.vue'
import BlkAiCheck from '../../../components/store/blocks/BlkAiCheck.vue'
import BlkAiGrid from '../../../components/store/blocks/BlkAiGrid.vue'
import BlkAiBand from '../../../components/store/blocks/BlkAiBand.vue'
import BlkAiProcess from '../../../components/store/blocks/BlkAiProcess.vue'
import BlkAiPricing from '../../../components/store/blocks/BlkAiPricing.vue'
import BlkAiMosaic from '../../../components/store/blocks/BlkAiMosaic.vue'
import GyHero from './GyHero.vue'
import GyFeatured from './GyFeatured.vue'
import GyStats from './GyStats.vue'
import GyPlans from './GyPlans.vue'
import GyTeam from './GyTeam.vue'

const { pageTemplate, custom } = useStorePage()
const pageEl = ref(null)

const MAP = {
  announcements: BlkAnnouncements,
  hero: GyHero,
  categories: BlkCategories,
  featured: GyFeatured,
  about: BlkAbout,
  services: BlkServices,
  plans: GyPlans,
  stats: GyStats,
  brands: BlkBrands,
  benefits: BlkBenefits,
  countdown: BlkCountdown,
  offers: BlkOffers,
  testimonials: BlkTestimonials,
  team: GyTeam,
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
  if (block.id === 'featured') return { ...block, variant: block.variant || 'grid', props: { title: 'Planes y tienda', ...(block.props || {}) } }
  if (block.id === 'categories') return { ...block, variant: block.variant || 'row' }
  if (block.id === 'brands') return { ...block, variant: block.variant || 'logos' }
  if (block.id === 'gallery') return { ...block, variant: block.variant || 'grid', props: { title: 'El gimnasio', ...(block.props || {}) } }
  if (block.id === 'testimonials') return { ...block, variant: block.variant || 'cards' }
  if (block.id === 'team') return { ...block, variant: block.variant || 'grid', props: { title: 'El equipo', ...(block.props || {}) } }
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
  <div ref="pageEl" class="sp-page-root gy-home">
    <component
      :is="MAP[b.id]" v-for="(b, i) in items" :key="b.id"
      :block="b" :data-blk="b.id"
      :section-index="['featured', 'plans', 'stats', 'team'].includes(b.id) ? i + 1 : undefined"
    />
  </div>
</template>
