// Template Definitions: un solo registro por diseño que consolida lo que
// antes vivía disperso en tres dispatchers + la tabla de fuentes:
//   - fonts:    fuentes on-demand del diseño (las carga el layout);
//   - surfaces: landing / catalog / product (la página Servicios cuelga de
//               la misma carpeta del diseño);
//   - blocks:   whitelist de bloques por superficie y, en landing, orden
//               canónico por defecto de la portada (la vista lo monta de
//               forma generativa con useLayout; ver abajo).
//
// Catálogo cerrado de 8 diseños, dos por nivel de plan:
//   raiz         (base)     generalista / retail / servicios
//   alimentos    (base)     gastronomía / almacén / panadería
//   trama        (plus)     indumentaria / moda
//   indumentaria (plus)     indumentaria / moda profesional (piel de trama,
//                           composición propia)
//   boutique     (plus)     moda premium / deco / joyería
//   clasico      (plus)     comercio y servicios con oficio (marfil + serif)
//   circuito     (advanced) tecnología / electrónica
//   seguridad    (advanced) seguridad / bomberos / industrial
// El fallback global es 'raiz'. Todo id retirado se remapea con
// STORE_TEMPLATE_RETIRED_MAP (stores.api.js) antes de resolver.
//
// El render de la portada de TODOS los diseños es generativo: cada
// InicioView monta sus secciones desde useLayout('landing') (layout_config
// guardado ∪ patrón de diseño de la base), respetando orden, on/off,
// variante y props de cada bloque. Las tres superficies (landing, catalog,
// services) nacen VACÍAS: el front no declara secciones por defecto; la
// composición la decide el patrón DesignPattern (StoreApp/domains/design) o
// la config guardada de la tienda. La whitelist de ids sigue en
// blocks.js. resolveLayout() fuerza 'contact' al final.

import { defineAsyncComponent } from 'vue'
import { blockSpec, LAYOUT_SURFACES } from './blocks.js'
import { STORE_TEMPLATE_RETIRED_MAP, STORE_TEMPLATES } from '../api/stores.api.js'

import raiz         from './raiz/index.js'
import alimentos    from './alimentos/index.js'
import trama        from './trama/index.js'
import indumentaria from './indumentaria/index.js'
import boutique     from './boutique/index.js'
import clasico      from './clasico/index.js'
import circuito     from './circuito/index.js'
import seguridad    from './seguridad/index.js'

export const TEMPLATE_DEFS = { raiz, alimentos, trama, indumentaria, boutique, clasico, circuito, seguridad }

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

// Las tres superficies de la web nacen VACÍAS: ninguna plantilla declara
// secciones por defecto. La composición sale del patrón DesignPattern de la
// base (layout) o del layout_config guardado por la tienda.
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
      // Si la config no trae variante/props se conserva la firma del default
      // (p.ej. la cinta 'static' de trama): la IA solo pisa lo que elige.
      ...(typeof raw.variant === 'string' && raw.variant ? { variant: raw.variant } : {}),
      ...(raw.props && typeof raw.props === 'object' ? { props: raw.props } : {})
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
