import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'lab' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["manrope","jetbrains-mono"],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.circuit,
    product: productViews.circuit
  },
  blocks: {
    landing: ['hero', 'featured', 'benefits', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
