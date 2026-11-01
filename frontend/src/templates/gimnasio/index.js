import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'gimnasio' — deporte / fitness (nivel plus).
// Oscuro y energético: tinta carbón, acento lima, Barlow Condensed en
// titulares y JetBrains Mono en etiquetas. Composición GENERATIVA:
// `blocks.landing` es la whitelist del Studio y el orden canónico por
// defecto. Catálogo / ficha / servicios reutilizan Raíz bajo `.gy-skin`.
export default {
  usesSectionOrder: false,
  fonts: ['barlow', 'barlow-condensed', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.gimnasio,
    catalog: catalogViews.gimnasio,
    product: productViews.gimnasio,
    services: servicesViews.gimnasio
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'categories', 'featured', 'services',
      'benefits', 'stats', 'gallery', 'testimonials', 'faq', 'cta', 'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
