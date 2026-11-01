import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'clasico' — comercio y servicios con oficio (nivel
// plus). Identidad propia: marfil + serif (Playfair Display) + verde
// profundo, reglas finas, fotos enmarcadas y numeración editorial de
// secciones. Piel aparte (store-clasico.css / store-clasico-catalog.css),
// no comparte hoja con ningún otro diseño.
// Composición GENERATIVA: `blocks.landing` es el orden canónico por defecto Y
// la whitelist del Studio; el Inicio lo monta con useLayout y cada pieza se
// auto-oculta sin datos. Trae la tira de marcas (logos) y no la banda de
// ofertas. Catálogo, ficha y servicios tienen vistas propias.
// Tipografía: Playfair Display (display) + Inter (cuerpo), on-demand.
export default {
  usesSectionOrder: false,
  fonts: ['inter', 'playfair-display'],
  surfaces: {
    landing: landingViews.clasico,
    catalog: catalogViews.clasico,
    product: productViews.clasico,
    services: servicesViews.clasico
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
    // duplicadas (mismo criterio que trama/boutique).
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
