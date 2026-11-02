import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'moderntec' (ModernTec) — tecnología / electrónica /
// gaming (nivel plus, has_design_plus). Oscuro tecnológico con acento dual
// cyan→violeta: la portada monta el layout canónico de forma generativa
// (useLayout('landing')) con piezas propias mt-* sobre la base raíz.
// Fuentes on-demand: Space Grotesk (display) + JetBrains Mono (chips/specs);
// Inter ya va cargada en index.html.
export default {
  usesSectionOrder: false,
  fonts: ['space-grotesk', 'sora', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.moderntec,
    catalog: catalogViews.moderntec,
    product: productViews.moderntec,
    services: servicesViews.moderntec
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'highlights', 'categories', 'featured', 'about',
      'stats', 'services', 'benefits', 'countdown', 'offers', 'plans', 'brands',
      'gallery', 'testimonials', 'faq', 'cta', 'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
