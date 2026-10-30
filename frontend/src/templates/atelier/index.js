import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'atelier' — indumentaria editorial (nivel plus).
// Port a Vue del diseño Atelier Otoño: papel cálido, verde bosque, Bricolage
// Grotesque + Hanken Grotesk, hero con placas y vitrina con chips.
// Composición GENERATIVA: `blocks.landing` es a la vez la whitelist del Studio
// y el orden canónico por defecto; el Inicio monta los bloques del layout
// efectivo (useLayout). Las tres superficies comparten la piel de la hoja
// store-atelier.css.
export default {
  usesSectionOrder: false,
  fonts: ['hanken-grotesk', 'bricolage-grotesque'],
  surfaces: {
    landing: landingViews.atelier,
    catalog: catalogViews.atelier,
    product: productViews.atelier,
    services: servicesViews.atelier
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'featured', 'highlights', 'about', 'services',
      'benefits', 'testimonials', 'gallery', 'faq', 'cta', 'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
