import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'atelier' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["archivo","oswald"],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.atelier,
    product: productViews.atelier
  },
  blocks: {
    landing: ['hero', 'highlights', 'featured', 'announcements', 'services', 'stats', 'benefits', 'offers', 'brands', 'countdown', 'gallery', 'about', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
