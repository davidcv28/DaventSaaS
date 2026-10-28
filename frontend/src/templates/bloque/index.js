import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'bloque' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["archivo","jetbrains-mono"],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.bloque,
    product: productViews.classic
  },
  blocks: {
    landing: ['hero', 'highlights', 'featured', 'announcements', 'stats', 'benefits', 'offers', 'about', 'services', 'brands', 'countdown', 'testimonials', 'gallery', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
