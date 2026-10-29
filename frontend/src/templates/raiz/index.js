import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'raiz' — generalista / retail / servicios (nivel base).
// Superficies: las vistas propias de la carpeta views/store/raiz/.
export default {
  usesSectionOrder: true,
  fonts: ['manrope', 'bricolage-grotesque'],
  surfaces: {
    landing: landingViews.raiz,
    catalog: catalogViews.raiz,
    product: productViews.raiz,
    services: servicesViews.raiz
  },
  blocks: {
    landing: ['announcements', 'hero', 'highlights', 'categories', 'featured', 'about', 'stats', 'services', 'benefits', 'offers', 'countdown', 'brands', 'gallery', 'testimonials', 'faq', 'cta', 'contact'],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
