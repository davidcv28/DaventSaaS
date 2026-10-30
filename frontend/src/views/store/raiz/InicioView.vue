<script setup>
// Inicio del diseño RAÍZ (generalista / retail / servicios) — v3 GENERATIVA.
// La vista ya no fija la composición: monta las secciones que devuelve
// useLayout('landing') (layout canónico de la plantilla ∪ layout_config
// guardado) en el orden efectivo, respetando on/off, variante y props de cada
// bloque. El layout por defecto es EXACTAMENTE la composición editorial
// anterior, así una tienda sin config se ve idéntica: cada sección es un
// componente Rh* que se auto-oculta sin datos (una tienda vacía no deja
// huecos) y la numeración (01, 02…) la resuelve el CSS con un contador.
// Los ids extra que la IA puede sumar (video, trayectoria, equipo y los
// aiOnly) se montan con los Blk* compartidos; un id sin componente se
// descarta (el diseño no lo soporta).
// La piel del chrome/tokens vive en assets/store-raiz.css; la portada en
// assets/store-raiz-home.css.
import { computed } from 'vue'
import { useLayout } from '../../../composables/useLayout.js'
import { landingExtras } from '../../../templates/_shared.js'
import RhAnnouncements from '../../../components/store/blocks/raiz/RhAnnouncements.vue'
import RhHero from '../../../components/store/blocks/raiz/RhHero.vue'
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

// mapa id de bloque -> componente. Las piezas firma Rh* pisan a los Blk*
// compartidos del mismo id; los ids que raíz no compone por defecto quedan
// disponibles para la IA/el Studio vía landingExtras.
const MAP = {
  ...landingExtras,
  announcements: RhAnnouncements,
  hero: RhHero,
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

const { blocks } = useLayout('landing')
const visible = computed(() => blocks.value.filter((b) => b.enabled !== false && MAP[b.id]))
</script>

<template>
  <main class="sp-page-root rz-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </main>
</template>
