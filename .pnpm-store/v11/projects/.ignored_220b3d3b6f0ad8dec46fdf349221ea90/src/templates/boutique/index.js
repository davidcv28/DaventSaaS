import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'boutique' — moda premium / deco / joyería (nivel plus).
// Composición GENERATIVA: `blocks.landing` es a la vez la whitelist del Studio
// y el orden canónico por defecto. El Inicio monta los bloques del layout
// efectivo (useLayout) sobre su mapa id -> componente: un id sin componente se
// descarta y cada componente se auto-oculta sin datos.
// Tipografía: Cormorant Garamond (display, itálica en la palabra acentuada) y
// Jost (cuerpo). La display la fija la hoja del diseño; el dueño sigue
// eligiendo su name_font.
export default {
  usesSectionOrder: false,
  fonts: ['jost', 'cormorant-garamond'],
  surfaces: {
    landing: landingViews.boutique,
    catalog: catalogViews.boutique,
    product: productViews.boutique,
    services: servicesViews.boutique
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'highlights', 'categories', 'featured', 'about',
      'benefits', 'testimonials', 'gallery', 'faq', 'cta', 'contact'
    ],
    // `note` y `promo` ya vienen dentro de CATALOG_BLOCKS; el Set evita repetir
    // ids (el Inicio los montaría dos veces con la misma key).
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
