<script setup>
// Inicio del diseño INDUMENTARIA MODERNIMPACT (revista suiza de moda, nivel
// plus) — composición generativa: monta los bloques del layout efectivo en su
// orden canónico. Piezas propias: ImpHero (pliego de tapa con cabecera,
// titular Anton, ficha de datos y cinta marquee), ImpCategories (índice de
// colección numerado) e ImpAbout (dossier de la marca); el resto son los
// Blk* compartidos re-skineados por store-impacto.css (tokens --mi-*).
import { computed, inject } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { landingExtras } from '../../../templates/_shared.js'
import ImpHero from '../../../components/store/blocks/impacto/ImpHero.vue'
import ImpCategories from '../../../components/store/blocks/impacto/ImpCategories.vue'
import ImpAbout from '../../../components/store/blocks/impacto/ImpAbout.vue'
import ImpFeatured from '../../../components/store/blocks/impacto/ImpFeatured.vue'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
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
  hero: ImpHero,
  highlights: BlkHighlights,
  categories: ImpCategories,
  featured: ImpFeatured,
  about: ImpAbout,
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
  <main class="sp-page-root mi-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </main>
</template>
