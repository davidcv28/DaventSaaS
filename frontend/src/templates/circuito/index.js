import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'circuito' — tecnología / electrónica (nivel advanced).
// Portada GENERATIVA: `blocks.landing` es el orden canónico por defecto
// (barra de acento, hero partido con tarjeta, franja de garantías, categorías
// 6 en 3×2, destacados, banda de servicios, oferta + cuenta regresiva, marcas,
// testimonios, FAQ y contacto) y a la vez la whitelist del Studio. Las
// variantes no-default se fijan acá para conservar el render anterior
// (anuncios 'static', contador 'band', marcas 'logos').
export default {
  usesSectionOrder: false,
  fonts: ['space-grotesk', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.circuito,
    catalog: catalogViews.circuito,
    product: productViews.circuito,
    services: servicesViews.circuito
  },
  blocks: {
    landing: [
      { id: 'announcements', variant: 'static' },
      'hero',
      'highlights',   // CiGuarantees (franja de 4 garantías)
      'categories',
      'featured',
      'services',     // CiServicesBand (banda de servicios)
      { id: 'countdown', variant: 'band' },
      { id: 'brands', variant: 'logos' },
      'testimonials',
      'faq',
      'contact'
    ],
    catalog: ['note', 'promo', ...CATALOG_BLOCKS],
    services: SERVICES_BLOCKS
  }
}
