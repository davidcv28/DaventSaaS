import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'lookbook' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["fraunces","work-sans"],
  surfaces: {
    landing: landingViews.lifestyle,
    catalog: catalogViews.lookbook,
    product: productViews.lifestyle
  },
  blocks: {
    landing: ['hero', 'offers', 'testimonials', 'cta'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
