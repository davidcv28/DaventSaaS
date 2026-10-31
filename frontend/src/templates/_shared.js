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
// 'indumentaria' comparte las vistas de catálogo/ficha/servicios con 'trama'
// (misma piel, misma lógica). El bundler cachea el mismo módulo: no duplica
// código ni CSS.
export const landingViews = {
  raiz:         () => import('../views/store/raiz/InicioView.vue'),
  alimentos:    () => import('../views/store/alimentos/InicioView.vue'),
  trama:        () => import('../views/store/trama/InicioView.vue'),
  indumentaria: () => import('../views/store/indumentaria/InicioView.vue'),
  boutique:     () => import('../views/store/boutique/InicioView.vue'),
  atelier:      () => import('../views/store/atelier/InicioView.vue'),
  sastreria:    () => import('../views/store/sastreria/InicioView.vue'),
  mercado:      () => import('../views/store/mercado/InicioView.vue'),
  clasico:      () => import('../views/store/clasico/InicioView.vue'),
  circuito:     () => import('../views/store/circuito/InicioView.vue'),
  seguridad:    () => import('../views/store/seguridad/InicioView.vue')
}

export const catalogViews = {
  raiz:         () => import('../views/store/raiz/CatalogoView.vue'),
  alimentos:    () => import('../views/store/alimentos/CatalogoView.vue'),
  trama:        () => import('../views/store/trama/CatalogoView.vue'),
  indumentaria: () => import('../views/store/trama/CatalogoView.vue'),
  boutique:     () => import('../views/store/boutique/CatalogoView.vue'),
  atelier:      () => import('../views/store/atelier/CatalogoView.vue'),
  sastreria:    () => import('../views/store/sastreria/CatalogoView.vue'),
  mercado:      () => import('../views/store/mercado/CatalogoView.vue'),
  clasico:      () => import('../views/store/clasico/CatalogoView.vue'),
  circuito:     () => import('../views/store/circuito/CatalogoView.vue'),
  seguridad:    () => import('../views/store/seguridad/CatalogoView.vue')
}

export const productViews = {
  raiz:         () => import('../views/store/raiz/ProductoView.vue'),
  alimentos:    () => import('../views/store/alimentos/ProductoView.vue'),
  trama:        () => import('../views/store/trama/ProductoView.vue'),
  indumentaria: () => import('../views/store/trama/ProductoView.vue'),
  boutique:     () => import('../views/store/boutique/ProductoView.vue'),
  atelier:      () => import('../views/store/atelier/ProductoView.vue'),
  sastreria:    () => import('../views/store/sastreria/ProductoView.vue'),
  mercado:      () => import('../views/store/mercado/ProductoView.vue'),
  clasico:      () => import('../views/store/clasico/ProductoView.vue'),
  circuito:     () => import('../views/store/circuito/ProductoView.vue'),
  seguridad:    () => import('../views/store/seguridad/ProductoView.vue')
}

export const servicesViews = {
  raiz:         () => import('../views/store/raiz/ServiciosView.vue'),
  alimentos:    () => import('../views/store/alimentos/ServiciosView.vue'),
  trama:        () => import('../views/store/trama/ServiciosView.vue'),
  indumentaria: () => import('../views/store/trama/ServiciosView.vue'),
  boutique:     () => import('../views/store/boutique/ServiciosView.vue'),
  atelier:      () => import('../views/store/atelier/ServiciosView.vue'),
  sastreria:    () => import('../views/store/sastreria/ServiciosView.vue'),
  mercado:      () => import('../views/store/mercado/ServiciosView.vue'),
  clasico:      () => import('../views/store/clasico/ServiciosView.vue'),
  circuito:     () => import('../views/store/circuito/ServiciosView.vue'),
  seguridad:    () => import('../views/store/seguridad/ServiciosView.vue')
}

// ===== Listas canónicas de bloques =====
// La lista que declara cada plantilla es a la vez su whitelist soportada y
// su layout por defecto para el Studio; la portada la recorre de forma
// generativa (useLayout) — el orden canónico de cada diseño vive en su
// templates/<id>/index.js.

// Landing: hero y contacto fijos en los extremos; entre medio van las bandas
// de portada y las secciones de marketing en su orden fijo
// (SECTION_ORDER_KEYS — ver defaultLayout en index.js).
export const SP_LANDING = [
  'hero', 'categories', 'highlights', 'featured', 'announcements',
  'about', 'services', 'stats', 'benefits', 'offers', 'brands', 'countdown',
  'gallery', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'
]

// Bloques del catálogo compartidos por todos los diseños.
export const CATALOG_BLOCKS = ['note', 'promo', 'filters', 'sort', 'grid']

// La página de servicios es una vista propia por diseño.
export const SERVICES_BLOCKS = ['hero', 'band', 'picker', 'steps', 'form', 'faq']

// ===== Bloques generativos compartidos =====
// Ids del catálogo que un diseño puede NO componer por defecto (o que la IA
// suma como extra) y que se montan con los Blk* compartidos, eskinados por
// CSS. Cada InicioView los mezcla en su mapa id→componente: los ids que el
// diseño sí trae en su layout canónico se pisan con su pieza propia.
// Carga on-demand: solo entra al bundle el bloque que el layout efectivo pide.
import { defineAsyncComponent, defineComponent, h } from 'vue'
const lazy = (load) => defineAsyncComponent(load)

export const landingExtras = {
  about:        lazy(() => import('../components/store/blocks/BlkAbout.vue')),
  services:     lazy(() => import('../components/store/blocks/BlkServices.vue')),
  stats:        lazy(() => import('../components/store/blocks/BlkStats.vue')),
  benefits:     lazy(() => import('../components/store/blocks/BlkBenefits.vue')),
  offers:       lazy(() => import('../components/store/blocks/BlkOffers.vue')),
  brands:       lazy(() => import('../components/store/blocks/BlkBrands.vue')),
  countdown:    lazy(() => import('../components/store/blocks/BlkCountdown.vue')),
  gallery:      lazy(() => import('../components/store/blocks/BlkGallery.vue')),
  testimonials: lazy(() => import('../components/store/blocks/BlkTestimonials.vue')),
  faq:          lazy(() => import('../components/store/blocks/BlkFaq.vue')),
  video:        lazy(() => import('../components/store/blocks/BlkVideo.vue')),
  timeline:     lazy(() => import('../components/store/blocks/BlkTimeline.vue')),
  team:         lazy(() => import('../components/store/blocks/BlkTeam.vue')),
  // Bloques solo-IA (has_ai_design): el motor los propone con su id propio.
  aiquote:      lazy(() => import('../components/store/blocks/BlkAiQuote.vue')),
  aistrip:      lazy(() => import('../components/store/blocks/BlkAiStrip.vue')),
  aicheck:      lazy(() => import('../components/store/blocks/BlkAiCheck.vue')),
  aigrid:       lazy(() => import('../components/store/blocks/BlkAiGrid.vue')),
  aiband:       lazy(() => import('../components/store/blocks/BlkAiBand.vue')),
  aiprocess:    lazy(() => import('../components/store/blocks/BlkAiProcess.vue')),
  aipricing:    lazy(() => import('../components/store/blocks/BlkAiPricing.vue')),
  aimosaic:     lazy(() => import('../components/store/blocks/BlkAiMosaic.vue'))
}

// Piezas firma que no declaran el prop `block` (su composición ES la
// variante por defecto): wrapper sin herencia de attrs para montarlas desde
// el mapa generativo sin ensuciar el DOM ni pedirles variantes que no tienen.
export function firma(component) {
  return defineComponent({ name: 'FirmaBlock', inheritAttrs: false, setup: () => () => h(component) })
}
