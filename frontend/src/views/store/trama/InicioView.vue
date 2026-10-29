<script setup>
// Inicio del diseño TRAMA (indumentaria / moda).
// Portada GENERATIVA: monta las secciones de useLayout('landing') en el orden
// efectivo (layout canónico ∪ layout_config) respetando on/off, variante y
// props de cada bloque; el default es EXACTAMENTE la composición editorial de
// siempre (barra promo, hero partido, marquee de acento, categorías, nueva
// temporada, lookbook, beneficios, looks del mes, FAQ, banda CTA y contacto).
// Las piezas firma (Tr*) se montan con un wrapper que no les pasa `block`: su
// composición ES la firma y no tienen variantes; los ids compartidos usan los
// Blk* (que la piel de trama ya eskinaba). El chrome es el compartido,
// re-skineado desde store-trama.css. Cada sección se auto-oculta sin datos.
import { computed } from 'vue'
import { useLayout } from '../../../composables/useLayout.js'
import { firma, landingExtras } from '../../../templates/_shared.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import TrHero from './TrHero.vue'
import TrMarquee from './TrMarquee.vue'
import TrCategories from './TrCategories.vue'
import TrFeatured from './TrFeatured.vue'
import TrLookbook from './TrLookbook.vue'

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: firma(TrHero),
  highlights: firma(TrMarquee),
  categories: firma(TrCategories),
  featured: firma(TrFeatured),
  about: firma(TrLookbook),
  benefits: BlkBenefits,
  gallery: BlkGallery,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact
}

const { blocks } = useLayout('landing')
const visible = computed(() => blocks.value.filter((b) => b.enabled !== false && MAP[b.id]))
</script>

<template>
  <div class="sp-page-root tr-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" />
  </div>
</template>
