import { landingViews, catalogViews, productViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'atelier' — superficies + bloques soportados por
// superficie (el orden declarativo de cada lista es el layout por
// defecto). Los ids pertenecen al catálogo cerrado de templates/blocks.js
// (espejo de TEMPLATE_BLOCKS del backend).
export default {
  fonts: ["archivo","oswald"],
  surfaces: {
    landing: landingViews.atelier,
    catalog: catalogViews.atelier,
    product: productViews.atelier
  },
  blocks: {
    landing: ['hero', 'featured', 'gallery', 'about', 'contact'],
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
