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

// desc: una línea en lenguaje llano de qué muestra el bloque (solo se usa
// en el editor; el backend no la valida — valida id/variant/props).
// edit: sección del panel donde se carga su contenido (company = Mi empresa,
// catalogs = Mis catálogos, services = Mis servicios, design = Diseño) — el
// editor muestra el enlace "lo cargás en …" que navega ahí. Sin edit = el
// bloque se arma solo (portada, grilla, filtros…).
export const TEMPLATE_BLOCKS = {
  landing: {
    hero:         { label: 'Portada',              variants: { full: 'Completa', compact: 'Compacta' }, desc: 'El encabezado de tu web: nombre, logo, titular y botones de acceso.', edit: 'design' },
    announcements:{ label: 'Cinta de anuncios',    variants: { marquee: 'Marquesina', static: 'Fija' }, desc: 'Una franja con avisos que corre bajo la portada.', edit: 'company' },
    highlights:   { label: 'Etiquetas destacadas', desc: 'Etiquetas con tu WhatsApp y tus horarios, pegadas a la portada.', edit: 'design' },
    categories:   { label: 'Departamentos',        props: TITLE, desc: 'Las categorías de tu catálogo con foto y conteo de productos.', edit: 'catalogs' },
    featured:     { label: 'Vitrina de productos', props: TITLE, desc: 'Los primeros productos de tu catálogo, en portada.', edit: 'catalogs' },
    about:        { label: 'Sobre nosotros',       props: TITLE, desc: 'Tu historia: qué hacés, hace cuánto y tu misión.', edit: 'company' },
    services:     { label: 'Qué ofrecemos',        props: TITLE, desc: 'La lista de rubros u oficios que ofrecés.', edit: 'company' },
    stats:        { label: 'Cifras del negocio',   variants: { band: 'Banda', cards: 'Tarjetas' }, props: TITLE, desc: 'Tus números: años, clientes, ventas — lo que quieras destacar.', edit: 'company' },
    benefits:     { label: 'Garantías',            props: TITLE, desc: 'Los beneficios y garantías que le das al cliente.', edit: 'company' },
    offers:       { label: 'Ofertas',              props: TITLE, desc: 'Los productos que tienen descuento vigente.', edit: 'catalogs' },
    brands:       { label: 'Marcas',               props: TITLE, desc: 'Las marcas que vendés o trabajás.', edit: 'catalogs' },
    countdown:    { label: 'Cuenta regresiva',     desc: 'Cuenta atrás hasta que venza tu promo más próxima.', edit: 'catalogs' },
    timeline:     { label: 'Trayectoria',          props: TITLE, desc: 'Tu recorrido año a año o etapa a etapa.', edit: 'company' },
    team:         { label: 'Equipo',               props: TITLE, desc: 'Las personas que trabajan en el negocio.', edit: 'company' },
    gallery:      { label: 'Galería',              props: TITLE, desc: 'La grilla de fotos de tu local o de tus trabajos.', edit: 'design' },
    testimonials: { label: 'Testimonios',          props: TITLE, desc: 'Lo que dicen tus clientes.', edit: 'company' },
    faq:          { label: 'Preguntas frecuentes', props: TITLE, desc: 'Las dudas típicas de tus clientes con su respuesta.', edit: 'company' },
    video:        { label: 'Video',                props: TITLE, desc: 'Un video de YouTube o Vimeo embebido en la página.', edit: 'company' },
    steps:        { label: 'Cómo funciona',        props: TITLE, desc: 'Los pasos para comprar o encargar.' },
    compare:      { label: 'Comparativa',          desc: 'Una tabla para comparar opciones lado a lado.' },
    cta:          { label: 'Llamado a la acción',  props: { title: 120 }, desc: 'La banda final con tu mensaje y el botón a WhatsApp.', edit: 'company' },
    contact:      { label: 'Contacto',             props: TITLE, desc: 'El formulario que te llega al email, con mapa y redes.', edit: 'design' }
  },
  catalog: {
    note:    { label: 'Aviso del catálogo',   desc: 'Un texto fijo que se muestra encima de tu catálogo.', edit: 'company' },
    banner:  { label: 'Carrusel de portada',  premium: true, desc: 'Las fotos de portada que rotan arriba del catálogo.', edit: 'catalogs' },
    promo:   { label: 'Promociones vigentes', desc: 'Una banda con tus descuentos vigentes.', edit: 'catalogs' },
    filters: { label: 'Filtros',              desc: 'El panel para filtrar por categoría, marca y precio.' },
    sort:    { label: 'Ordenamiento',         desc: 'El selector de orden: precio, recientes, nombre.' },
    grid:    { label: 'Grilla de productos',  locked: true, desc: 'La grilla con todos tus productos. Es parte fija de la página.', edit: 'catalogs' }
  },
  services: {
    hero:   { label: 'Portada',               desc: 'El encabezado de la página de servicios.', edit: 'design' },
    band:   { label: 'Cinta de servicios',    desc: 'Una franja con los servicios que ofrecés.', edit: 'services' },
    picker: { label: 'Selector y presupuesto', locked: true, desc: 'Donde el cliente tilda servicios y arma su presupuesto. Es parte fija de la página.', edit: 'services' },
    steps:  { label: 'Cómo funciona',          desc: 'Los pasos para encargarte el trabajo.', edit: 'services' },
    form:   { label: 'Formulario de pedido',   desc: 'El formulario donde el cliente elige día y franja.', edit: 'services' },
    faq:    { label: 'Preguntas frecuentes',   desc: 'Las dudas típicas sobre tus servicios.', edit: 'company' }
  }
}

export function blockSpec(surface, id) {
  return TEMPLATE_BLOCKS[surface]?.[id] || null
}
