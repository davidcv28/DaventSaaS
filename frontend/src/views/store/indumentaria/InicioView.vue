<script setup>
// Inicio del diseño INDUMENTARIA (lookbook / runway, nivel plus) —
// composición generativa: monta los bloques del layout efectivo en su
// orden canónico. Piezas propias: IndHero (rail COLECCIÓN/01 + etiqueta +
// cinta marquee), IndCategories (páginas de lookbook) e IndAbout (ficha
// como etiqueta de ropa); el resto son los Blk* compartidos re-skineados
// por store-indumentaria.css (tokens --in-* + puente --sp-*).
import { computed, inject } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { landingExtras } from '../../../templates/_shared.js'
import IndHero from '../../../components/store/blocks/indumentaria/IndHero.vue'
import IndCategories from '../../../components/store/blocks/indumentaria/IndCategories.vue'
import IndAbout from '../../../components/store/blocks/indumentaria/IndAbout.vue'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkFeatured from '../../../components/store/blocks/BlkFeatured.vue'
import BlkStats from '../../../components/store/blocks/BlkStats.vue'
import BlkServices from '../../../components/store/blocks/BlkServices.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkOffers from '../../../components/store/blocks/BlkOffers.vue'
import BlkPlans from '../../../components/store/blocks/BlkPlans.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: IndHero,
  highlights: BlkHighlights,
  categories: IndCategories,
  featured: BlkFeatured,
  about: IndAbout,
  stats: BlkStats,
  services: BlkServices,
  benefits: BlkBenefits,
  countdown: BlkCountdown,
  offers: BlkOffers,
  plans: BlkPlans,
  brands: BlkBrands,
  gallery: BlkGallery,
  testimonials: BlkTestimonials,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact
}

const { pageTemplate, custom } = inject('storePage')
const visible = computed(() => templateBlocks(pageTemplate.value, 'landing', custom.value?.layout_config)
  .filter((b) => b.enabled !== false && MAP[b.id]))
</script>

<template>
  <main class="sp-page-root in-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </main>
</template>
