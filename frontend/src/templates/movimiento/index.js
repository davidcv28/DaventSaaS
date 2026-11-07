import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'movimiento' — estudio de entrenamiento (nivel
// advanced / Plan Premium). Editorial LUMINOSO (contraste directo con la
// sala oscura de `gimnasio`): papel hueso, tinta casi negra y UN acento
// señal; Bricolage Grotesque en titulares condensados, Instrument Sans en
// cuerpo y JetBrains Mono en índices/datos. Composición partida con
// numeración editorial 01/02/03 como columna vertebral, manifiesto
// "no es un gym más", servicios como lista numerada y membresías en
// tarjetas de precio. Catálogo / ficha / servicios reusan Raíz bajo
// `.mv-skin`, re-eskinados por store-movimiento.css.
export default {
  usesSectionOrder: false,
  fonts: ['bricolage-grotesque', 'instrument-sans', 'jetbrains-mono'],
  surfaces: {
    landing: landingViews.movimiento,
    catalog: catalogViews.movimiento,
    product: productViews.movimiento,
    services: servicesViews.movimiento
  },
  blocks: {
    landing: [
      'announcements', 'hero', 'categories', 'featured', 'about', 'services',
      'timeline', 'plans', 'benefits', 'stats', 'brands', 'gallery', 'testimonials',
      'team', 'faq', 'cta', 'contact'
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
