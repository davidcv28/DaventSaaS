<script setup>
// Inicio del diseño MODERNTEC (tecnología / electrónica / gaming) —
// generativa: monta las secciones del layout efectivo de la portada en su
// orden. Pieza firma: MtHero (chip mono + gradiente cyan→violeta + tarjeta
// device con specs); el resto son los bloques compartidos Blk* re-skineados
// por store-moderntec.css (tokens --sp-* bajo [data-template='moderntec']).
import { computed, inject } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { landingExtras } from '../../../templates/_shared.js'
import MtHero from '../../../components/store/blocks/moderntec/MtHero.vue'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkFeatured from '../../../components/store/blocks/BlkFeatured.vue'
import BlkAbout from '../../../components/store/blocks/BlkAbout.vue'
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
  hero: MtHero,
  highlights: BlkHighlights,
  categories: BlkCategories,
  featured: BlkFeatured,
  about: BlkAbout,
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
  <main class="sp-page-root mt-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </main>
</template>
