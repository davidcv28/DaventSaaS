<script setup>
// Inicio del diseño NEXO (tecnología premium).
// Portada GENERATIVA: monta las secciones de useLayout('landing') en el orden
// efectivo (layout canónico ∪ layout_config) respetando on/off, variante y
// props de cada bloque; el default es la composición del boceto (cinta de
// anuncios, hero cinema, etiquetas, categorías, vitrina, cifras, garantías
// bento, servicios, oferta + cuenta regresiva, marcas, galería, testimonios,
// FAQ, CTA y contacto). La pieza firma (NxHero) se monta con wrapper sin
// `block`; el resto sale de los Blk* compartidos, eskinados por CSS.
// La piel vive en assets/store-nexo2.css con raíz [data-template="nexo2"].
import { computed, inject } from 'vue'
import { templateBlocks } from '../../../templates/index.js'
import { firma, landingExtras } from '../../../templates/_shared.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkFeatured from '../../../components/store/blocks/BlkFeatured.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import NxHero from './NxHero.vue'

const ctx = inject('storePage')

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: firma(NxHero),
  categories: BlkCategories,
  featured: BlkFeatured,
  brands: BlkBrands,
  testimonials: BlkTestimonials,
  faq: BlkFaq,
  contact: BlkContact
}

const visible = computed(() => templateBlocks(ctx.pageTemplate.value, 'landing', ctx.custom.value?.layout_config)
  .filter((b) => b.enabled !== false && MAP[b.id]))
</script>

<template>
  <div class="sp-page-root nx-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </div>
</template>
