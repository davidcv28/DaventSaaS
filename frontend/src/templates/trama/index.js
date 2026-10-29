import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'trama' — indumentaria / moda (nivel plus).
// Portada GENERATIVA: `blocks.landing` es el orden canónico por defecto de la
// composición editorial (barra promo, hero partido, marquee de acento,
// categorías, nueva temporada, lookbook, garantías, looks del mes, FAQ, CTA y
// contacto) y a la vez la whitelist del Studio. Las variantes que no son la
// primera del catálogo se fijan acá para que el default sea EXACTAMENTE el
// render anterior (anuncios 'static', CTA 'band'); `resolveLayout` conserva
// esa firma cuando layout_config no la pisa.
export default {
  usesSectionOrder: false,
  fonts: ['archivo', 'anton'],
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
      'highlights',   // TrMarquee (banda de acento)
      'categories',
      'featured',
      'about',        // TrLookbook (lookbook editorial)
      'benefits',
      { id: 'gallery', props: { title: 'Looks del mes' } },
      'faq',
      { id: 'cta', variant: 'band' },
      'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
