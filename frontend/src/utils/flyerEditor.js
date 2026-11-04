// Documento del editor libre de folletos: lienzo con elementos absolutos
// posicionados en % del formato elegido (x/y/ancho/alto de 0 a 100), con
// rotación y orden de capas. El borrador vive en localStorage por tienda y
// la vista de impresión (/folleto?custom=2) lo lee, igual que el diseñador.
import { sizeById } from './flyer.js'

let seq = 0
const uid = () => `e${Date.now().toString(36)}${(seq++).toString(36)}`

// Familias elegibles en textos: 'store' hereda la fuente de la web (como el
// resto del folleto); el resto sale del catálogo STORE_FONTS del Diseño web
// (Google Fonts, se cargan on-demand con ensureStoreFont). Las familias se
// ofrecen agrupadas por estilo para el selectbox del inspector.
import { STORE_FONTS, storeFontFamily, ensureStoreFont } from '../api/stores.api.js'

export const EL_FONT_GROUPS = [
  { label: 'Sans serif', keys: ['inter', 'roboto', 'open-sans', 'lato', 'montserrat', 'poppins', 'raleway', 'nunito', 'work-sans', 'dm-sans', 'sora', 'space-grotesk', 'rubik', 'manrope', 'instrument-sans', 'figtree', 'hanken-grotesk', 'outfit', 'plus-jakarta-sans', 'jost', 'barlow', 'archivo', 'bricolage-grotesque', 'quicksand', 'comfortaa', 'inter-tight'] },
  { label: 'Serif y editorial', keys: ['playfair-display', 'merriweather', 'lora', 'fraunces', 'cinzel', 'cormorant-garamond', 'dm-serif-display', 'libre-baskerville'] },
  { label: 'Display e impacto', keys: ['oswald', 'bebas-neue', 'anton', 'archivo-black', 'righteous', 'orbitron', 'barlow-condensed'] },
  { label: 'Manuscritas', keys: ['pacifico', 'dancing-script', 'caveat', 'lobster'] },
  { label: 'Monoespaciadas', keys: ['space-mono', 'jetbrains-mono'] }
]
export const EL_FONT_SLUGS = EL_FONT_GROUPS.flatMap((g) => g.keys)

// Borradores viejos guardaban ids de stacks genéricos: se mapean al slug
// equivalente del catálogo para que sigan viéndose igual (y mejor).
const LEGACY_FONTS = { sans: 'inter', serif: 'lora', mono: 'jetbrains-mono', display: 'anton' }

export function fontFamilyOf(id) {
  if (id === 'store' || !id) return 'var(--store-font, Inter, system-ui, sans-serif)'
  return storeFontFamily(LEGACY_FONTS[id] || id)
}

// Normaliza el id guardado (legacy → slug del catálogo).
export const fontSlugOf = (id) => LEGACY_FONTS[id] || id
// Carga el css2 de la fuente elegida (no-op para 'store' y stacks locales).
export function ensureElFont(id) {
  const slug = fontSlugOf(id)
  if (slug && slug !== 'store' && STORE_FONTS[slug]) ensureStoreFont(slug)
}

// Un solo <link> css2 con todas las familias del catálogo: la vista previa
// del selectbox y cualquier texto ya guardado se ven al instante sin N
// requests separadas (mismo patrón que ensureStoreFontPicker).
export function ensureElFontCatalog() {
  const families = EL_FONT_SLUGS
    .map((k) => STORE_FONTS[k]?.google)
    .filter(Boolean)
    .sort()
    .map((g) => `family=${g}`)
    .join('&')
  if (!families || document.getElementById('flyer-fonts-catalog')) return
  const link = document.createElement('link')
  link.id = 'flyer-fonts-catalog'
  link.rel = 'stylesheet'
  link.href = `https://fonts.googleapis.com/css2?${families}&display=swap`
  document.head.appendChild(link)
}

// Rellenos: los tokens ('accent', 'ink'…) resuelven a las vars de marca de
// la web para que el folleto salga con los colores de la tienda; cualquier
// otro valor es un color CSS directo (de la paleta o del picker).
export const EL_FILLS = {
  accent: 'var(--store-accent, #6366f1)',
  ink: 'var(--store-accent-ink, #4338ca)',
  soft: 'var(--store-accent-soft, #eef2ff)',
  paper: '#ffffff',
  dark: '#0f172a',
  muted: '#64748b',
  gold: '#fde047',
  green: '#16a34a',
  red: '#dc2626'
}
export const fillOf = (v) => EL_FILLS[v] || v || 'transparent'
export const EL_SWATCHES = [
  { id: 'accent', label: 'Color de tu web' },
  { id: 'ink', label: 'Tinta de tu web' },
  { id: 'soft', label: 'Suave de tu web' },
  { id: 'paper', label: 'Blanco' },
  { id: 'dark', label: 'Negro' },
  { id: 'muted', label: 'Gris' },
  { id: 'gold', label: 'Dorado' },
  { id: 'green', label: 'Verde' },
  { id: 'red', label: 'Rojo' }
]

export const EL_SHAPES = [
  { id: 'rect', label: 'Rectángulo' },
  { id: 'round', label: 'Redondeado' },
  { id: 'pill', label: 'Píldora' },
  { id: 'circle', label: 'Círculo / óvalo' },
  { id: 'line', label: 'Línea' },
  { id: 'star', label: 'Estrella' }
]

// Iconos insertables (set Lucide ya bundleado por AppIcon).
export const EL_ICONS = [
  'sparkles', 'zap', 'flame', 'percent', 'tag', 'star', 'heart', 'gift',
  'truck', 'phone', 'whatsapp', 'map-pin', 'store', 'check', 'badge-check',
  'crown', 'megaphone', 'calendar', 'clock', 'qr-code', 'shield-check',
  'thumbs-up', 'shopping-bag'
]

// Herramientas del riel izquierdo: cada una agrega un elemento al lienzo.
export const EL_TOOLS = [
  { id: 'title', icon: 'type', label: 'Título', hint: 'Texto grande' },
  { id: 'text', icon: 'file-text', label: 'Texto', hint: 'Frase o párrafo' },
  { id: 'image', icon: 'image', label: 'Foto', hint: 'De tu galería o subida' },
  { id: 'shape', icon: 'box', label: 'Forma', hint: 'Bloques, líneas, sellos' },
  { id: 'icon', icon: 'star', label: 'Ícono', hint: 'Dibujos simples' },
  { id: 'product', icon: 'package', label: 'Producto', hint: 'Tarjeta con foto y precio' },
  { id: 'logo', icon: 'store', label: 'Tu marca', hint: 'Logo y nombre' },
  { id: 'qr', icon: 'qr-code', label: 'QR', hint: 'Lleva a tu página' }
]

export const EL_TYPE_LABELS = {
  text: 'Texto', image: 'Foto', shape: 'Forma', icon: 'Ícono',
  product: 'Producto', logo: 'Marca', qr: 'Código QR'
}

const clamp = (n, min, max) => Math.min(max, Math.max(min, n))

// Valores por defecto de cada herramienta (posiciones en % del lienzo).
const DEFS = {
  title: { type: 'text', x: 8, y: 40, w: 84, h: 14, text: 'TU TITULAR ACÁ', font: 'store', size: 9, bold: true, align: 'center', color: 'ink', uppercase: true, spacing: 0, line: 1.05 },
  text: { type: 'text', x: 12, y: 56, w: 76, h: 9, text: 'Tu frase de apoyo', font: 'inter', size: 4, bold: false, align: 'center', color: 'dark', uppercase: false, spacing: 0, line: 1.3 },
  image: { type: 'image', x: 15, y: 15, w: 40, h: 36, src: '', fit: 'cover', radius: 10 },
  shape: { type: 'shape', x: 10, y: 10, w: 34, h: 20, shape: 'round', fill: 'accent', stroke: '', strokeW: 0 },
  icon: { type: 'icon', x: 44, y: 44, w: 12, h: 12, name: 'star', color: 'accent' },
  product: { type: 'product', x: 10, y: 20, w: 26, h: 34, productId: '', bg: 'paper', ink: 'dark', radius: 10, showPrice: true, showName: true },
  logo: { type: 'logo', x: 22, y: 5, w: 56, h: 11, color: 'dark', showName: true },
  qr: { type: 'qr', x: 74, y: 78, w: 20, h: 20, bg: 'paper', pad: 8 }
}

export function makeElement(tool, extra = {}) {
  const base = { id: uid(), rot: 0, opacity: 1, locked: false, hidden: false }
  const def = DEFS[tool] || DEFS.text
  return { ...base, ...JSON.parse(JSON.stringify(def)), ...extra }
}

// Composición inicial: banda de marca, foto, titular, texto y pie con QR.
// El usuario puede borrar todo y armar el folleto desde cero.
export function defaultEditorDoc() {
  return {
    size: 'a5',
    sheet: 'a4',
    bg: 'paper',
    elements: [
      makeElement('shape', { x: 0, y: 0, w: 100, h: 22, shape: 'rect', fill: 'accent' }),
      makeElement('logo', { x: 6, y: 5.5, w: 60, h: 11, color: 'paper' }),
      makeElement('shape', { x: 76, y: 8, w: 18, h: 6, shape: 'pill', fill: 'gold' }),
      makeElement('image', { x: 10, y: 27, w: 80, h: 34, radius: 12 }),
      makeElement('title', { x: 8, y: 63, w: 84, h: 13, text: 'TU TITULAR ACÁ', size: 8.4 }),
      makeElement('text', { x: 14, y: 76, w: 72, h: 8, text: 'Tu frase de apoyo' }),
      makeElement('shape', { x: 0, y: 88, w: 100, h: 12, shape: 'rect', fill: 'ink' }),
      makeElement('qr', { x: 6, y: 88.6, w: 11, h: 10.8 }),
      makeElement('text', { x: 20, y: 90.5, w: 74, h: 7, text: 'ESCANEÁ Y MIRÁ TODO', font: 'sans', size: 3.6, bold: true, align: 'left', color: 'paper' })
    ]
  }
}

const keyOf = (slug) => `davent:flyer-free:${slug || 'tienda'}`

const num = (v, fallback, min, max) => {
  const n = Number(v)
  return Number.isFinite(n) ? clamp(n, min, max) : fallback
}

// Normaliza un elemento leído del storage: cualquier campo raro vuelve al
// default de su tipo para que un borrador viejo nunca rompa el editor.
function cleanElement(raw) {
  if (!raw || typeof raw !== 'object') return null
  const tool = raw.type === 'text' && raw.variant === 'title' ? 'title' : raw.type
  const el = makeElement(DEFS[tool] ? tool : 'text')
  const out = { ...el, ...raw, id: String(raw.id || uid()) }
  out.x = num(out.x, el.x, -80, 180)
  out.y = num(out.y, el.y, -80, 180)
  out.w = num(out.w, el.w, 1, 300)
  out.h = num(out.h, el.h, 0.5, 300)
  out.rot = num(out.rot, 0, -360, 360)
  out.opacity = num(out.opacity, 1, 0, 1)
  if (out.type === 'text') out.font = fontSlugOf(out.font)
  return out
}

export function loadEditorDoc(slug) {
  const base = defaultEditorDoc()
  try {
    const raw = JSON.parse(localStorage.getItem(keyOf(slug)) || 'null')
    if (!raw || typeof raw !== 'object') return base
    const doc = {
      size: sizeById(raw.size).id,
      sheet: raw.sheet === 'own' ? 'own' : 'a4',
      bg: String(raw.bg || 'paper'),
      elements: (Array.isArray(raw.elements) ? raw.elements : [])
        .map(cleanElement).filter(Boolean).slice(0, 60)
    }
    if (!doc.elements.length) doc.elements = base.elements
    return doc
  } catch {
    return base
  }
}

export function saveEditorDoc(slug, doc) {
  try { localStorage.setItem(keyOf(slug), JSON.stringify(doc)) } catch { /* noop */ }
}
export function clearEditorDoc(slug) {
  try { localStorage.removeItem(keyOf(slug)) } catch { /* noop */ }
}
