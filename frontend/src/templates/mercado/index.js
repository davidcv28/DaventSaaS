import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'mercado' — marketplace (nivel plus).
// Port a Vue del lenguaje del comercio masivo: masthead amarillo con buscador,
// fondo gris, tarjetas blancas densas, precios grandes y descuentos en verde.
// Composición GENERATIVA: `blocks.landing` es a la vez la whitelist del Studio
// y el orden canónico por defecto; el Inicio monta los bloques del layout
// efectivo (useLayout). Las tres superficies comparten la piel de la hoja
// store-mercado.css.
export default {
  usesSectionOrder: false,
  fonts: [],
  surfaces: {
    landing: landingViews.mercado,
    catalog: catalogViews.mercado,
    product: productViews.mercado,
    services: servicesViews.mercado
  },
  blocks: {
    landing: [
      'hero', 'categories', 'offers', 'featured', 'announcements', 'highlights',
      'brands', 'about', 'services', 'stats', 'gallery', 'testimonials', 'faq',
      'cta', 'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
