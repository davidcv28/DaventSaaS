// Piezas compartidas de las Template Definitions: loaders de vistas por
// superficie y listas canónicas de bloques. Las rutas se resuelven
// relativas a ESTE archivo (src/templates/_shared.js), así que cada
// templates/<id>/index.js solo declara qué piezas usa.
//
// Cada loader va envuelto en defineAsyncComponent por templates/index.js
// (con cache por plantilla+superficie), manteniendo el code-splitting que
// ya tenían los dispatchers de Home/Catalog/Product.

// ===== Landings (Inicio) =====
export const landingViews = {
  sp:        () => import('../views/StorePublicView.vue'),
  duo:       () => import('../views/StorePublicAltView.vue'),
  bloque:    () => import('../views/StoreBloqueView.vue'),
  riso:      () => import('../views/StoreRisoView.vue'),
  terra:     () => import('../views/StoreTerraView.vue'),
  atelier:   () => import('../views/StoreAtelierView.vue'),
  circuit:   () => import('../views/StoreCircuitView.vue'),
  mercado:   () => import('../views/StoreMercadoView.vue'),
  studio:    () => import('../views/StoreStudioView.vue'),
  ofertas:   () => import('../views/StoreOfertasView.vue'),
  gamer:     () => import('../views/StoreGamerView.vue'),
  belleza:   () => import('../views/StoreBellezaView.vue'),
  lifestyle: () => import('../views/StoreLifestyleView.vue')
}

// ===== Catálogos =====
export const catalogViews = {
  classic:     () => import('../views/catalog/CatalogClassic.vue'),
  perspective: () => import('../views/catalog/CatalogPerspective.vue'),
  duo:         () => import('../views/catalog/CatalogDuo.vue'),
  street:      () => import('../views/catalog/CatalogStreet.vue'),
  ofertas:     () => import('../views/catalog/CatalogOfertas.vue'),
  terminal:    () => import('../views/catalog/CatalogTerminal.vue'),
  gamer:       () => import('../views/catalog/CatalogGamer.vue'),
  lookbook:    () => import('../views/catalog/CatalogLookbook.vue'),
  cobre:       () => import('../views/catalog/CatalogCobre.vue'),
  minimal:     () => import('../views/catalog/CatalogMinimal.vue'),
  boutique:    () => import('../views/catalog/CatalogBoutique.vue'),
  belleza:     () => import('../views/catalog/CatalogBelleza.vue'),
  signature:   () => import('../views/catalog/CatalogSignature.vue'),
  lifestyle:   () => import('../views/catalog/CatalogLifestyle.vue'),
  aurora:      () => import('../views/catalog/CatalogAurora.vue'),
  bloque:      () => import('../views/catalog/CatalogBloque.vue'),
  riso:        () => import('../views/catalog/CatalogRiso.vue'),
  terra:       () => import('../views/catalog/CatalogTerra.vue'),
  atelier:     () => import('../views/catalog/CatalogAtelier.vue'),
  circuit:     () => import('../views/catalog/CatalogCircuit.vue'),
  mercado:     () => import('../views/catalog/CatalogMercado.vue'),
  carta:       () => import('../views/catalog/CatalogCarta.vue'),
  studio:      () => import('../views/catalog/CatalogStudio.vue')
}

// ===== Fichas de producto =====
export const productViews = {
  classic:   () => import('../views/product/ProductClassic.vue'),
  atelier:   () => import('../views/product/ProductAtelier.vue'),
  circuit:   () => import('../views/product/ProductCircuit.vue'),
  mercado:   () => import('../views/product/ProductMercado.vue'),
  studio:    () => import('../views/product/ProductStudio.vue'),
  ofertas:   () => import('../views/product/ProductOfertas.vue'),
  gamer:     () => import('../views/product/ProductGamer.vue'),
  belleza:   () => import('../views/product/ProductBelleza.vue'),
  hogar:     () => import('../views/product/ProductHogar.vue'),
  lifestyle: () => import('../views/product/ProductLifestyle.vue')
}

// ===== Listas canónicas de bloques =====
// La lista que declara cada plantilla es a la vez su whitelist soportada
// y su layout por defecto (el orden declarativo). Los ids pertenecen al
// catálogo cerrado de templates/blocks.js (espejo del backend).

// Landing de las vistas servidas por StorePublicView: hero y contacto
// fijos en los extremos; entre medio van las bandas de portada y las
// secciones de marketing en su orden fijo (SECTION_ORDER_KEYS — ver
// defaultLayout en index.js).
export const SP_LANDING = [
  'hero', 'categories', 'highlights', 'featured', 'announcements',
  'about', 'services', 'stats', 'benefits', 'offers', 'brands', 'countdown',
  'gallery', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta', 'contact'
]
// Sin departamentos ni vitrina (classic/perspective no los renderizan).
export const SP_LANDING_BASE = SP_LANDING.filter((id) => id !== 'categories' && id !== 'featured')
// Solo vitrina (cobre/minimal no tienen departamentos).
export const SP_LANDING_FEATURED = SP_LANDING.filter((id) => id !== 'categories')

// Bloques del catálogo compartidos por todas las plantillas (el carrusel
// 'banner' solo lo monta CatalogClassic — lo declara solo esa plantilla).
export const CATALOG_BLOCKS = ['note', 'promo', 'filters', 'sort', 'grid']

// La página de servicios es una sola vista para todas las plantillas.
export const SERVICES_BLOCKS = ['hero', 'band', 'picker', 'steps', 'form', 'faq']
