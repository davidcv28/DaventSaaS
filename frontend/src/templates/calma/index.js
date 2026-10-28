import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'calma' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["lora","nunito"],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.belleza,
    product: productViews.belleza
  },
  blocks: {
    landing: ['hero', 'highlights', 'featured', 'announcements', 'about', 'stats', 'services', 'benefits', 'brands', 'countdown', 'gallery', 'offers', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
