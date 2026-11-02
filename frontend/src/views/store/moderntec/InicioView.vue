<script setup>
// Inicio del diseño MODERNTEC (tecnología / electrónica / gaming) —
// generativa como Raíz: monta las secciones de useLayout('landing')
// respetando enabled/variant/props. Las piezas firma son las Rh* de Raíz
// eskinadas por store-moderntec.css ([data-template='moderntec']); el hero
// se pisa con MtHero (chip mono + gradiente + tarjeta device con specs).
// Los ids extra de la IA se resuelven con los Blk* compartidos.
import { computed, inject } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { landingExtras } from '../../../templates/_shared.js'
import MtHero from '../../../components/store/blocks/moderntec/MtHero.vue'
import RhAnnouncements from '../../../components/store/blocks/raiz/RhAnnouncements.vue'
import RhGuarantees from '../../../components/store/blocks/raiz/RhGuarantees.vue'
import RhCategories from '../../../components/store/blocks/raiz/RhCategories.vue'
import RhRecent from '../../../components/store/blocks/raiz/RhRecent.vue'
import RhAbout from '../../../components/store/blocks/raiz/RhAbout.vue'
import RhStats from '../../../components/store/blocks/raiz/RhStats.vue'
import RhServices from '../../../components/store/blocks/raiz/RhServices.vue'
import RhBenefits from '../../../components/store/blocks/raiz/RhBenefits.vue'
import RhCountdown from '../../../components/store/blocks/raiz/RhCountdown.vue'
import RhOffers from '../../../components/store/blocks/raiz/RhOffers.vue'
import RhBrands from '../../../components/store/blocks/raiz/RhBrands.vue'
import RhGallery from '../../../components/store/blocks/raiz/RhGallery.vue'
import RhTestimonials from '../../../components/store/blocks/raiz/RhTestimonials.vue'
import RhFaq from '../../../components/store/blocks/raiz/RhFaq.vue'
import RhCta from '../../../components/store/blocks/raiz/RhCta.vue'
import RhContact from '../../../components/store/blocks/raiz/RhContact.vue'

const MAP = {
  ...landingExtras,
  announcements: RhAnnouncements,
  hero: MtHero,
  highlights: RhGuarantees,
  categories: RhCategories,
  featured: RhRecent,
  about: RhAbout,
  stats: RhStats,
  services: RhServices,
  benefits: RhBenefits,
  countdown: RhCountdown,
  offers: RhOffers,
  brands: RhBrands,
  gallery: RhGallery,
  testimonials: RhTestimonials,
  faq: RhFaq,
  cta: RhCta,
  contact: RhContact
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
