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
// aiOnly: bloque que solo propone el motor de IA (has_ai_design); el
//   editor lo oculta sin el beneficio y el backend lo descarta.
// variants: catálogo cerrado por bloque; la primera es la default.
// variantTiers: nivel de plan que pide una variante por los datos que
//   consume ('plus' | 'advanced') — anotación del contrato; el backend
//   no la fuerza (la variante degrada sola sin datos premium).
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
    hero:         { icon: 'panel-top', label: 'Portada',              variants: { full: 'Completa', compact: 'Compacta', centered: 'Centrada', split: 'Imagen y texto', cinema: 'Video a pantalla completa', editorial: 'Editorial', search: 'Con buscador', slides: 'Carrusel de fotos', logo: 'Logo' }, variantTiers: { cinema: 'plus', slides: 'advanced' }, desc: 'El encabezado de tu web: nombre, logo, titular y botones de acceso.', edit: 'design' },
    announcements:{ icon: 'megaphone', label: 'Cinta de anuncios',    variants: { marquee: 'Marquesina', static: 'Fija' }, desc: 'Una franja con avisos que corre bajo la portada.', edit: 'company' },
    highlights:   { icon: 'tag', label: 'Etiquetas destacadas', desc: 'Etiquetas con tu WhatsApp y tus horarios, pegadas a la portada.', edit: 'design' },
    categories:   { icon: 'layout-grid', label: 'Departamentos',        variants: { row: 'En fila', rail: 'Carrusel' }, props: TITLE, desc: 'Las categorías de tu catálogo con foto y conteo de productos.', edit: 'catalogs' },
    featured:     { icon: 'package', label: 'Vitrina de productos', variants: { grid: 'Grilla', cols2: '2 columnas', cols3: '3 columnas', cols4: '4 columnas', masonry: 'Masonry', rail: 'Carrusel', lead: 'Destacado + grilla', cats: 'Por categoría', quick: 'Vista rápida' }, props: TITLE, desc: 'Los primeros productos de tu catálogo, en portada.', edit: 'catalogs' },
    about:        { icon: 'building-2', label: 'Sobre nosotros',       props: TITLE, desc: 'Tu historia: qué hacés, hace cuánto y tu misión.', edit: 'company' },
    services:     { icon: 'wrench', label: 'Qué ofrecemos',        props: TITLE, desc: 'La lista de rubros u oficios que ofrecés.', edit: 'company' },
    stats:        { icon: 'trending-up', label: 'Cifras del negocio',   variants: { band: 'Banda', cards: 'Tarjetas' }, props: TITLE, desc: 'Tus números: años, clientes, ventas — lo que quieras destacar.', edit: 'company' },
    benefits:     { icon: 'shield-check', label: 'Garantías',            variants: { cards: 'Tarjetas', bento: 'Bento' }, props: TITLE, desc: 'Los beneficios y garantías que le das al cliente.', edit: 'company' },
    offers:       { icon: 'percent', label: 'Ofertas',              variants: { grid: 'Grilla', rail: 'Carrusel', quick: 'Vista rápida' }, props: TITLE, desc: 'Los productos que tienen descuento vigente.', edit: 'catalogs' },
    brands:       { icon: 'badge-check', label: 'Marcas',               variants: { marquee: 'Marquesina', logos: 'Logos' }, props: TITLE, desc: 'Las marcas que vendés o trabajás.', edit: 'catalogs' },
    countdown:    { icon: 'timer', label: 'Cuenta regresiva',     variants: { card: 'Tarjeta', band: 'Banda' }, desc: 'Cuenta atrás hasta que venza tu promo más próxima.', edit: 'catalogs' },
    timeline:     { icon: 'history', label: 'Trayectoria',          props: TITLE, desc: 'Tu recorrido año a año o etapa a etapa.', edit: 'company' },
    team:         { icon: 'users', label: 'Equipo',               props: TITLE, desc: 'Las personas que trabajan en el negocio.', edit: 'company' },
    gallery:      { icon: 'images', label: 'Galería',              variants: { grid: 'Grilla', masonry: 'Masonry', rail: 'Carrusel' }, props: TITLE, desc: 'La grilla de fotos de tu local o de tus trabajos.', edit: 'design' },
    testimonials: { icon: 'quote', label: 'Testimonios',          variants: { cards: 'Tarjetas', carousel: 'Carrusel', masonry: 'Masonry' }, props: TITLE, desc: 'Lo que dicen tus clientes.', edit: 'company' },
    faq:          { icon: 'circle-help', label: 'Preguntas frecuentes', variants: { accordion: 'Acordeón', cols: 'Dos columnas', list: 'Lista abierta' }, props: TITLE, desc: 'Las dudas típicas de tus clientes con su respuesta.', edit: 'company' },
    video:        { icon: 'film', label: 'Video',                props: TITLE, desc: 'Un video de YouTube o Vimeo embebido en la página.', edit: 'company' },
    steps:        { icon: 'list-ordered', label: 'Cómo funciona',        props: TITLE, desc: 'Los pasos para comprar o encargar.' },
    compare:      { icon: 'columns-2', label: 'Comparativa',          desc: 'Una tabla para comparar opciones lado a lado.' },
    cta:          { icon: 'zap', label: 'Llamado a la acción',  variants: { card: 'Tarjeta', band: 'Banda' }, props: { title: 120 }, desc: 'La banda final con tu mensaje y el botón a WhatsApp.', edit: 'company' },
    // Bloques SOLO-IA (surface landing): los propone el motor "Diseñar con
    // IA" y el backend los descarta sin has_ai_design. aiOnly = el editor
    // los muestra solo con ese beneficio; el render público no los filtra
    // (sin props no pintan nada).
    aiquote:      { icon: 'quote', label: 'Frase destacada',      variants: { centered: 'Centrada', split: 'Con línea de acento' }, props: { text: 160, author: 40 }, aiOnly: true, desc: 'Una frase del negocio o de un cliente, en grande.' },
    aistrip:      { icon: 'sparkles', label: 'Banda de sellos',    variants: { band: 'Banda', cards: 'Tarjetas' }, props: { items: { icon: 32, label: 40 }, max: 4 }, aiOnly: true, desc: 'Una franja con 2 a 4 sellos: envíos, garantía, atención.' },
    aicheck:      { icon: 'check-circle', label: 'Checklist',     variants: { cards: 'Tarjetas', list: 'Lista' }, props: { title: 80, items: { text: 90 }, max: 6 }, aiOnly: true, desc: 'Una lista de puntos a favor con tilde de acento.' },
    aigrid:       { icon: 'layout-grid', label: 'Grilla de íconos', variants: { grid2: '2 columnas', grid3: '3 columnas', grid4: '4 columnas' }, props: { title: 80, items: { icon: 32, title: 40, text: 90 }, max: 6 }, aiOnly: true, desc: 'Una grilla de íconos con título y texto corto.' },
    aiband:       { icon: 'megaphone', label: 'Banda intermedia',  variants: { band: 'Banda', card: 'Tarjeta' }, props: { title: 80, text: 160, label: 40 }, aiOnly: true, desc: 'Una banda de acento con un botón, entre dos secciones.' },
    contact:      { icon: 'mail', label: 'Contacto',             variants: { card: 'Tarjeta', map: 'Mapa y horarios' }, props: TITLE, desc: 'El formulario que te llega al email, con mapa y redes.', edit: 'design' }
  },
  catalog: {
    note:    { icon: 'megaphone', label: 'Aviso del catálogo',   desc: 'Un texto fijo que se muestra encima de tu catálogo.', edit: 'company' },
    banner:  { icon: 'images', label: 'Carrusel de portada',  premium: true, desc: 'Las fotos de portada que rotan arriba del catálogo.', edit: 'catalogs' },
    promo:   { icon: 'percent', label: 'Promociones vigentes', desc: 'Una banda con tus descuentos vigentes.', edit: 'catalogs' },
    filters: { icon: 'filter', label: 'Filtros',              variants: { panel: 'Panel lateral', chips: 'Chips rápidos' }, desc: 'El panel para filtrar por categoría, marca y precio.' },
    sort:    { icon: 'arrow-down-wide-narrow', label: 'Ordenamiento',         desc: 'El selector de orden: precio, recientes, nombre.' },
    grid:    { icon: 'layout-grid', label: 'Grilla de productos',  locked: true, variants: { auto: 'Automática', cols2: '2 columnas', cols3: '3 columnas', cols4: '4 columnas', masonry: 'Masonry', list: 'Lista', lead: 'Destacado + grilla', quick: 'Vista rápida' }, desc: 'La grilla con todos tus productos. Es parte fija de la página.', edit: 'catalogs' }
  },
  services: {
    hero:   { icon: 'panel-top', label: 'Portada',               desc: 'El encabezado de la página de servicios.', edit: 'design' },
    band:   { icon: 'rows-3', label: 'Cinta de servicios',    desc: 'Una franja con los servicios que ofrecés.', edit: 'services' },
    picker: { icon: 'checklist', label: 'Selector y presupuesto', locked: true, desc: 'Donde el cliente tilda servicios y arma su presupuesto. Es parte fija de la página.', edit: 'services' },
    steps:  { icon: 'list-ordered', label: 'Cómo funciona',          desc: 'Los pasos para encargarte el trabajo.', edit: 'services' },
    form:   { icon: 'clipboard-list', label: 'Formulario de pedido',   desc: 'El formulario donde el cliente elige día y franja.', edit: 'services' },
    faq:    { icon: 'circle-help', label: 'Preguntas frecuentes',   desc: 'Las dudas típicas sobre tus servicios.', edit: 'company' }
  }
}

export function blockSpec(surface, id) {
  return TEMPLATE_BLOCKS[surface]?.[id] || null
}
