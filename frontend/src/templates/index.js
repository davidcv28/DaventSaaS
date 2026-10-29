// Template Definitions: un solo registro por diseño que consolida lo que
// antes vivía disperso en tres dispatchers + la tabla de fuentes:
//   - fonts:    fuentes on-demand del diseño (las carga el layout);
//   - surfaces: landing / catalog / product (la página Servicios cuelga de
//               la misma carpeta del diseño);
//   - blocks:   whitelist de bloques por superficie. Los 3 diseños son
//               composiciones FIJAS: el orden canónico lo pone la vista, no
//               layout_config (que se sigue aceptando por compatibilidad).
//
// Catálogo cerrado de 3 diseños, uno por rubro y nivel de plan:
//   raiz     (base)     generalista / retail / servicios
//   trama    (plus)     indumentaria / moda
//   circuito (advanced) tecnología / electrónica
// El fallback global es 'raiz'. Todo id retirado se remapea con
// STORE_TEMPLATE_RETIRED_MAP (stores.api.js) antes de resolver.
//
// resolveLayout() se conserva para el Studio de bloques (compatibilidad):
// mezcla el layout por defecto con customization.layout_config, descarta ids
// desconocidos y fuerza contacto al final — el render público de estos 3
// diseños NO lo usa.

import { defineAsyncComponent } from 'vue'
import { blockSpec } from './blocks.js'
import { SECTION_ORDER_KEYS, STORE_TEMPLATE_RETIRED_MAP, STORE_TEMPLATES } from '../api/stores.api.js'

import raiz     from './raiz/index.js'
import trama    from './trama/index.js'
import circuito from './circuito/index.js'

export const TEMPLATE_DEFS = { raiz, trama, circuito }

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

// Un id retirado (payload viejo, borrador corrupto) se remapea antes de
// resolver: nunca queda una superficie vacía.
export function templateOf(value) {
  const normalized = STORE_TEMPLATE_RETIRED_MAP[value] || value
  return TEMPLATE_DEFS[normalized] ? normalized : DEFAULT_TEMPLATE
}

// Layout por defecto de una superficie: la lista declarativa de la plantilla.
export function defaultLayout(id, surface) {
  const def = templateDef(templateOf(id))
  let supported = def.blocks?.[surface] || []
  if (surface === 'landing' && def.usesSectionOrder) {
    const ordered = SECTION_ORDER_KEYS.filter((k) => supported.includes(k))
    const fixed = supported.filter((k) => !SECTION_ORDER_KEYS.includes(k))
    const head = fixed.filter((k) => ['hero', 'categories', 'highlights', 'featured', 'announcements'].includes(k))
    const tail = fixed.filter((k) => !head.includes(k) && k !== 'contact')
    supported = [...head, ...ordered, ...tail, ...(supported.includes('contact') ? ['contact'] : [])]
  }
  return supported.map((blockId, i) => ({ id: blockId, enabled: true, order: i }))
}

// Layout efectivo (Studio): default ∪ config guardada.
export function resolveLayout(id, surface, layoutConfig) {
  const base = defaultLayout(id, surface)
  const byId = new Map(base.map((b) => [b.id, b]))
  const saved = Array.isArray(layoutConfig?.[surface]?.blocks) ? layoutConfig[surface].blocks : []
  const savedById = new Map()
  for (const raw of saved) {
    if (!raw || typeof raw !== 'object') continue
    const blockId = String(raw.id || '')
    const known = byId.get(blockId) || (blockSpec(surface, blockId) ? { id: blockId } : null)
    if (!known || savedById.has(blockId)) continue
    savedById.set(blockId, {
      ...known,
      enabled: raw.enabled !== false,
      variant: typeof raw.variant === 'string' && raw.variant ? raw.variant : undefined,
      props: raw.props && typeof raw.props === 'object' ? raw.props : undefined
    })
  }
  const orderedSaved = [...savedById.values()].sort((a, b) => {
    const ia = saved.findIndex((r) => r?.id === a.id)
    const ib = saved.findIndex((r) => r?.id === b.id)
    return (typeof saved[ia]?.order === 'number' ? saved[ia].order : ia) - (typeof saved[ib]?.order === 'number' ? saved[ib].order : ib)
  })
  const merged = [...orderedSaved, ...base.filter((b) => !savedById.has(b.id))]
  const contactAt = merged.findIndex((b) => b.id === 'contact')
  if (contactAt >= 0 && contactAt !== merged.length - 1) merged.push(...merged.splice(contactAt, 1))
  return merged.map((block, i) => {
    const spec = blockSpec(surface, block.id)
    return { ...block, order: i, enabled: spec?.locked ? true : block.enabled !== false }
  })
}

// Etiquetas del catálogo para el panel (re-export cómodo).
export const TEMPLATE_LABELS = Object.fromEntries(
  Object.entries(STORE_TEMPLATES).map(([key, meta]) => [key, meta.label])
)
