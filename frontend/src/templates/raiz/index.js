import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'raiz' — generalista / retail / servicios (nivel base).
// Superficies: las vistas propias de la carpeta views/store/raiz/.
// `blocks.landing` es el orden canónico por defecto Y la whitelist del Studio:
// la portada lo monta de forma generativa (useLayout('landing')), así el
// default es idéntico a la composición editorial clásica y la IA puede
// reordenar/encender/apagar secciones por cliente.
export default {
  usesSectionOrder: false,
  fonts: ['manrope', 'bricolage-grotesque'],
  surfaces: {
    landing: landingViews.raiz,
    catalog: catalogViews.raiz,
    product: productViews.raiz,
    services: servicesViews.raiz
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'highlights', 'categories', 'featured', 'about',
      'stats', 'services', 'benefits', 'countdown', 'offers', 'brands',
      'gallery', 'testimonials', 'faq', 'cta', 'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
