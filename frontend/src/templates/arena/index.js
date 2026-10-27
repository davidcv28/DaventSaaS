import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'arena' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["orbitron","space-grotesk"],
  surfaces: {
    landing: landingViews.gamer,
    catalog: catalogViews.gamer,
    product: productViews.gamer
  },
  blocks: {
    landing: ['hero', 'offers', 'featured', 'categories', 'brands', 'steps', 'faq', 'testimonials', 'cta'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
