import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'moderntec' (ModernTec) — tecnología / electrónica /
// gaming (nivel plus, has_design_plus). Oscuro tecnológico con acento dual
// cyan→violeta: la portada monta el layout canónico de forma generativa
// (useLayout('landing')) con piezas propias mt-* sobre la base raíz.
// Fuentes on-demand: Outfit (display) + JetBrains Mono (chips/specs);
// Inter ya va cargada en index.html.
export default {
  usesSectionOrder: false,
  fonts: ['outfit', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.moderntec,
    catalog: catalogViews.moderntec,
    product: productViews.moderntec,
    services: servicesViews.moderntec
  },
  blocks: {
    landing: [
      'hero', 'categories', 'featured', 'benefits', 'offers', 'brands', 'about',
      'gallery', 'faq', 'cta', 'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
