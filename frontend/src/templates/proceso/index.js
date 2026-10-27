import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'proceso' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["space-grotesk","work-sans","jetbrains-mono"],
  surfaces: {
    landing: landingViews.studio,
    catalog: catalogViews.studio,
    product: productViews.studio
  },
  blocks: {
    landing: ['hero', 'stats', 'services', 'steps', 'gallery', 'testimonials', 'faq', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
