// Folleto a medida: el diseño (layout) lo arma DAVENT y el cliente rellena
// los textos y elige una foto de su galería (y, en los de catálogo, sus
// productos). El borrador vive en localStorage por tienda: el diseñador lo
// guarda y la vista de impresión (/folleto?custom=1) lo lee, sin tocar el backend.

export const FLYER_KINDS = [
  { id: 'marketing', label: 'Marketing', icon: 'megaphone', desc: 'Para publicitar tu empresa: una idea, una foto y un llamado a la acción.' },
  { id: 'catalogo', label: 'Catálogo', icon: 'package', desc: 'Para mostrar productos con foto y precio.' }
]

export const FLYER_LAYOUTS = [
  { id: 'impacto', kind: 'marketing', label: 'Impacto', icon: 'zap', desc: 'Foto grande arriba, titular fuerte y sello de oferta.' },
  { id: 'oferta', kind: 'marketing', label: 'Oferta', icon: 'percent', desc: 'Fondo a todo color con el descuento como protagonista.' },
  { id: 'editorial', kind: 'marketing', label: 'Editorial', icon: 'sparkles', desc: 'Elegante y sobrio, con foto en arco sobre fondo claro.' },
  { id: 'vitrina', kind: 'catalogo', label: 'Vitrina', icon: 'layout-grid', desc: 'Hasta 4 productos en cuadrícula, con foto y precio.', products: 4 },
  { id: 'lista', kind: 'catalogo', label: 'Lista de precios', icon: 'receipt', desc: 'Hasta 6 productos en lista, ideal para precios.', products: 6 },
  { id: 'destacado', kind: 'catalogo', label: 'Destacado', icon: 'star', desc: 'Un producto estrella grande y 3 más abajo.', products: 4 }
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
    bullets: ['', '', ''],
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
    const bullets = Array.isArray(raw.bullets) ? raw.bullets.slice(0, 3).map(String) : base.bullets
    while (bullets.length < 3) bullets.push('')
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
