// Catálogo cerrado de bloques del editor de layout — espejo de
// TEMPLATE_BLOCKS (StoreApp/domains/stores/layout_blocks.py). La forma
// guardada en customization.layout_config es
//   { surface: { blocks: [{id, enabled, order, variant?, props?}] } }
// Cada plantilla declara qué bloques soporta por superficie en
// src/templates/<id>/index.js (su orden declarativo es el layout por
// defecto); el backend descarta ids/variantes/props fuera de este
// catálogo, así que ambos lados comparten los mismos nombres.
//
// premium: el bloque exige has_design_advanced (el backend lo descarta
//   del PATCH sin el beneficio; el editor lo muestra bloqueado).
// locked: bloque estructural — el editor no permite apagarlo (la grilla
//   del catálogo, el selector de servicios).
// variants: catálogo cerrado por bloque; la primera es la default.
// props: campos de texto propios del bloque (hoy 'title' = override del
//   título de la sección — se sanitiza en el backend, máx 80).

export const LAYOUT_SURFACES = ['landing', 'catalog', 'services']

export const SURFACE_LABELS = {
  landing: 'Inicio',
  catalog: 'Catálogo',
  services: 'Servicios'
}

const TITLE = { title: 80 }

export const TEMPLATE_BLOCKS = {
  landing: {
    hero:         { label: 'Portada',              variants: { full: 'Completa', compact: 'Compacta' } },
    announcements:{ label: 'Cinta de anuncios',    variants: { marquee: 'Marquesina', static: 'Fija' } },
    highlights:   { label: 'Etiquetas destacadas' },
    categories:   { label: 'Departamentos',        props: TITLE },
    featured:     { label: 'Vitrina de productos', props: TITLE },
    about:        { label: 'Sobre nosotros',       props: TITLE },
    services:     { label: 'Qué ofrecemos',        props: TITLE },
    stats:        { label: 'Cifras del negocio',   variants: { band: 'Banda', cards: 'Tarjetas' }, props: TITLE },
    benefits:     { label: 'Garantías',            props: TITLE },
    offers:       { label: 'Ofertas',              props: TITLE },
    brands:       { label: 'Marcas',               props: TITLE },
    countdown:    { label: 'Cuenta regresiva' },
    timeline:     { label: 'Trayectoria',          props: TITLE },
    team:         { label: 'Equipo',               props: TITLE },
    gallery:      { label: 'Galería',              props: TITLE },
    testimonials: { label: 'Testimonios',          props: TITLE },
    faq:          { label: 'Preguntas frecuentes', props: TITLE },
    video:        { label: 'Video',                props: TITLE },
    steps:        { label: 'Cómo funciona',        props: TITLE },
    compare:      { label: 'Comparativa' },
    cta:          { label: 'Llamado a la acción',  props: { title: 120 } },
    contact:      { label: 'Contacto',             props: TITLE }
  },
  catalog: {
    note:    { label: 'Aviso del catálogo' },
    banner:  { label: 'Carrusel de portada', premium: true },
    promo:   { label: 'Promociones vigentes' },
    filters: { label: 'Filtros' },
    sort:    { label: 'Ordenamiento' },
    grid:    { label: 'Grilla de productos', locked: true }
  },
  services: {
    hero:   { label: 'Portada' },
    band:   { label: 'Cinta de servicios' },
    picker: { label: 'Selector y presupuesto', locked: true },
    steps:  { label: 'Cómo funciona' },
    form:   { label: 'Formulario de pedido' },
    faq:    { label: 'Preguntas frecuentes' }
  }
}

export function blockSpec(surface, id) {
  return TEMPLATE_BLOCKS[surface]?.[id] || null
}
