import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'sastreria' — indumentaria editorial (nivel plus).
// Sastrería de autor: papel hueso, tinta y cuero, Fraunces + Instrument Sans,
// índice numerado y prendas en filas de fichero. Composición GENERATIVA:
// `blocks.landing` es la whitelist del Studio y el orden canónico por defecto.
// Las tres superficies comparten la piel de store-sastreria.css.
export default {
  usesSectionOrder: false,
  fonts: ['fraunces', 'instrument-sans', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.sastreria,
    catalog: catalogViews.sastreria,
    product: productViews.sastreria,
    services: servicesViews.sastreria
  },
  blocks: {
    landing: [
      'hero', 'categories', 'featured', 'about', 'benefits', 'testimonials',
      'gallery', 'faq', 'cta', 'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
