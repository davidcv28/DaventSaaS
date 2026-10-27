import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'promo' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["archivo-black","jetbrains-mono"],
  surfaces: {
    landing: landingViews.ofertas,
    catalog: catalogViews.ofertas,
    product: productViews.ofertas
  },
  blocks: {
    landing: ['hero', 'offers', 'categories', 'steps', 'testimonials', 'cta'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
