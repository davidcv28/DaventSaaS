import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'mercado' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["fraunces","nunito"],
  surfaces: {
    landing: landingViews.mercado,
    catalog: catalogViews.mercado,
    product: productViews.mercado
  },
  blocks: {
    landing: ['hero', 'offers', 'steps', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
