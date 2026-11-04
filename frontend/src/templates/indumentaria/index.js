import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'indumentaria' — lookbook / runway de moda (nivel
// plus). Editorial de indumentaria: crudo tela, carbón y un acento de
// temporada, Fraunces display + Archivo + JetBrains Mono, rail COLECCIÓN,
// etiquetas colgantes, cinta marquee y grillas LOOK 01/02. Composición
// GENERATIVA: `blocks.landing` es la whitelist del Studio y el orden
// canónico por defecto. Las cuatro superficies comparten la piel de
// store-indumentaria.css (catálogo/ficha/servicios van sobre `.in-skin`).
export default {
  usesSectionOrder: false,
  fonts: ['fraunces', 'archivo', 'archivo-black', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.indumentaria,
    catalog: catalogViews.indumentaria,
    product: productViews.indumentaria,
    services: servicesViews.indumentaria
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
