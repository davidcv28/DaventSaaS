import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'signature' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["cinzel","dancing-script"],
  surfaces: {
    landing: landingViews.belleza,
    catalog: catalogViews.signature,
    product: productViews.belleza
  },
  blocks: {
    landing: ['hero', 'stats', 'services', 'gallery', 'offers', 'contact', 'testimonials', 'cta'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
