import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'trama' — indumentaria / moda profesional (nivel plus).
// Composición GENERATIVA: `blocks.landing` es el orden canónico por defecto Y
// la whitelist del Studio; el Inicio lo monta con useLayout y cada pieza se
// auto-oculta sin datos. La firma del diseño es la del SPEC «Indumentaria ·
// Profesional»: utility bar, hero partido, franja de garantías, categorías con
// línea de prenda, Recién llegado con tabs, editorial + cifras, banda de
// cuenta regresiva, Por qué elegirnos, marcas, opiniones, galería, FAQ, banda
// CTA y contacto. `highlights` queda fuera del default pero el MAP del
// InicioView lo sigue soportando (config guardada o IA pueden pedirlo).
// Tipografía: Inter Tight (display) + Inter (cuerpo), servidas on-demand.
export default {
  usesSectionOrder: false,
  fonts: ['inter', 'inter-tight'],
  surfaces: {
    landing: landingViews.trama,
    catalog: catalogViews.trama,
    product: productViews.trama,
    services: servicesViews.trama
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
      'services',
      { id: 'brands', variant: 'logos' },
      { id: 'testimonials', variant: 'cards' },
      { id: 'gallery', variant: 'grid' },
      'faq',
      { id: 'cta', variant: 'band' },
      { id: 'contact', variant: 'card' }
    ],
    // `note` y `promo` ya vienen dentro de CATALOG_BLOCKS; el Set evita filas
    // duplicadas (antes trama repetía note/promo en el catálogo).
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
