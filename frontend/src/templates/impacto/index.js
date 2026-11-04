import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'impacto' — Indumentaria ModernImpact (nivel plus).
// Revista suiza de moda: papel crudo, tinta de imprenta y un acento de
// temporada, Anton en caja alta, etiquetas JetBrains Mono, reglas de 2px,
// numeración 01/02 y cintas marquee con datos reales de la tienda.
// Composición GENERATIVA: `blocks.landing` es la whitelist del Studio y el
// orden canónico por defecto. Las cuatro superficies comparten la piel de
// store-impacto.css (catálogo/ficha/servicios van sobre `.mi-skin`).
export default {
  usesSectionOrder: false,
  fonts: ['anton', 'space-grotesk', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.impacto,
    catalog: catalogViews.impacto,
    product: productViews.impacto,
    services: servicesViews.impacto
  },
  blocks: {
    landing: [
      'hero', 'categories', 'featured', 'about', 'benefits', 'offers',
      'gallery', 'testimonials', 'faq', 'cta', 'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
