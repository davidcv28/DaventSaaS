// Folleto a medida: el diseño (layout) lo arma DAVENT y el cliente rellena
// los textos y elige qué contenido lleva (productos del catálogo, servicios
// o una selección automática de lo ya cargado en la página). El borrador
// vive en localStorage por tienda: el diseñador lo guarda y la vista de
// impresión (/folleto?custom=1) lo lee, sin tocar el backend.
import { resolveSiteTheme } from '../studio/contract.js'
import { storeThemeVars, storeFontFamily, serviceHue } from '../api/stores.api.js'
import { formatARS } from '../api/billing.api.js'

export const FLYER_KINDS = [
  { id: 'empresa', label: 'Publicidad de empresa', icon: 'store', desc: 'Presentá tu negocio: quiénes son, qué hacen y por qué elegirte.' },
  { id: 'marketing', label: 'Promociones', icon: 'megaphone', desc: 'Ofertas y campañas puntuales con una foto y un llamado a la acción.' },
  { id: 'catalogo', label: 'Productos y precios', icon: 'package', desc: 'Catálogo con foto y precio: comida, almacén, kioscos, etc.' },
  { id: 'indumentaria', label: 'Indumentaria', icon: 'tag', desc: 'Colecciones y prendas para tiendas de ropa y calzado.' },
  { id: 'electro', label: 'Electrodomésticos', icon: 'monitor', desc: 'Ofertas de electro y tecnología con precio y cuotas.' }
]

// Formatos admitidos por la mayoría de los diseños: hojas de impresión y
// piezas digitales verticales/cuadradas. El diseño 'banner' es el único que
// vive en formato horizontal.
const STD_SIZES = ['a4', 'carta', 'a5', 'a6', 'a7', 'post', 'story']

export const FLYER_LAYOUTS = [
  { id: 'portada', kind: 'empresa', label: 'Portada', icon: 'store', desc: 'Tapa de marca: logo y nombre al centro, titular y llamado.', photo: true,
    sizes: STD_SIZES,
    ph: { title: 'Ej. Todo lo que buscás, en un solo lugar', subtitle: 'Ej. Atención personalizada y precios de siempre', badge: 'Ej. Desde 2015', bulletsLabel: 'Razones para elegirte', bullets: ['Ej. Calidad garantizada', 'Ej. Atención directa', 'Ej. Precios claros', ''] } },
  { id: 'corporativo', kind: 'empresa', label: 'Corporativo', icon: 'store', desc: 'Limpio y profesional: nombre, foto y 4 puntos fuertes numerados.', photo: true,
    sizes: STD_SIZES,
    ph: { title: 'Ej. Constructora Norte', subtitle: 'Ej. Más de 15 años construyendo hogares en Salta', badge: 'Ej. Desde 2009', bulletsLabel: 'Servicios o puntos fuertes', bullets: ['Ej. Obras llave en mano', 'Ej. Presupuesto sin cargo', 'Ej. Garantía por escrito', 'Ej. Atención personalizada'] } },
  { id: 'manifiesto', kind: 'empresa', label: 'Manifiesto', icon: 'megaphone', desc: 'Foto a sangre con una frase de marca enorme. Impacto e identidad.', photo: true,
    sizes: STD_SIZES,
    ph: { title: 'Ej. Hacemos que tu casa respire', subtitle: 'Ej. Diseño, calidad y compromiso en cada detalle', badge: 'Ej. Nueva etapa', bulletsLabel: 'Etiquetas de la marca', bullets: ['Ej. Calidad', 'Ej. Confianza', 'Ej. Garantía', ''] } },
  { id: 'servicios', kind: 'empresa', label: 'Servicios', icon: 'checklist', desc: 'Fondo oscuro con tus servicios en lista numerada.', photo: true,
    sizes: STD_SIZES, list: true, products: 6, prefer: 'services',
    ph: { title: 'Ej. Todo para tu hogar', subtitle: 'Ej. Un equipo, una sola llamada', badge: 'Ej. Servicio 24 hs', bulletsLabel: 'Servicios', bullets: ['Ej. Plomería y gas', 'Ej. Electricidad', 'Ej. Pintura y reformas', 'Ej. Mantenimiento'] } },
  { id: 'ficha', kind: 'empresa', label: 'Ficha de servicio', icon: 'wrench', desc: 'Foto al costado y tus servicios numerados: claro, cálido y directo.', photo: true,
    sizes: STD_SIZES, list: true, products: 6, prefer: 'services',
    ph: { title: 'Ej. Electricista matriculado', subtitle: 'Ej. Instalaciones, urgencias y mantenimiento en tu zona', badge: 'Ej. 24 hs', bulletsLabel: 'Servicios', bullets: ['Ej. Instalaciones eléctricas', 'Ej. Urgencias las 24 hs', 'Ej. Tableros y automatización', 'Ej. Presupuesto sin cargo'] } },
  { id: 'anuncio', kind: 'empresa', label: 'Anuncio', icon: 'flame', desc: 'Para novedades: inauguración, nueva sucursal o aniversario.', photo: true,
    sizes: STD_SIZES,
    ph: { title: 'Ej. Nueva sucursal en el centro', subtitle: 'Ej. Te esperamos con sorpresas y regalos', badge: 'Ej. INAUGURACIÓN', bulletsLabel: 'Detalles (fecha, dirección, horario)', bullets: ['Ej. Sábado 15 de marzo', 'Ej. Av. Belgrano 450', 'Ej. De 9 a 21 hs', ''] } },

  { id: 'impacto', kind: 'marketing', label: 'Impacto', icon: 'zap', desc: 'Foto grande arriba, titular fuerte y sello de oferta.', photo: true,
    sizes: STD_SIZES },
  { id: 'oferta', kind: 'marketing', label: 'Oferta', icon: 'percent', desc: 'Fondo a todo color con el descuento como protagonista.', photo: true,
    sizes: STD_SIZES },
  { id: 'editorial', kind: 'marketing', label: 'Editorial', icon: 'sparkles', desc: 'Elegante y sobrio, con foto en arco sobre fondo claro.', photo: true,
    sizes: STD_SIZES },
  { id: 'story', kind: 'marketing', label: 'Historia', icon: 'smartphone', desc: 'Vertical para redes: marca arriba, oferta enorme y QR abajo.', photo: true,
    sizes: STD_SIZES,
    ph: { title: 'Ej. Semana de ofertas', subtitle: 'Ej. Solo por hoy en toda la tienda', badge: 'Ej. -30%' } },
  { id: 'banner', kind: 'marketing', label: 'Banner', icon: 'panel-top', desc: 'Horizontal para portada de WhatsApp o web: marca, oferta y QR.',
    sizes: ['banner'], products: 3,
    ph: { title: 'Ej. Envíos gratis esta semana', badge: 'Ej. OFERTA' } },

  { id: 'vitrina', kind: 'catalogo', label: 'Vitrina', icon: 'layout-grid', desc: 'Hasta 4 productos en cuadrícula, con foto y precio.',
    sizes: STD_SIZES, products: 4 },
  { id: 'nueve', kind: 'catalogo', label: 'Grilla 9', icon: 'layout-grid', desc: 'Hasta 9 productos en cuadrícula compacta de 3×3.',
    sizes: STD_SIZES, products: 9 },
  { id: 'lista', kind: 'catalogo', label: 'Lista de precios', icon: 'receipt', desc: 'Hasta 6 productos en lista, ideal para precios.',
    sizes: STD_SIZES, products: 6 },
  { id: 'carta', kind: 'catalogo', label: 'Carta / Menú', icon: 'file-text', desc: 'Lista elegante estilo restaurante: nombre, descripción y precio.',
    sizes: STD_SIZES, list: true, products: 8,
    ph: { title: 'Ej. Nuestra carta', subtitle: 'Ej. Hecho en el día, con productos de estación', badge: 'Ej. Menú' } },
  { id: 'destacado', kind: 'catalogo', label: 'Destacado', icon: 'star', desc: 'Un producto estrella grande y 3 más abajo.',
    sizes: STD_SIZES, products: 4 },

  { id: 'moda', kind: 'indumentaria', label: 'Colección', icon: 'sparkles', desc: 'Editorial de moda: 3 prendas en pliegos altos sobre fondo marfil.',
    sizes: STD_SIZES, products: 3,
    ph: { title: 'Ej. Otoño / Invierno', subtitle: 'Ej. Nueva colección ya en tienda', badge: 'Ej. Nuevo' } },
  { id: 'urbano', kind: 'indumentaria', label: 'Urbano', icon: 'zap', desc: 'Streetwear: fondo negro, titular XXL y etiquetas de precio.',
    sizes: STD_SIZES, products: 4,
    ph: { title: 'Ej. Nuevo drop', subtitle: 'Ej. Stock limitado, talles S al XXL', badge: 'Ej. New drop' } },

  { id: 'electro', kind: 'electro', label: 'Ficha de producto', icon: 'monitor', desc: '4 productos con precio grande y beneficios (cuotas, envío, garantía).',
    sizes: STD_SIZES, products: 4, perks: true,
    ph: { title: 'Ej. Semana del hogar', subtitle: 'Ej. Las mejores marcas al mejor precio', badge: 'Ej. Ofertas', bulletsLabel: 'Beneficios', bullets: ['Ej. 12 cuotas sin interés', 'Ej. Envío gratis', 'Ej. Garantía oficial', ''] } },
  { id: 'ofertazo', kind: 'electro', label: 'Ofertazo', icon: 'percent', desc: 'Estilo de gran superficie: descuento gigante y 3 productos en fila.',
    sizes: STD_SIZES, products: 3, perks: true,
    ph: { title: 'Ej. Liquidación total', subtitle: 'Ej. Hasta agotar stock', badge: 'Ej. HASTA 40% OFF', bulletsLabel: 'Beneficios', bullets: ['Ej. Cuotas sin interés', 'Ej. Retiro en el día', 'Ej. Instalación', ''] } }
]

export const layoutsOfKind = (kind) => FLYER_LAYOUTS.filter((l) => l.kind === kind)
export const layoutById = (id) => FLYER_LAYOUTS.find((l) => l.id === id) || FLYER_LAYOUTS[0]
// Diseños compatibles con un formato (el 'banner' solo acepta su diseño).
export const layoutsForSize = (sizeId) => FLYER_LAYOUTS.filter((l) => !l.sizes || l.sizes.includes(sizeId))

// Fuentes de contenido del folleto: 'landing' toma automáticamente lo
// cargado en la página (ofertas y servicios), 'catalog' deja elegir
// productos y 'services' deja elegir servicios.
export const FLYER_SOURCES = [
  { id: 'landing', label: 'Automático', icon: 'sparkles', desc: 'Toma ofertas y destacados ya cargados en tu página.' },
  { id: 'catalog', label: 'Productos', icon: 'package', desc: 'Elegí los productos que va a mostrar.' },
  { id: 'services', label: 'Servicios', icon: 'wrench', desc: 'Elegí los servicios que va a mostrar.' }
]

// Medidas: hojas en mm (para imprimir) y piezas digitales en px (para
// redes/WhatsApp; el PNG sale exactamente en esos píxeles).
export const FLYER_SIZES = [
  { id: 'a4', group: 'print', label: 'A4', w: 210, h: 297, unit: 'mm', note: 'Hoja completa' },
  { id: 'carta', group: 'print', label: 'Carta', w: 216, h: 279, unit: 'mm', note: 'Hoja americana' },
  { id: 'a5', group: 'print', label: 'A5', w: 148, h: 210, unit: 'mm', note: 'Media hoja A4' },
  { id: 'a6', group: 'print', label: 'A6', w: 105, h: 148, unit: 'mm', note: 'Cuarto de hoja A4' },
  { id: 'a7', group: 'print', label: 'A7', w: 74, h: 105, unit: 'mm', note: 'Octavo de hoja A4' },
  { id: 'post', group: 'digital', label: 'Post', w: 1080, h: 1080, unit: 'px', note: 'Cuadrado · redes' },
  { id: 'story', group: 'digital', label: 'Historia', w: 1080, h: 1920, unit: 'px', note: 'Vertical · estados' },
  { id: 'banner', group: 'digital', label: 'Banner', w: 1920, h: 640, unit: 'px', note: 'Horizontal · portada' }
]
export const sizeById = (id) => FLYER_SIZES.find((s) => s.id === id) || FLYER_SIZES.find((s) => s.id === 'a5')
export const isDigitalSize = (id) => sizeById(id).group === 'digital'

// Tamaño del PNG de salida: los digitales salen en sus píxeles declarados;
// las hojas se rasterizan a ~150 dpi para que el texto quede nítido.
export function pngSizeOf(sizeId) {
  const s = sizeById(sizeId)
  if (s.unit === 'px') return { w: s.w, h: s.h }
  const k = (150 / 25.4)
  return { w: Math.round(s.w * k), h: Math.round(s.h * k) }
}

// Imposición: cuántas copias entran en la hoja y cómo se acomodan. Cada
// celda mide exactamente el tamaño del folleto, así que nunca se pisan
// entre sí: se prueba hoja A4 vertical y apaisada y se elige la que entra
// más copias. Las piezas digitales y la hoja Carta (más ancha que A4) van
// una por página ajustadas a la hoja disponible.
export function imposition(sizeId, sheet) {
  const s = sizeById(sizeId)
  if (s.unit === 'px') return { ...fitSheet(s), cols: 1, rows: 1, count: 1, own: true, digital: true }
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
  if (!best.count) return { cols: 1, rows: 1, count: 1, pageW: s.w, pageH: s.h, landscape: false, fw: s.w, fh: s.h, own: true }
  return best
}

// Pieza digital ajustada a una hoja A4 para imprimir de todos modos (una
// por página, centrada y sin recortes).
function fitSheet(s) {
  const r = s.w / s.h
  const box = r >= 1 ? { w: 270, h: 180 } : { w: 180, h: 270 }
  let fw = box.w
  let fh = fw / r
  if (fh > box.h) { fh = box.h; fw = fh * r }
  const landscape = r >= 1
  return { pageW: landscape ? 297 : 210, pageH: landscape ? 210 : 297, landscape, fw: Math.round(fw), fh: Math.round(fh) }
}

export const FLYER_LIMITS = { title: 42, subtitle: 110, badge: 14, cta: 60, bullet: 46, contact: 40 }

export function defaultFlyerDraft(contact = '') {
  return {
    kind: 'marketing',
    layout: 'impacto',
    size: 'a5',
    sheet: 'a4',
    source: 'landing',
    title: '',
    subtitle: '',
    badge: '',
    bullets: ['', '', '', ''],
    cta: 'Escaneá y mirá todo el catálogo',
    contact,
    photo: '',
    productIds: [],
    serviceIds: [],
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
  return { id: p.id, name: p.name, image: p.image || '', icon: '', price: offer ?? price, old: offer != null ? price : null, desc: '' }
}

// Ítem de servicio (dominio services de la API): precio orientativo o
// "A convenir"; sin foto — las tarjetas muestran el ícono del servicio.
export function flyerService(s) {
  const price = Number(s.price)
  const hasPrice = s.price !== null && s.price !== undefined && Number.isFinite(price)
  return { id: `svc-${s.id}`, name: s.name, image: '', icon: s.icon || 'wrench', hue: serviceHue(s.icon), price: hasPrice ? price : null, old: null, priceLabel: hasPrice ? null : 'A convenir', desc: s.description || '' }
}

// Ítem del bloque "Qué ofrecemos" de la portada (customization.services):
// nombre + texto, sin precio. Es el respaldo cuando la página Servicios
// no está en el plan (su API responde 403).
export function flyerLegacyService(row, i) {
  return { id: `mk-${i}`, name: row?.title || '', image: '', icon: row?.icon || 'package', hue: serviceHue(row?.icon), price: null, old: null, priceLabel: '', desc: row?.text || '' }
}

// Texto de precio de cualquier ítem del folleto (producto o servicio).
export const priceText = (p) => p.priceLabel || (p.price == null ? '' : formatARS(p.price))

// Resuelve los ítems que muestra el folleto según la fuente elegida.
// `products` ya viene normalizado con flyerProduct y `services` con
// flyerService/flyerLegacyService. En 'landing' se toma lo mejor cargado:
// ofertas primero, luego lo que tenga foto; los diseños de servicios
// prefieren la lista de servicios.
export function resolveFlyerItems(draft, layout, { products = [], services = [] } = {}) {
  const max = layout.products || 0
  if (!max) return []
  if (draft.source === 'catalog') {
    return draft.productIds.map((id) => products.find((p) => p.id === id)).filter(Boolean).slice(0, max)
  }
  if (draft.source === 'services') {
    return draft.serviceIds.map((id) => services.find((s) => s.id === id)).filter(Boolean).slice(0, max)
  }
  const preferServices = layout.prefer === 'services'
  const ranked = [...products].sort((a, b) => Number(b.old != null) - Number(a.old != null) || Number(Boolean(b.image)) - Number(Boolean(a.image)))
  const first = preferServices ? [services, ranked] : [ranked, services]
  const pool = first[0].length ? first[0] : first[1]
  return pool.slice(0, max)
}

// ---------------------------------------------------------------------------
// Tema del folleto: hereda la identidad de la web. Con site_theme (Studio)
// se usan su acento/tinta y su fuente de titulares; sin site_theme quedan
// el acento y la fuente del Diseño web — una tienda sin Studio se ve igual.
// ---------------------------------------------------------------------------
export function flyerVars(customization) {
  const base = storeThemeVars(customization)
  const st = customization?.site_theme
  if (!st || typeof st !== 'object' || !Object.keys(st).length) return base
  const t = resolveSiteTheme(st)
  return {
    ...base,
    '--store-accent': t.palette.accent,
    '--store-accent-ink': t.palette.secondary,
    '--store-accent-soft': `color-mix(in srgb, ${t.palette.accent} 12%, #fff)`,
    '--store-font': flyerFont(t.typography.heading, customization)
  }
}

// Familia de la fuente del folleto: slug del catálogo -> familia real; un
// stack CSS propio viaja tal cual.
function flyerFont(value, customization) {
  const v = String(value || '').trim()
  if (v.includes(',') || v.includes("'") || v.includes('"')) return v
  return storeFontFamily(v || customization?.name_font)
}

// Slug de Google Fonts que el folleto necesita cargado (para la vista y
// para incrustarlo en el PNG): el heading del site_theme si hay, si no la
// fuente del nombre.
export function flyerFontSlug(customization) {
  const st = customization?.site_theme
  const heading = st?.typography?.heading
  const v = String(heading || customization?.name_font || '').trim()
  return v && !v.includes(',') && !v.includes("'") ? v : ''
}

// ---------------------------------------------------------------------------
// Exportar a PNG: la tarjeta se serializa como SVG foreignObject con el CSS
// de la app incrustado, las imágenes pasadas a dataURL (CORS) y las fuentes
// de Google embebidas como @font-face. Cero dependencias.
// ---------------------------------------------------------------------------
const FLYER_CSS_CACHE = { css: null }

async function flyerCssText() {
  if (FLYER_CSS_CACHE.css) return FLYER_CSS_CACHE.css
  const parts = []
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) parts.push(rule.cssText)
    } catch { /* hojas cross-origin (Google Fonts) se resuelven abajo */ }
  }
  // Fuentes externas: se baja el css2 y se reemplaza cada url() por dataURL
  // (las hojas de Google Fonts sirven con CORS abierto).
  const links = [...document.querySelectorAll('link[rel~="stylesheet"]')]
    .map((l) => l.href)
    .filter((h) => h.includes('fonts.googleapis'))
  for (const href of links.slice(0, 4)) {
    try {
      const css = await (await fetch(href)).text()
      parts.push(await inlineFontUrls(css))
    } catch { /* sin fuente embebida: el PNG sale con la fuente de respaldo */ }
  }
  FLYER_CSS_CACHE.css = parts.join('\n')
  return FLYER_CSS_CACHE.css
}

async function inlineFontUrls(css) {
  const urls = [...css.matchAll(/url\((https:[^)]+)\)/g)].map((m) => m[1]).slice(0, 40)
  for (const url of urls) {
    try {
      const blob = await (await fetch(url)).blob()
      const data = await blobToDataUrl(blob)
      css = css.split(url).join(data)
    } catch { /* noop */ }
  }
  return css
}

const blobToDataUrl = (blob) => new Promise((res, rej) => {
  const r = new FileReader()
  r.onload = () => res(r.result)
  r.onerror = rej
  r.readAsDataURL(blob)
})

// Cada <img> externo viaja como dataURL; si el servidor no deja leerla
// (CORS), se quita el nodo y queda el fondo de marca del diseño.
async function inlineImages(root) {
  let skipped = 0
  const imgs = [...root.querySelectorAll('img')]
  await Promise.all(imgs.map(async (img) => {
    const src = img.getAttribute('src') || ''
    if (!src || src.startsWith('data:') || src.startsWith('blob:')) return
    try {
      const blob = await (await fetch(src, { mode: 'cors' })).blob()
      img.setAttribute('src', await blobToDataUrl(blob))
    } catch {
      skipped += 1
      img.remove()
    }
  }))
  return skipped
}

// Exporta el nodo .fc a un PNG de w×h píxeles. `vars` son las CSS vars de
// marca (--store-*) que el clon pierde al despegarse del árbol. Devuelve
// { blob, skipped } — skipped = imágenes que no se pudieron incrustar.
export async function exportFlyerPng(el, { w, h, vars = {} } = {}) {
  const css = await flyerCssText()
  const clone = el.cloneNode(true)
  clone.setAttribute('style', `${el.getAttribute('style') || ''};width:${w}px;height:${h}px;`)
  for (const [k, v] of Object.entries(vars)) clone.style.setProperty(k, v)
  const skipped = await inlineImages(clone)
  const doc = clone.ownerDocument
  const wrap = doc.createElement('div')
  wrap.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml')
  const style = doc.createElement('style')
  style.textContent = css
  wrap.appendChild(style)
  wrap.appendChild(clone)
  const html = new XMLSerializer().serializeToString(wrap)
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><foreignObject width="100%" height="100%">${html}</foreignObject></svg>`
  // data: URL, no blob: — Chrome mancha el canvas si la imagen SVG con
  // foreignObject viene de una blob: (mismo contenido, mismo origen).
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  const img = await new Promise((res, rej) => {
    const i = new Image()
    i.onload = () => res(i)
    i.onerror = () => rej(new Error('svg'))
    i.src = url
  })
  const canvas = doc.createElement('canvas')
  canvas.width = w
  canvas.height = h
  canvas.getContext('2d').drawImage(img, 0, 0, w, h)
  const blob = await new Promise((res) => canvas.toBlob(res, 'image/png'))
  return { blob, skipped }
}

export function downloadBlob(blob, fileName) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = fileName
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 4000)
}

// ---------------------------------------------------------------------------
// Plantillas guardadas (localStorage): diseños del usuario para reutilizar.
// ---------------------------------------------------------------------------
const TPL_MAX = 8
const tplKeyOf = (slug) => `davent:flyer-tpls:${slug || 'tienda'}`

export function listFlyerTemplates(slug) {
  try {
    const raw = JSON.parse(localStorage.getItem(tplKeyOf(slug)) || '[]')
    return Array.isArray(raw) ? raw.filter((t) => t && t.draft) : []
  } catch { return [] }
}

export function saveFlyerTemplate(slug, name, draft) {
  const list = listFlyerTemplates(slug)
  const item = { id: `t${Date.now()}`, name: String(name || 'Mi folleto').slice(0, 30), draft: JSON.parse(JSON.stringify(draft)) }
  list.unshift(item)
  try { localStorage.setItem(tplKeyOf(slug), JSON.stringify(list.slice(0, TPL_MAX))) } catch { /* noop */ }
  return item
}

export function deleteFlyerTemplate(slug, id) {
  const list = listFlyerTemplates(slug).filter((t) => t.id !== id)
  try { localStorage.setItem(tplKeyOf(slug), JSON.stringify(list)) } catch { /* noop */ }
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
    merged.productIds = Array.isArray(raw.productIds) ? raw.productIds.slice(0, 9) : []
    merged.serviceIds = Array.isArray(raw.serviceIds) ? raw.serviceIds.slice(0, 9).map(String) : []
    if (!FLYER_SOURCES.some((s) => s.id === merged.source)) merged.source = 'landing'
    const layout = layoutById(merged.layout)
    merged.layout = layout.id
    merged.kind = layout.kind
    merged.size = sizeById(merged.size).id
    // El diseño elegido manda: si no admite el formato, el formato se ajusta.
    if (layout.sizes && !layout.sizes.includes(merged.size)) merged.size = layout.sizes[0]
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
