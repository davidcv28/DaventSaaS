<script setup>
// Inicio del diseño SASTRERÍA (indumentaria editorial, nivel plus).
// Render generativo: monta los bloques del layout efectivo de la portada en
// su orden. Piezas firma: SastreriaHero (portada asimétrica) y
// SastreriaFeatured (prendas en filas de fichero); el resto son los bloques
// compartidos re-skineados desde store-sastreria.css.
import { computed, ref } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { useStorePage } from '../../../composables/useStorePage.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkServices from '../../../components/store/blocks/BlkServices.vue'
import BlkStats from '../../../components/store/blocks/BlkStats.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import BlkOffers from '../../../components/store/blocks/BlkOffers.vue'
import BlkAbout from '../../../components/store/blocks/BlkAbout.vue'
import SastreriaHero from './SastreriaHero.vue'
import SastreriaFeatured from './SastreriaFeatured.vue'

const { pageTemplate } = useStorePage()
const pageEl = ref(null)

const MAP = {
  announcements: BlkAnnouncements,
  hero: SastreriaHero,
  categories: BlkCategories,
  featured: SastreriaFeatured,
  about: BlkAbout,
  services: BlkServices,
  stats: BlkStats,
  brands: BlkBrands,
  benefits: BlkBenefits,
  offers: BlkOffers,
  testimonials: BlkTestimonials,
  gallery: BlkGallery,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact
}

function withDefaults(block) {
  if (block.id === 'featured') return { ...block, variant: block.variant || 'lead', props: { title: 'La colección', ...(block.props || {}) } }
  if (block.id === 'gallery') return { ...block, variant: block.variant || 'grid', props: { title: 'Galería', ...(block.props || {}) } }
  if (block.id === 'hero') return { ...block, variant: block.variant || 'editorial' }
  if (block.id === 'contact') return { ...block, variant: block.variant || 'card', props: { title: 'Contacto', ...(block.props || {}) } }
  return block
}

const items = computed(() => templateBlocks(pageTemplate.value, 'landing')
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map(withDefaults))
</script>

<template>
  <div ref="pageEl" class="sp-page-root ss-home">
    <component
      :is="MAP[b.id]" v-for="b in items" :key="b.id"
      :block="b" :data-blk="b.id"
    />
  </div>
</template>
