import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'duo' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: [],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.duo,
    product: productViews.classic
  },
  blocks: {
    landing: ['hero', 'announcements', 'stats', 'highlights', 'offers', 'about', 'services', 'testimonials', 'gallery', 'faq', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
