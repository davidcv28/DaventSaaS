import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'circuito' — tecnología / electrónica (nivel advanced).
// STUB de la fundación: monta las vistas de Raíz hasta que se implemente el
// diseño completo en views/store/circuito/.
export default {
  usesSectionOrder: true,
  fonts: ['space-grotesk', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.circuito,
    catalog: catalogViews.circuito,
    product: productViews.circuito,
    services: servicesViews.circuito
  },
  blocks: {
    landing: ['hero', 'highlights', 'categories', 'featured', 'services', 'offers', 'testimonials', 'faq', 'contact'],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
