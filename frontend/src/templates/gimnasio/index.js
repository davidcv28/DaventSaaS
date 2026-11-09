import { landingViews, catalogViews, productViews, CATALOG_BLOCKS } from '../_shared.js'

// Template Definition 'gimnasio' — deporte / fitness (nivel plus).
// Oscuro y energético: negro oliva, acento lima, Barlow Condensed 800 en
// titulares e Inter en cuerpo y etiquetas. Composición GENERATIVA:
// `blocks.landing` es la whitelist del Studio y el orden canónico por
// defecto. Catálogo / ficha reutilizan Raíz bajo `.gy-skin`. El diseño no
// cubre la página Servicios: la conversión del gimnasio es la suscripción
// (bloque `plans` — membresías), no el pedido de servicios.
// `pages` limita site_templates: sin página Servicios propia, 'services'
// renderizaba una superficie vacía (surfaces.services no está declarada).
export default {
  usesSectionOrder: false,
  fonts: ['barlow-condensed', 'inter', 'jetbrains-mono'],
  pages: ['landing', 'catalog', 'plans'],
  surfaces: {
    landing: landingViews.gimnasio,
    catalog: catalogViews.gimnasio,
    product: productViews.gimnasio
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'categories', 'featured', 'plans',
      'benefits', 'stats', 'brands', 'gallery', 'testimonials', 'team', 'faq', 'cta', 'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])]
  }
}
