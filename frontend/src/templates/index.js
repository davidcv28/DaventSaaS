// Template Definitions: un solo registro por diseño que consolida lo que
// antes vivía disperso en tres dispatchers + la tabla de fuentes:
//   - fonts:    fuentes on-demand del diseño (las carga el layout);
//   - surfaces: landing / catalog / product (la página Servicios cuelga de
//               la misma carpeta del diseño);
//   - blocks:   composición canónica por superficie (la vista monta esos
//               bloques en ese orden; ver templateBlocks/resolveLayout).
//
// Catálogo por rubro: 'raiz' (Esencial) es el base y el fallback global.
// Todo id retirado se remapea con STORE_TEMPLATE_RETIRED_MAP
// (stores.api.js) antes de resolver.
//
// El sistema de bloques se retiró: cada plantilla declara su composición
// única en `blocks.<superficie>` y esa es la que se monta, sin reordenar ni
// apagar nada desde la config de la tienda. La whitelist de ids sigue en
// blocks.js.

import { defineAsyncComponent } from 'vue'
import { LAYOUT_SURFACES } from './blocks.js'
import { STORE_TEMPLATE_RETIRED_MAP, STORE_TEMPLATES, SITE_TEMPLATE_KEYS } from '../api/stores.api.js'

import raiz         from './raiz/index.js'
import mercado      from './mercado/index.js'
import gimnasio     from './gimnasio/index.js'
import sastreria    from './sastreria/index.js'
import moderntec    from './moderntec/index.js'

export const TEMPLATE_DEFS = { raiz, mercado, gimnasio, sastreria, moderntec }

export const DEFAULT_TEMPLATE = 'raiz'

export function templateDef(id) {
  return TEMPLATE_DEFS[id] || TEMPLATE_DEFS[DEFAULT_TEMPLATE]
}

// Componente async de una superficie (cacheado por plantilla+superficie:
// crear defineAsyncComponent en cada render remontaría la vista).
const _components = new Map()
export function surfaceComponent(id, surface) {
  const known = TEMPLATE_DEFS[id] ? id : DEFAULT_TEMPLATE
  const key = `${known}:${surface}`
  if (!_components.has(key)) {
    const loader = templateDef(known).surfaces?.[surface]
    _components.set(key, loader ? defineAsyncComponent(loader) : null)
  }
  return _components.get(key)
}

export function templateFonts(id) {
  return templateDef(id).fonts || []
}

// Páginas (site_templates) que el diseño soporta: la def puede recortar el
// catálogo cerrado con `pages` (Bazar no ofrece Servicios ni Suscripciones);
// sin `pages` se asumen todas. El público y "Qué mostrar" filtran con esto.
export function templatePages(id) {
  const pages = templateDef(id).pages
  return Array.isArray(pages) && pages.length ? pages : SITE_TEMPLATE_KEYS
}

// Un id retirado (payload viejo, borrador corrupto) se remapea antes de
// resolver: nunca queda una superficie vacía.
export function templateOf(value) {
  const normalized = STORE_TEMPLATE_RETIRED_MAP[value] || value
  return TEMPLATE_DEFS[normalized] ? normalized : DEFAULT_TEMPLATE
}

// Sin layout por defecto global: cada plantilla declara el suyo en
// `blocks.<superficie>`.
export function defaultLayout() {
  return []
}

// Layout de un patrón de diseño (DesignPattern.layout / DesignStyle.layout)
// normalizado a la forma de layout_config: {surface: {blocks: [...]}}.
// Acepta tanto el objeto canónico como la lista plana por superficie y
// descarta ids repetidos o inválidos.
export function normalizeLayoutConfig(raw) {
  const out = {}
  if (!raw || typeof raw !== 'object') return out
  for (const surface of LAYOUT_SURFACES) {
    const src = raw[surface]
    const list = Array.isArray(src) ? src : Array.isArray(src?.blocks) ? src.blocks : []
    const seen = new Set()
    const blocks = []
    list.forEach((item, i) => {
      if (!item || typeof item !== 'object' || item.id == null) return
      const id = String(item.id)
      if (!id || seen.has(id)) return
      seen.add(id)
      blocks.push({
        id,
        enabled: item.enabled !== false,
        order: typeof item.order === 'number' ? item.order : i,
        ...(typeof item.variant === 'string' && item.variant ? { variant: item.variant } : {}),
        ...(item.props && typeof item.props === 'object' ? { props: item.props } : {})
      })
    })
    if (!blocks.length) continue
    blocks.sort((a, b) => a.order - b.order)
    out[surface] = { blocks: blocks.map((b, i) => ({ ...b, order: i })) }
  }
  return out
}

// Composición canónica de una superficie: la que declara el DISEÑO en
// `blocks.<superficie>`. `saved` (layout_config de la tienda, ya saneado)
// pisa enabled/variant/props de los bloques declarados — el orden lo fija el
// diseño; un id que el diseño no trae no se agrega acá (los extra de la IA
// los inserta el renderer). Cambiar de diseño descarta los ids ajenos vía
// clean_layout_config del backend.
export function templateBlocks(id, surface, saved = null) {
  const canonical = templateDef(id).blocks?.[surface] || []
  const savedList = Array.isArray(saved?.[surface]?.blocks) ? saved[surface].blocks : []
  const byId = new Map()
  savedList.forEach((raw) => {
    if (raw && raw.id != null && !byId.has(raw.id)) byId.set(String(raw.id), raw)
  })
  return canonical.map((entry, i) => {
    const base = typeof entry === 'string' ? { id: entry } : { ...entry }
    const block = { ...base, order: i, enabled: base.enabled !== false }
    const s = byId.get(block.id)
    if (s) {
      block.enabled = s.enabled !== false
      if (typeof s.variant === 'string' && s.variant) block.variant = s.variant
      if (s.props && typeof s.props === 'object') block.props = s.props
    }
    return block
  })
}

// Estado de un bloque puntual de la composición (variant/props/enabled).
export function templateBlock(id, surface, blockId, saved = null) {
  return templateBlocks(id, surface, saved).find((b) => b.id === blockId) || { id: blockId, enabled: true }
}

export function resolveLayout(id, surface, saved = null) {
  return templateBlocks(id, surface, saved)
}

// Superficies que cubre un patrón de diseño (DesignPattern): las que
// declara en `layout`; si no declara ninguna, hereda las del template base.
export function patternSurfaces(pattern) {
  const declared = Object.keys(normalizeLayoutConfig(pattern?.layout))
  if (declared.length) return declared
  const blocks = templateDef(templateOf(pattern?.template)).blocks || {}
  return LAYOUT_SURFACES.filter((s) => Array.isArray(blocks[s]) && blocks[s].length)
}

// Filtra el catálogo a los patrones que cubren TODAS las páginas activas
// de la tienda (site_templates: 'landing' | 'catalog' | 'services'). Si la
// combinación no tiene ningún diseño compatible devuelve lista vacía y el
// dashboard obliga a elegir otra combinación en "Qué mostrar".
export function patternsForSiteTemplates(patterns, siteTemplates = []) {
  const list = Array.isArray(patterns) ? patterns : []
  const required = LAYOUT_SURFACES.filter((s) => siteTemplates.includes(s))
  if (!required.length) return list
  return list.filter((p) => required.every((s) => patternSurfaces(p).includes(s)))
}

// Etiquetas del catálogo para el panel (re-export cómodo).
export const TEMPLATE_LABELS = Object.fromEntries(
  Object.entries(STORE_TEMPLATES).map(([key, meta]) => [key, meta.label])
)
