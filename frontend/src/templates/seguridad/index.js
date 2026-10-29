import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'seguridad' — seguridad industrial / bomberos / EPP
// (nivel advanced). A diferencia de raiz/trama/circuito (composición fija),
// este diseño es GENERATIVO: la portada monta las secciones que devuelve
// useLayout('landing') (default de acá ∪ layout_config guardado), así el
// motor de IA puede recomponer orden/variantes por cliente.
// `blocks.landing` es a la vez whitelist del Studio y layout por defecto.
export default {
  usesSectionOrder: false,
  fonts: ['barlow', 'barlow-condensed'],
  surfaces: {
    landing: landingViews.seguridad,
    catalog: catalogViews.seguridad,
    product: productViews.seguridad,
    services: servicesViews.seguridad
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'highlights', 'categories', 'featured',
      'services', 'aigrid', 'stats', 'brands', 'gallery', 'testimonials',
      'faq', 'cta', 'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
