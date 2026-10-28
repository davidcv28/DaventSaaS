import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'studio' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["manrope","work-sans"],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.studio,
    product: productViews.studio
  },
  blocks: {
    landing: ['hero', 'highlights', 'featured', 'announcements', 'about', 'stats', 'services', 'benefits', 'offers', 'brands', 'countdown', 'timeline', 'gallery', 'testimonials', 'team', 'faq', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
