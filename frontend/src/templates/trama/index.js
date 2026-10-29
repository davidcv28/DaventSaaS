import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'trama' — indumentaria / moda (nivel plus).
// STUB de la fundación: monta las vistas de Raíz hasta que se implemente el
// diseño completo en views/store/trama/ (el registro ya apunta a esa carpeta,
// así el reemplazo es archivo por archivo).
export default {
  usesSectionOrder: true,
  fonts: ['archivo', 'anton'],
  surfaces: {
    landing: landingViews.trama,
    catalog: catalogViews.trama,
    product: productViews.trama,
    services: servicesViews.trama
  },
  blocks: {
    landing: ['hero', 'announcements', 'categories', 'featured', 'about', 'benefits', 'gallery', 'testimonials', 'faq', 'cta', 'contact'],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
