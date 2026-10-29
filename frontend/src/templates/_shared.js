// Piezas compartidas de las Template Definitions: loaders de vistas por
// superficie y listas canónicas de bloques. Las rutas se resuelven relativas
// a ESTE archivo (src/templates/_shared.js), así que cada
// templates/<id>/index.js solo declara qué piezas usa.
//
// Cada loader va envuelto en defineAsyncComponent por templates/index.js
// (con cache por plantilla+superficie), manteniendo el code-splitting de la
// web pública.

// ===== Superficies por diseño =====
// Inicio, Catálogo, Ficha de producto y Servicios viven en la carpeta del
// diseño (views/store/<id>/). Un diseño nuevo solo agrega sus loaders acá.
export const landingViews = {
  raiz:      () => import('../views/store/raiz/InicioView.vue'),
  trama:     () => import('../views/store/trama/InicioView.vue'),
  circuito:  () => import('../views/store/circuito/InicioView.vue')
}

export const catalogViews = {
  raiz:      () => import('../views/store/raiz/CatalogoView.vue'),
  trama:     () => import('../views/store/trama/CatalogoView.vue'),
  circuito:  () => import('../views/store/circuito/CatalogoView.vue')
}

export const productViews = {
  raiz:      () => import('../views/store/raiz/ProductoView.vue'),
  trama:     () => import('../views/store/trama/ProductoView.vue'),
  circuito:  () => import('../views/store/circuito/ProductoView.vue')
}

export const servicesViews = {
  raiz:      () => import('../views/store/raiz/ServiciosView.vue'),
  trama:     () => import('../views/store/trama/ServiciosView.vue'),
  circuito:  () => import('../views/store/circuito/ServiciosView.vue')
}

// ===== Listas canónicas de bloques =====
// La lista que declara cada plantilla es a la vez su whitelist soportada y
// su layout por defecto para el Studio (el render público de los 3 diseños
// aplica el orden canónico de su vista).

// Landing: hero y contacto fijos en los extremos; entre medio van las bandas
// de portada y las secciones de marketing en su orden fijo
// (SECTION_ORDER_KEYS — ver defaultLayout en index.js).
export const SP_LANDING = [
  'hero', 'categories', 'highlights', 'featured', 'announcements',
  'about', 'services', 'stats', 'benefits', 'offers', 'brands', 'countdown',
  'gallery', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'
]

// Bloques del catálogo compartidos por los 3 diseños.
export const CATALOG_BLOCKS = ['note', 'promo', 'filters', 'sort', 'grid']

// La página de servicios es una vista propia por diseño.
export const SERVICES_BLOCKS = ['hero', 'band', 'picker', 'steps', 'form', 'faq']
