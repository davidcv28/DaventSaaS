// Utilidades del catálogo de estilos del Studio.
//
// Los presets ya NO viven acá: son registros del dominio design
// (StoreApp/domains/design) y llegan por `GET /api/design/catalog/`
// (ver composables/useDesignCatalog.js). Este módulo solo conserva la
// lógica pura que el shell y la galería necesitan: expansión del layout
// compacto, lock por plan, filtros y fuentes on-demand.
import { defaultLayout } from '../../templates/index.js'
import { blockSpec } from '../../templates/blocks.js'
import { STORE_FONTS, STORE_TEMPLATES } from '../../api/stores.api.js'
import { STUDIO_SURFACES } from '../contract.js'

// Compatibilidad: sin presets locales. La galería usa los de la API.
export const STUDIO_PRESETS = []

// ---------------------------------------------------------------------------
// Spec compacto -> layout_config del contrato.
// ---------------------------------------------------------------------------
export function buildLayout(templateId, spec = {}) {
  const out = {}
  for (const surface of STUDIO_SURFACES) {
    const base = defaultLayout(templateId, surface)
    const s = spec[surface] || {}
    const byId = new Map(base.map((b) => [b.id, b]))
    const ordered = []
    const seen = new Set()
    // ids pedidos por el preset (aunque la plantilla no los soporte)
    const on = Array.isArray(s.on) ? s.on : null
    const listed = new Set(on || [])
    for (const id of on || base.map((b) => b.id)) {
      const b = byId.get(id)
      if (b && !seen.has(id)) { seen.add(id); ordered.push(b) }
    }
    // el resto, en el orden canónico de la plantilla (sin repetir ids)
    for (const b of base) if (!seen.has(b.id)) { seen.add(b.id); ordered.push(b) }
    const off = new Set(s.off || [])
    const variants = s.var || {}
    out[surface] = {
      blocks: ordered.map((b, i) => {
        const meta = blockSpec(surface, b.id)
        const enabled = meta?.locked ? true : (on ? listed.has(b.id) : true) && !off.has(b.id)
        const block = { id: b.id, enabled, order: i }
        const v = variants[b.id]
        if (v && meta?.variants?.[v]) block.variant = v
        return block
      })
    }
  }
  return out
}

export const RUBRO_LABELS = {
  ofertas: 'Ofertas', gamer: 'Gamer', general: 'Generalista', belleza: 'Belleza',
  hogar: 'Hogar', lifestyle: 'Lifestyle', moda: 'Indumentaria', tech: 'Tecnología',
  food: 'Comestibles', services: 'Servicios'
}

const RUBRO_KEYWORDS = {
  tech:     ['tecno', 'electro', 'celular', 'comput', 'notebook', 'audio', 'cable', 'cargador', 'smart', 'tablet', 'impresor', 'software', 'hardware', 'informat'],
  gamer:    ['gamer', 'gaming', 'consola', 'videojuego', 'esport', 'playstation', 'xbox', 'nintendo', 'joystick', 'pc ', 'setup'],
  moda:     ['ropa', 'indumentaria', 'remera', 'zapatilla', 'calzado', 'vestido', 'jean', 'moda', 'accesorio', 'cartera', 'zapato', 'buzo', 'campera', 'lenceria'],
  belleza:  ['belleza', 'cosmet', 'peluquer', 'unas', 'maquill', 'estet', 'skin', 'perfume', 'cabello', 'barber', 'spa', 'nails', 'pestan'],
  food:     ['comida', 'alimento', 'gourmet', 'dulce', 'panific', 'cafe', 'resto', 'bebida', 'vino', 'queso', 'pizza', 'empanada', 'helado', 'pasteler', 'gastron', 'cerveza', 'te ', 'mate'],
  hogar:    ['hogar', 'deco', 'mueble', 'ilumin', 'jardin', 'textil', 'vajilla', 'aroma', 'vela', 'cocina', 'blanqueria', 'cortina'],
  services: ['servicio', 'reparac', 'consultor', 'diseno', 'gestion', 'asesor', 'estudio', 'abogad', 'contad', 'taller', 'electric', 'plomer', 'flete', 'limpieza'],
  ofertas:  ['oferta', 'outlet', 'liquidac', 'mayor', 'descuent', 'regal', 'bazaar', 'bazar', 'variedades'],
  lifestyle:['libreria', 'regal', 'joya', 'reloj', 'arte', 'foto', 'mascota', 'plantas', 'deporte', 'fitness', 'gym', 'yoga']
}

// Un solo paso sobre todo el texto disponible (sin rubro explícito en el
// modelo, así que se infiere del negocio + categorías del catálogo).
export function detectRubro({ name = '', headline = '', categories = [] } = {}) {
  const text = [name, headline, ...categories]
    .join(' ').toLowerCase().normalize('NFD').replace(/\p{M}/gu, '')
  let best = null
  let bestScore = 0
  for (const [key, kws] of Object.entries(RUBRO_KEYWORDS)) {
    let score = 0
    for (const kw of kws) if (text.includes(kw)) score += kw.length > 5 ? 2 : 1
    if (score > bestScore) { best = key; bestScore = score }
  }
  return bestScore >= 2 ? best : null
}

export function presetById(id, list = STUDIO_PRESETS) {
  return (list || []).find((p) => p.id === id) || null
}

// Layout del preset re-expandido contra OTRA plantilla (para "Combinar →
// solo la distribución" sobre el diseño que ya tiene la tienda).
export function layoutForTemplate(preset, templateId) {
  return buildLayout(templateId, preset?.layoutSpec || {})
}

// null = persiste completo; 'plan' = la plantilla está por encima del nivel;
// 'theme' = la plantilla alcanza pero el tema completo pide Premium (con
// Plus solo viajan radius/density de containers y nada del resto). Un preset
// de plantilla Base ya se guarda con el plan Básico (style.id + styleColors):
// no pide diseño avanzado.
const TIER_BENEFIT = { base: null, plus: 'has_design_plus', advanced: 'has_design_advanced' }
export function presetLock(preset, benefits = {}) {
  const tier = STORE_TEMPLATES[preset?.template]?.tier || preset?.tier || 'base'
  const need = TIER_BENEFIT[tier]
  if (need && !benefits[need]) return 'plan'
  if (tier !== 'base' && !benefits.has_design_advanced) return 'theme'
  return null
}

// Fuentes del catálogo entero en UN link (mismo patrón que
// ensureStoreFontPicker): las tarjetas se renderizan con su tipografía real.
let presetFontsDone = false
export function ensurePresetFonts(list = STUDIO_PRESETS) {
  if (presetFontsDone) return
  if (!list?.length) return
  presetFontsDone = true
  const googles = new Set()
  for (const p of list) {
    for (const slug of [p.theme?.typography?.heading, p.theme?.typography?.body]) {
      const g = STORE_FONTS[slug]?.google
      if (g) googles.add(g)
    }
  }
  if (!googles.size || typeof document === 'undefined') return
  const link = document.createElement('link')
  link.id = 'preset-fonts'
  link.rel = 'stylesheet'
  link.href = `https://fonts.googleapis.com/css2?${[...googles].sort().map((g) => `family=${g}`).join('&')}&display=swap`
  document.head.appendChild(link)
}

// Filtros de la galería: texto libre (nombre/estilo/rubro), rubro de la
// tienda, dirección de estilo, tier del plan y favoritos.
export function filterPresets(list, { q = '', rubro = '', style = '', tier = '', favs = null, usable = false, benefits = {} } = {}) {
  const needle = q.trim().toLowerCase()
  return (list || []).filter((p) => {
    if (favs && !favs.has(p.id)) return false
    if (tier && p.tier !== tier) return false
    if (style && p.style !== style) return false
    if (rubro && !p.rubros.includes(rubro)) return false
    if (usable && presetLock(p, benefits) !== null) return false
    if (!needle) return true
    const hay = `${p.name} ${p.style} ${p.desc} ${p.rubros.map((r) => RUBRO_LABELS[r] || r).join(' ')}`.toLowerCase()
    return hay.includes(needle)
  })
}
