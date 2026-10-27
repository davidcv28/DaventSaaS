// Componentes de bloque de la superficie `landing` de la familia
// StorePublicView (classic, perspective, promo, street, terminal,
// lookbook, cobre, minimal, boutique, signature, aurora y shop). El mapa
// id -> componente async lo consume BlockRenderer: los ids son los del
// catálogo cerrado (templates/blocks.js) y cada bloque recibe :block con
// {id, enabled, order, variant?, props?} para aplicar su variante y el
// override de título (props.title).
//
// Los ids sin componente aquí (p.ej. 'steps', 'compare') no se montan aunque
// la plantilla los declare — el renderer los filtra solo.
import { defineAsyncComponent } from 'vue'

export const SP_LANDING_BLOCKS = {
  hero:          defineAsyncComponent(() => import('./BlkHero.vue')),
  categories:    defineAsyncComponent(() => import('./BlkCategories.vue')),
  highlights:    defineAsyncComponent(() => import('./BlkHighlights.vue')),
  featured:      defineAsyncComponent(() => import('./BlkFeatured.vue')),
  announcements: defineAsyncComponent(() => import('./BlkAnnouncements.vue')),
  about:         defineAsyncComponent(() => import('./BlkAbout.vue')),
  services:      defineAsyncComponent(() => import('./BlkServices.vue')),
  stats:         defineAsyncComponent(() => import('./BlkStats.vue')),
  benefits:      defineAsyncComponent(() => import('./BlkBenefits.vue')),
  offers:        defineAsyncComponent(() => import('./BlkOffers.vue')),
  brands:        defineAsyncComponent(() => import('./BlkBrands.vue')),
  countdown:     defineAsyncComponent(() => import('./BlkCountdown.vue')),
  gallery:       defineAsyncComponent(() => import('./BlkGallery.vue')),
  testimonials:  defineAsyncComponent(() => import('./BlkTestimonials.vue')),
  timeline:      defineAsyncComponent(() => import('./BlkTimeline.vue')),
  team:          defineAsyncComponent(() => import('./BlkTeam.vue')),
  faq:           defineAsyncComponent(() => import('./BlkFaq.vue')),
  video:         defineAsyncComponent(() => import('./BlkVideo.vue')),
  cta:           defineAsyncComponent(() => import('./BlkCta.vue')),
  contact:       defineAsyncComponent(() => import('./BlkContact.vue'))
}
