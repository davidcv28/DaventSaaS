import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'classic' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  usesSectionOrder: true,
  fonts: [],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.classic,
    product: productViews.classic
  },
  blocks: {
    landing: ['hero', 'highlights', 'announcements', 'about', 'services', 'stats', 'benefits', 'offers', 'brands', 'countdown', 'gallery', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'],
    catalog: ['note', 'banner', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
