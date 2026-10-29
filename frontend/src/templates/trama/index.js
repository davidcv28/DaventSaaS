import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'trama' — indumentaria / moda (nivel plus).
// Composición FIJA de 12 secciones (spec §7.1): la vista decide el orden y
// `layout_config` se ignora (por eso usesSectionOrder: false). La lista de
// `blocks` es la whitelist del Studio y el default que leen los bloques
// compartidos (useLayout), no el orden real del render.
export default {
  usesSectionOrder: false,
  fonts: ['archivo', 'anton'],
  surfaces: {
    landing: landingViews.trama,
    catalog: catalogViews.trama,
    product: productViews.trama,
    services: servicesViews.trama
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'categories', 'featured', 'about',
      'benefits', 'gallery', 'faq', 'cta', 'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
