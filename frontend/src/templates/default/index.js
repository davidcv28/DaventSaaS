import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

// Template Definition 'default' — generalista neutro (nivel base).
// Port a Vue del boceto "default": una sola plantilla para todos los planes
// que cubre las 4 páginas (portada, catálogo, servicios y la genérica de
// suscripciones) con los bloques universales — sin piezas firma, la
// identidad la dan los temas: `default` (claro, índigo, Inter) y
// `default-premium` (dark, dorado, Fraunces) desde los tokens del estilo.
// Catálogo / ficha / servicios reusan las vistas de Raíz bajo `.df-skin`.
export default {
  usesSectionOrder: false,
  fonts: ['inter', 'fraunces'],
  surfaces: {
    landing: landingViews.default,
    catalog: catalogViews.default,
    product: productViews.default,
    services: servicesViews.default
  },
  blocks: {
    landing: [
      { id: 'hero', variant: 'centered' },
      'highlights',
      { id: 'categories', variant: 'rail' },
      { id: 'featured', variant: 'grid' },
      'about',
      { id: 'stats', variant: 'cards' },
      { id: 'testimonials', variant: 'cards' },
      { id: 'faq', variant: 'accordion' },
      { id: 'cta', variant: 'band' },
      { id: 'contact', variant: 'card' }
    ],
    catalog: [...new Set(['note', 'promo', ...CATALOG_BLOCKS])],
    services: SERVICES_BLOCKS
  }
}
