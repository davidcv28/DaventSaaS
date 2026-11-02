<script setup>
// Inicio del diseño DEFAULT (generalista neutro, todos los planes).
// Portada GENERATIVA 100% compartida: monta los Blk* del catálogo en el orden
// efectivo (layout canónico ∪ layout_config); el default es la composición
// del boceto "default" (hero centered, etiquetas, categorías en riel,
// destacados en grilla, sobre nosotros + cifras, testimonios, FAQ, CTA y
// contacto). Sin piezas firma: la identidad la dan los tokens del tema
// (`default` claro/índigo · `default-premium` dark/dorado/Fraunces).
// La piel vive en assets/store-default.css con raíz [data-template="default"].
import { computed, inject } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { landingExtras } from '../../../templates/_shared.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHero from '../../../components/store/blocks/BlkHero.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkFeatured from '../../../components/store/blocks/BlkFeatured.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'

const ctx = inject('storePage')

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: BlkHero,
  highlights: BlkHighlights,
  categories: BlkCategories,
  featured: BlkFeatured,
  brands: BlkBrands,
  testimonials: BlkTestimonials,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact
}

const visible = computed(() => templateBlocks(ctx.pageTemplate.value, 'landing', ctx.custom.value?.layout_config)
  .filter((b) => b.enabled !== false && MAP[b.id]))
</script>

<template>
  <div class="sp-page-root df-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </div>
</template>
