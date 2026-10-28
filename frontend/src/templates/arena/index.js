import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'arena' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["orbitron","space-grotesk"],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.gamer,
    product: productViews.gamer
  },
  blocks: {
    landing: ['hero', 'highlights', 'announcements', 'about', 'services', 'stats', 'benefits', 'offers', 'featured', 'categories', 'brands', 'countdown', 'gallery', 'timeline', 'team', 'faq', 'testimonials', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
