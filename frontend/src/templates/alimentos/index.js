import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'alimentos' — gastronomía / almacén / panadería
// (nivel base). Composición GENERATIVA: la lista de `blocks.landing` es a la
// vez la whitelist del Studio y el orden canónico por defecto, y el Inicio
// monta los bloques del layout efectivo (useLayout) sobre su mapa
// id -> componente (los ids sin componente se descartan).
// Tipografía: DM Serif Display para titulares y DM Sans para el cuerpo; el
// dueño sigue eligiendo su name_font, la display solo pinta los titulares.
export default {
  usesSectionOrder: false,
  fonts: ['dm-sans', 'dm-serif-display'],
  surfaces: {
    landing: landingViews.alimentos,
    catalog: catalogViews.alimentos,
    product: productViews.alimentos,
    services: servicesViews.alimentos
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'categories', 'featured', 'steps', 'countdown',
      'benefits', 'about', 'stats', 'testimonials', 'faq', 'cta', 'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
