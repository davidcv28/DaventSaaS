import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'boutique' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  usesSectionOrder: true,
  fonts: ["playfair-display","raleway"],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.boutique,
    product: productViews.classic
  },
  blocks: {
    landing: ['hero', 'categories', 'highlights', 'featured', 'announcements', 'about', 'services', 'stats', 'benefits', 'offers', 'brands', 'countdown', 'gallery', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
