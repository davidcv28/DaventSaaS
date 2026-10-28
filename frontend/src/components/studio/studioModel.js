// Modelo del Studio de diseño: catálogo de herramientas del riel, semilla
// de siteTheme desde la customization actual y utilidades de snapshot.
// Sin estado: las piezas reactivas viven en StudioShell.
import { effectiveAccent } from '../../api/stores.api.js'

// Riel de herramientas (orden = orden visual). Cada panel por defecto vive
// en StudioPanel.vue; cualquier fase puede reemplazarlo con el slot
// #panel-<id> del StudioShell.
export const STUDIO_TOOLS = [
  { id: 'estilos',      icon: 'sparkles',     label: 'Estilos',      desc: 'Identidad, colores, fuente y diseño base de tu página.' },
  { id: 'colores',      icon: 'palette',      label: 'Colores',      desc: 'Paleta por rol, armonías, logo y contraste accesible.' },
  { id: 'tipografia',   icon: 'type',         label: 'Tipografía',   desc: 'Fuentes, pares recomendados, escala y peso.' },
  { id: 'contenedores', icon: 'layout-grid',  label: 'Contenedores', desc: 'Bordes, sombras, densidad, superficie y botones.' },
  { id: 'fondo',        icon: 'image',        label: 'Fondo',        desc: 'Color, degradado, malla, patrón o imagen de fondo.' },
  { id: 'distribucion', icon: 'list-ordered', label: 'Distribución', desc: 'Qué bloques lleva cada página y en qué orden.' },
  { id: 'movil',        icon: 'smartphone',   label: 'Móvil',        desc: 'Navegación, grilla y portada en pantallas chicas.' },
  { id: 'movimiento',   icon: 'zap',          label: 'Movimiento',   desc: 'Revelado al bajar, reacción al mouse e intensidad.' },
  { id: 'folletos',     icon: 'printer',      label: 'Folletos',     desc: 'Piezas imprimibles con tu identidad (QR y ofertas).' },
  { id: 'avanzado',     icon: 'sliders',      label: 'Avanzado',     desc: 'Tema claro/oscuro y ajustes finos del diseño.' }
]

export const SURFACE_LABELS = { landing: 'Inicio', catalog: 'Catálogo', services: 'Servicios' }

// siteTheme sembrado desde la customization guardada: el tema del Studio
// arranca reflejando el look actual (acento efectivo y fuente del nombre).
// No cubre logo/portada/imágenes — viajan por la API dentro del iframe.
export function seedStudioTheme(custom = {}) {
  const a = effectiveAccent(custom)
  return {
    palette: { primary: a.hex, secondary: a.ink, accent: a.hex },
    typography: { heading: custom.name_font || 'inter', body: custom.name_font || 'inter' }
  }
}

// Sincronización form -> siteTheme (una sola dirección): los campos
// editables del diseño actual se reflejan en el tema del Studio para que
// la vista previa los muestre sin guardar.
export function formThemePatch(form = {}) {
  const a = effectiveAccent(form)
  return {
    palette: { primary: a.hex, secondary: a.ink, accent: a.hex },
    typography: { heading: form.name_font || 'inter', body: form.name_font || 'inter' }
  }
}

// Merge profundo acotado al esquema (nivel 2: grupo -> campo).
export function mergeTheme(base, patch) {
  const out = { ...(base || {}) }
  for (const [group, value] of Object.entries(patch || {})) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      out[group] = { ...(base?.[group] || {}), ...value }
    } else if (value !== undefined) {
      out[group] = value
    }
  }
  return out
}

export const clone = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)))

// ---------------------------------------------------------------------------
// Click en la vista previa -> herramienta + control del panel.
// El target resume "qué" se tocó; toolForTarget decide dónde se edita.
// ---------------------------------------------------------------------------

const PICK_RULES = [
  // [predicado sobre el elemento clickeado, target]
  [(el) => el.closest('.sp-top, .sp-shop-nav, .sp-dock'), 'chrome.nav'],
  [(el) => el.closest('.sp-hero, .sp-hero-band, [class*="-hero"], [class*="hero-"]'), 'hero'],
  [(el) => el.closest('.tpc, .sp-card, [class*="-card"]'), 'card'],
  [(el) => el.closest('h1, h2, h3'), 'typo'],
  [(el) => el.closest('.sp-btn, [class*="-cta"], [class*="-btn"]'), 'buttons'],
  [(el) => el.closest('img, figure, video'), 'media']
]

// De un elemento del iframe devuelve el target Studio: 'blk:<id>' para
// bloques (prioridad máxima — son la unidad editable de Distribución),
// una clave semántica o 'sec:<id>' para secciones con ancla.
export function pickTargetFor(el) {
  if (!el || !el.closest) return null
  const blk = el.closest('[data-blk]')
  if (blk?.dataset?.blk) return `blk:${blk.dataset.blk}`
  for (const [rule, target] of PICK_RULES) {
    if (rule(el)) return target
  }
  const sec = el.closest('section[id], footer[id], main[id]')
  if (sec?.id) return `sec:${sec.id}`
  return 'page'
}

export function toolForTarget(target) {
  if (!target) return 'estilos'
  if (target.startsWith('blk:') || target.startsWith('sec:')) return 'distribucion'
  return {
    hero: 'estilos',
    typo: 'tipografia',
    card: 'contenedores',
    'chrome.nav': 'movil',
    buttons: 'colores',
    media: 'estilos',
    page: 'fondo'
  }[target] || 'estilos'
}
