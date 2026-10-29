import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'circuito' — tecnología / electrónica (nivel advanced).
// Composición FIJA de 12 secciones (spec §7.1): la vista decide el orden y
// `layout_config` se ignora (por eso usesSectionOrder: false). La lista de
// `blocks` es la whitelist del Studio y el default que leen los bloques
// compartidos (useLayout), no el orden real del render.
export default {
  usesSectionOrder: false,
  fonts: ['space-grotesk', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.circuito,
    catalog: catalogViews.circuito,
    product: productViews.circuito,
    services: servicesViews.circuito
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'highlights', 'categories', 'featured',
      'services', 'countdown', 'brands', 'testimonials', 'faq', 'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
