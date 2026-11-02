import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'nexo' — tecnología premium (nivel advanced).
// Port a Vue del boceto "tecnología premium" (boceto/tecnologia-premium):
// tinta casi negra, retícula técnica, acento del tema (teal o ámbar), Space
// Grotesk + JetBrains Mono, hero cinema con tarjeta de producto flotante.
// Composición GENERATIVA: `blocks.landing` es a la vez la whitelist del
// Studio y el orden canónico por defecto; el Inicio monta los bloques del
// layout efectivo (useLayout). Catálogo / ficha / servicios reusan las
// vistas de Raíz bajo `.nx-skin` (puente de tokens en store-nexo.css).
export default {
  usesSectionOrder: false,
  fonts: ['space-grotesk', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.nexo,
    catalog: catalogViews.nexo,
    product: productViews.nexo,
    services: servicesViews.nexo
  },
  blocks: {
    landing: [
      { id: 'announcements', variant: 'marquee' },
      'hero',
      'highlights',
      { id: 'categories', variant: 'rail' },
      { id: 'featured', variant: 'cols4' },
      { id: 'stats', variant: 'band' },
      { id: 'benefits', variant: 'bento' },
      'services',
      { id: 'offers', variant: 'rail' },
      { id: 'countdown', variant: 'card' },
      { id: 'brands', variant: 'marquee' },
      { id: 'gallery', variant: 'grid' },
      { id: 'testimonials', variant: 'cards' },
      { id: 'faq', variant: 'accordion' },
      { id: 'cta', variant: 'band' },
      'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
