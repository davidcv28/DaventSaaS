// Template Definitions: un solo registro por plantilla que consolida lo
// que antes vivía disperso en tres dispatchers + la tabla de fuentes:
//   - fonts:    fuentes on-demand del diseño (las carga el layout);
//   - surfaces: landing / catalog / product (la página Servicios es la
//               misma vista para todas las plantillas);
//   - blocks:   whitelist de bloques por superficie cuyo orden declarativo
//               es el layout por defecto (catálogo cerrado en blocks.js,
//               espejo de TEMPLATE_BLOCKS del backend).
//
// Este registro es el SUPERSET de render: el catálogo seleccionable son
// 6 diseños (2 por nivel — STORE_TEMPLATES / TEMPLATE_CHOICES) y los 20
// retirados quedan acá como red de seguridad — una tienda con un diseño
// viejo que no se remapeó (o un draft corrupto) sigue renderizando su
// piel en vez de caer al fallback 'classic'.
//
// resolveLayout() mezcla el layout por defecto con
// customization.layout_config: los bloques guardados mandan en orden y
// estado, los que falten entran al final en su posición canónica y los
// ids desconocidos/no soportados se descartan — así una config corrupta
// nunca rompe la web pública. En la portada las secciones de marketing
// van siempre en su orden fijo (SECTION_ORDER_KEYS).

import { defineAsyncComponent } from 'vue'
import { blockSpec } from './blocks.js'
import { SECTION_ORDER_KEYS } from '../api/stores.api.js'

import classic     from './classic/index.js'
import perspective from './perspective/index.js'
import duo         from './duo/index.js'
import bloque      from './bloque/index.js'
import riso        from './riso/index.js'
import terra       from './terra/index.js'
import street      from './street/index.js'
import atelier     from './atelier/index.js'
import circuit     from './circuit/index.js'
import lab         from './lab/index.js'
import mercado     from './mercado/index.js'
import carta       from './carta/index.js'
import studio      from './studio/index.js'
import proceso     from './proceso/index.js'
import promo       from './promo/index.js'
import shop        from './shop/index.js'
import arena       from './arena/index.js'
import terminal    from './terminal/index.js'
import calma       from './calma/index.js'
import signature   from './signature/index.js'
import vitrina     from './vitrina/index.js'
import lookbook    from './lookbook/index.js'
import cobre       from './cobre/index.js'
import minimal     from './minimal/index.js'
import boutique    from './boutique/index.js'
import aurora      from './aurora/index.js'

export const TEMPLATE_DEFS = {
  classic, perspective, duo, bloque, riso, terra, street, atelier,
  circuit, lab, mercado, carta, studio, proceso, promo, shop, arena,
  terminal, calma, signature, vitrina, lookbook, cobre, minimal,
  boutique, aurora
}

// Sistema de bloques base 'cobre': todas las plantillas montan los mismos
// elementos de landing (StorePublicView + Blk*) pero con su propia piel
// (data-store-template = plantilla real → paleta, fuentes y variantes tpl)
// y su propio arreglo estratégico de bloques (blocks.* por superficie).

export function templateDef(id) {
  return TEMPLATE_DEFS[id] || TEMPLATE_DEFS.classic
}

// Componente async de una superficie (cacheado por plantilla+superficie:
// crear defineAsyncComponent en cada render remontaría la vista).
const _components = new Map()
export function surfaceComponent(id, surface) {
  const key = `${templateDef(id) === TEMPLATE_DEFS[id] ? id : 'classic'}:${surface}`
  if (!_components.has(key)) {
    const loader = templateDef(id).surfaces?.[surface]
    _components.set(key, loader ? defineAsyncComponent(loader) : null)
  }
  return _components.get(key)
}

export function templateFonts(id) {
  return templateDef(id).fonts || []
}

// Layout por defecto de una superficie: la lista declarativa de la
// plantilla (= orden de autoría de la vista). Las plantillas servidas por
// StorePublicView declaran además usesSectionOrder: ahí las secciones de
// marketing van en el orden fijo de SECTION_ORDER_KEYS (hero y bandas
// primero, contacto último).
export function defaultLayout(id, surface) {
  const def = templateDef(id)
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

// Layout efectivo: default ∪ config guardada.
//  - ids soportados que llegan guardados conservan enabled/variant/props
//    y se ordenan entre sí por su order guardado;
//  - ids soportados que faltan en la config entran al final en orden
//    canónico (p.ej. los bloques de una plantilla recién elegida);
//  - los locked quedan siempre habilitados.
export function resolveLayout(id, surface, layoutConfig) {
  const base = defaultLayout(id, surface)
  const byId = new Map(base.map((b) => [b.id, b]))
  const saved = Array.isArray(layoutConfig?.[surface]?.blocks) ? layoutConfig[surface].blocks : []
  const savedById = new Map()
  for (const raw of saved) {
    if (!raw || typeof raw !== 'object') continue
    const base0 = byId.get(raw.id)
    if (!base0 || savedById.has(raw.id)) continue
    savedById.set(raw.id, {
      ...base0,
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
  return merged.map((block, i) => {
    const spec = blockSpec(surface, block.id)
    return { ...block, order: i, enabled: spec?.locked ? true : block.enabled !== false }
  })
}
