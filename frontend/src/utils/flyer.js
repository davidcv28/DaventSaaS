// Folleto a medida: el diseño (layout) lo arma DAVENT y el cliente rellena
// los textos y elige una foto de su galería (y, en los de catálogo, sus
// productos). El borrador vive en localStorage por tienda: el diseñador lo
// guarda y la vista de impresión (/folleto?custom=1) lo lee, sin tocar el backend.

export const FLYER_KINDS = [
  { id: 'empresa', label: 'Publicidad de empresa', icon: 'store', desc: 'Presentá tu negocio: quiénes son, qué hacen y por qué elegirte.' },
  { id: 'marketing', label: 'Promociones', icon: 'megaphone', desc: 'Ofertas y campañas puntuales con una foto y un llamado a la acción.' },
  { id: 'catalogo', label: 'Productos y precios', icon: 'package', desc: 'Catálogo con foto y precio: comida, almacén, kioscos, etc.' },
  { id: 'indumentaria', label: 'Indumentaria', icon: 'tag', desc: 'Colecciones y prendas para tiendas de ropa y calzado.' },
  { id: 'electro', label: 'Electrodomésticos', icon: 'monitor', desc: 'Ofertas de electro y tecnología con precio y cuotas.' }
]

export const FLYER_LAYOUTS = [
  { id: 'corporativo', kind: 'empresa', label: 'Corporativo', icon: 'store', desc: 'Limpio y profesional: nombre, foto y 4 puntos fuertes numerados.',
    ph: { title: 'Ej. Constructora Norte', subtitle: 'Ej. Más de 15 años construyendo hogares en Salta', badge: 'Ej. Desde 2009', bulletsLabel: 'Servicios o puntos fuertes', bullets: ['Ej. Obras llave en mano', 'Ej. Presupuesto sin cargo', 'Ej. Garantía por escrito', 'Ej. Atención personalizada'] } },
  { id: 'manifiesto', kind: 'empresa', label: 'Manifiesto', icon: 'megaphone', desc: 'Foto a sangre con una frase de marca enorme. Impacto e identidad.',
    ph: { title: 'Ej. Hacemos que tu casa respire', subtitle: 'Ej. Diseño, calidad y compromiso en cada detalle', badge: 'Ej. Nueva etapa', bulletsLabel: 'Etiquetas de la marca', bullets: ['Ej. Calidad', 'Ej. Confianza', 'Ej. Garantía', ''] } },
  { id: 'servicios', kind: 'empresa', label: 'Servicios', icon: 'checklist', desc: 'Fondo oscuro con tus servicios en lista numerada.',
    ph: { title: 'Ej. Todo para tu hogar', subtitle: 'Ej. Un equipo, una sola llamada', badge: 'Ej. Servicio 24 hs', bulletsLabel: 'Servicios', bullets: ['Ej. Plomería y gas', 'Ej. Electricidad', 'Ej. Pintura y reformas', 'Ej. Mantenimiento'] } },
  { id: 'anuncio', kind: 'empresa', label: 'Anuncio', icon: 'flame', desc: 'Para novedades: inauguración, nueva sucursal o aniversario.',
    ph: { title: 'Ej. Nueva sucursal en el centro', subtitle: 'Ej. Te esperamos con sorpresas y regalos', badge: 'Ej. INAUGURACIÓN', bulletsLabel: 'Detalles (fecha, dirección, horario)', bullets: ['Ej. Sábado 15 de marzo', 'Ej. Av. Belgrano 450', 'Ej. De 9 a 21 hs', ''] } },

  { id: 'impacto', kind: 'marketing', label: 'Impacto', icon: 'zap', desc: 'Foto grande arriba, titular fuerte y sello de oferta.' },
  { id: 'oferta', kind: 'marketing', label: 'Oferta', icon: 'percent', desc: 'Fondo a todo color con el descuento como protagonista.' },
  { id: 'editorial', kind: 'marketing', label: 'Editorial', icon: 'sparkles', desc: 'Elegante y sobrio, con foto en arco sobre fondo claro.' },

  { id: 'vitrina', kind: 'catalogo', label: 'Vitrina', icon: 'layout-grid', desc: 'Hasta 4 productos en cuadrícula, con foto y precio.', products: 4 },
  { id: 'lista', kind: 'catalogo', label: 'Lista de precios', icon: 'receipt', desc: 'Hasta 6 productos en lista, ideal para precios.', products: 6 },
  { id: 'destacado', kind: 'catalogo', label: 'Destacado', icon: 'star', desc: 'Un producto estrella grande y 3 más abajo.', products: 4 },

  { id: 'moda', kind: 'indumentaria', label: 'Colección', icon: 'sparkles', desc: 'Editorial de moda: 3 prendas en pliegos altos sobre fondo marfil.', products: 3,
    ph: { title: 'Ej. Otoño / Invierno', subtitle: 'Ej. Nueva colección ya en tienda', badge: 'Ej. Nuevo' } },
  { id: 'urbano', kind: 'indumentaria', label: 'Urbano', icon: 'zap', desc: 'Streetwear: fondo negro, titular XXL y etiquetas de precio.', products: 4,
    ph: { title: 'Ej. Nuevo drop', subtitle: 'Ej. Stock limitado, talles S al XXL', badge: 'Ej. New drop' } },

  { id: 'electro', kind: 'electro', label: 'Ficha de producto', icon: 'monitor', desc: '4 productos con precio grande y beneficios (cuotas, envío, garantía).', products: 4, perks: true,
    ph: { title: 'Ej. Semana del hogar', subtitle: 'Ej. Las mejores marcas al mejor precio', badge: 'Ej. Ofertas', bulletsLabel: 'Beneficios', bullets: ['Ej. 12 cuotas sin interés', 'Ej. Envío gratis', 'Ej. Garantía oficial', ''] } },
  { id: 'ofertazo', kind: 'electro', label: 'Ofertazo', icon: 'percent', desc: 'Estilo de gran superficie: descuento gigante y 3 productos en fila.', products: 3, perks: true,
    ph: { title: 'Ej. Liquidación total', subtitle: 'Ej. Hasta agotar stock', badge: 'Ej. HASTA 40% OFF', bulletsLabel: 'Beneficios', bullets: ['Ej. Cuotas sin interés', 'Ej. Retiro en el día', 'Ej. Instalación', ''] } }
]

export const layoutsOfKind = (kind) => FLYER_LAYOUTS.filter((l) => l.kind === kind)
export const layoutById = (id) => FLYER_LAYOUTS.find((l) => l.id === id) || FLYER_LAYOUTS[0]

// Medidas en mm (vertical). Todas comparten la proporción A.
export const FLYER_SIZES = [
  { id: 'a4', label: 'A4', w: 210, h: 297, note: 'Hoja completa' },
  { id: 'a5', label: 'A5', w: 148, h: 210, note: 'Media hoja A4' },
  { id: 'a6', label: 'A6', w: 105, h: 148, note: 'Cuarto de hoja A4' },
  { id: 'a7', label: 'A7', w: 74, h: 105, note: 'Octavo de hoja A4' }
]
export const sizeById = (id) => FLYER_SIZES.find((s) => s.id === id) || FLYER_SIZES[1]

// Imposición: cuántas copias entran en la hoja y cómo se acomodan. Cada celda
// mide exactamente el tamaño del folleto, así que nunca se pisan entre sí:
// se prueba hoja A4 vertical y apaisada y se elige la que entra más copias.
export function imposition(sizeId, sheet) {
  const s = sizeById(sizeId)
  if (sheet !== 'a4' || s.id === 'a4') {
    return { cols: 1, rows: 1, count: 1, pageW: s.w, pageH: s.h, landscape: false, fw: s.w, fh: s.h, own: true }
  }
  const best = [false, true]
    .map((landscape) => {
      const pageW = landscape ? 297 : 210
      const pageH = landscape ? 210 : 297
      const cols = Math.floor(pageW / s.w)
      const rows = Math.floor(pageH / s.h)
      return { cols, rows, count: cols * rows, pageW, pageH, landscape, fw: s.w, fh: s.h, own: false }
    })
    .sort((a, b) => b.count - a.count || Number(a.landscape) - Number(b.landscape))[0]
  return best
}

export const FLYER_LIMITS = { title: 42, subtitle: 110, badge: 14, cta: 60, bullet: 46, contact: 40 }

export function defaultFlyerDraft(contact = '') {
  return {
    kind: 'marketing',
    layout: 'impacto',
    size: 'a5',
    sheet: 'a4',
    title: '',
    subtitle: '',
    badge: '',
    bullets: ['', '', '', ''],
    cta: 'Escaneá y mirá todo el catálogo',
    contact,
    photo: '',
    productIds: [],
    showQr: true,
    showLogo: true
  }
}

// Precio de un producto del catálogo del dueño: la mejor oferta vigente
// (manual o por descuento programado) pasa a ser el precio y el de lista se tacha.
export function flyerProduct(p) {
  const price = Number(p.price)
  const offers = [p.offer_price, p.discount_offer].map(Number).filter((n) => n > 0 && n < price)
  const offer = offers.length ? Math.min(...offers) : null
  return { id: p.id, name: p.name, image: p.image || '', price: offer ?? price, old: offer != null ? price : null }
}

const keyOf = (slug) => `davent:flyer-draft:${slug || 'tienda'}`

export function loadFlyerDraft(slug, contact = '') {
  const base = defaultFlyerDraft(contact)
  try {
    const raw = JSON.parse(localStorage.getItem(keyOf(slug)) || 'null')
    if (!raw || typeof raw !== 'object') return base
    const bullets = Array.isArray(raw.bullets) ? raw.bullets.slice(0, 4).map(String) : base.bullets
    while (bullets.length < 4) bullets.push('')
    const merged = { ...base, ...raw, bullets }
    merged.productIds = Array.isArray(raw.productIds) ? raw.productIds.slice(0, 6) : []
    const layout = layoutById(merged.layout)
    merged.layout = layout.id
    merged.kind = layout.kind
    merged.size = sizeById(merged.size).id
    if (merged.sheet !== 'a4' && merged.sheet !== 'own') merged.sheet = 'a4'
    return merged
  } catch {
    return base
  }
}

export function saveFlyerDraft(slug, draft) {
  try {
    localStorage.setItem(keyOf(slug), JSON.stringify(draft))
  } catch { /* cuota llena o modo privado: el borrador simplemente no persiste */ }
}

export function clearFlyerDraft(slug) {
  try { localStorage.removeItem(keyOf(slug)) } catch { /* noop */ }
}
