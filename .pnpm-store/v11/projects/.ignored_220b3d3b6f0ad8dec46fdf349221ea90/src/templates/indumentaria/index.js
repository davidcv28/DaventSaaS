import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'indumentaria' — indumentaria / moda profesional
// (nivel plus). Comparte la PIEL con 'trama' (ambas declaran
// STORE_TEMPLATE_SKIN = 'indumentaria': store-trama.css y
// store-trama-catalog.css se scopan por data-skin, no por data-template),
// pero la COMPOSICIÓN es propia para que sea una opción real del selector:
// incluye la banda de ofertas y no trae la tira de marcas.
// Composición GENERATIVA: `blocks.landing` es el orden canónico por defecto Y
// la whitelist del Studio; el Inicio lo monta con useLayout y cada pieza se
// auto-oculta sin datos. Las piezas firma (hero, categorías, vitrina,
// editorial, garantías) las reusa de views/store/trama/.
// Catálogo y ficha apuntan a las vistas de trama (mismos archivos .vue).
// Tipografía: Inter Tight (display) + Inter (cuerpo), servidas on-demand.
export default {
  usesSectionOrder: false,
  fonts: ['inter', 'inter-tight'],
  surfaces: {
    landing: landingViews.indumentaria,
    catalog: catalogViews.indumentaria,
    product: productViews.indumentaria,
    services: servicesViews.indumentaria
  },
  blocks: {
    landing: [
      { id: 'announcements', variant: 'static' },
      'hero',
      'benefits',
      'categories',
      'featured',
      'about',
      { id: 'countdown', variant: 'band' },
      { id: 'offers', variant: 'grid' },
      'services',
      { id: 'testimonials', variant: 'cards' },
      { id: 'gallery', variant: 'grid' },
      'faq',
      { id: 'cta', variant: 'band' },
      { id: 'contact', variant: 'card' }
    ],
    // `note` y `promo` ya vienen dentro de CATALOG_BLOCKS; el Set evita filas
    // duplicadas (mismo criterio que trama).
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
