<script setup>
// Inicio del diseño SEGURIDAD (seguridad industrial / bomberos / EPP).
// Portada GENERATIVA: monta las secciones que devuelve useLayout('landing')
// (default de templates/seguridad ∪ layout_config guardado) con el mapa
// id→componente de abajo. Un bloque sin componente se descarta; los bloques
// con datos se auto-ocultan solos (categorías sin productos, servicios
// apagados, stats sin números, aigrid sin ítems…). La piel vive en
// assets/store-seguridad.css con raíz [data-template="seguridad"].
import { computed } from 'vue'
import { useLayout } from '../../../composables/useLayout.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkAbout from '../../../components/store/blocks/BlkAbout.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import BlkOffers from '../../../components/store/blocks/BlkOffers.vue'
import BlkVideo from '../../../components/store/blocks/BlkVideo.vue'
import BlkTimeline from '../../../components/store/blocks/BlkTimeline.vue'
import BlkTeam from '../../../components/store/blocks/BlkTeam.vue'
import BlkAiQuote from '../../../components/store/blocks/BlkAiQuote.vue'
import BlkAiStrip from '../../../components/store/blocks/BlkAiStrip.vue'
import BlkAiCheck from '../../../components/store/blocks/BlkAiCheck.vue'
import BlkAiBand from '../../../components/store/blocks/BlkAiBand.vue'
import BlkAiProcess from '../../../components/store/blocks/BlkAiProcess.vue'
import BlkAiPricing from '../../../components/store/blocks/BlkAiPricing.vue'
import BlkAiMosaic from '../../../components/store/blocks/BlkAiMosaic.vue'
import SgHero from './SgHero.vue'
import SgCategories from './SgCategories.vue'
import SgFeatured from './SgFeatured.vue'
import SgServicesBand from './SgServicesBand.vue'
import SgFireClasses from './SgFireClasses.vue'
import SgStats from './SgStats.vue'

// Mapa id de bloque → componente del diseño (firma propia o Blk* compartido).
const MAP = {
  announcements: BlkAnnouncements,
  hero: SgHero,
  highlights: BlkHighlights,
  categories: SgCategories,
  featured: SgFeatured,
  about: BlkAbout,
  benefits: BlkBenefits,
  countdown: BlkCountdown,
  services: SgServicesBand,
  aigrid: SgFireClasses,
  stats: SgStats,
  brands: BlkBrands,
  gallery: BlkGallery,
  testimonials: BlkTestimonials,
  faq: BlkFaq,
  cta: BlkCta,
  contact: BlkContact,
  // Bloques que puede proponer el motor de IA además del layout canónico
  // (se montan solo si el layout guardado los trae; sin props se ocultan).
  offers: BlkOffers,
  video: BlkVideo,
  timeline: BlkTimeline,
  team: BlkTeam,
  aiquote: BlkAiQuote,
  aistrip: BlkAiStrip,
  aicheck: BlkAiCheck,
  aiband: BlkAiBand,
  aiprocess: BlkAiProcess,
  aipricing: BlkAiPricing,
  aimosaic: BlkAiMosaic,
  // 'steps' no tiene componente propio en el catálogo compartido: se pinta
  // con la pieza de proceso (misma forma: título + pasos con texto).
  steps: BlkAiProcess
  // 'compare' queda sin mapa a propósito: no existe componente (se descarta).
}

// Variantes firma por defecto de los bloques compartidos (solo si el layout
// guardado no eligió otra): cinta fija, categorías en fila, marcas en logos,
// testimonios en tarjetas, FAQ acordeón, CTA banda y contacto tarjeta.
const FIRMA = {
  announcements: 'static',
  categories: 'row',
  brands: 'logos',
  gallery: 'grid',
  testimonials: 'cards',
  faq: 'accordion',
  cta: 'band',
  contact: 'card'
}

const { blocks } = useLayout('landing')
const visible = computed(() => blocks.value
  .filter((b) => b.enabled !== false && MAP[b.id])
  .map((b) => (b.variant ? b : { ...b, variant: FIRMA[b.id] })))
</script>

<template>
  <main class="sp-page-root sg-home">
    <component
      v-for="b in visible" :key="b.id" :is="MAP[b.id]"
      :block="b" :data-blk="b.id"
    />
  </main>
</template>
