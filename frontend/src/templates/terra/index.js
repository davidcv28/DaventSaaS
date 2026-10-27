import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'terra' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["fraunces"],
  surfaces: {
    landing: landingViews.terra,
    catalog: catalogViews.terra,
    product: productViews.hogar
  },
  blocks: {
    landing: ['hero', 'highlights', 'announcements', 'stats', 'featured', 'about', 'services', 'testimonials', 'gallery', 'faq', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
