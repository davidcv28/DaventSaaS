// Espejo del contrato del backend (AI_ICONS en AdminApp/domains/stores):
// esta lista es la ÚNICA fuente de verdad del frontend y debe coincidir
// nombre por nombre con la del backend. Los íconos son del set Lucide (ISC)
// bundleado en assets/icons/lucide; cuando el concepto no existe en el set,
// el backend manda `gen:<slug>` y se dibuja con utils/proceduralIcon.js.
import { h } from 'vue'
import { proceduralIcon, proceduralIconBody } from './proceduralIcon.js'

export const AI_ICONS = [
  'coffee',
  'scissors',
  'heart',
  'star',
  'truck',
  'clock',
  'map-pin',
  'phone',
  'message-circle',
  'mail',
  'package',
  'tag',
  'percent',
  'credit-card',
  'gift',
  'users',
  'building-2',
  'home',
  'wrench',
  'hammer',
  'monitor',
  'smartphone',
  'camera',
  'images',
  'music',
  'book-open',
  'graduation-cap',
  'paw-print',
  'dumbbell',
  'leaf',
  'flower',
  'sun',
  'moon',
  'sparkles',
  'shield-check',
  'check-circle',
  'award',
  'badge-check',
  'calendar',
  'quote',
  'shirt',
  'pizza',
  'cake',
  'car',
  'plane',
  'hotel',
  'key',
  'lock',
  'wallet',
  'receipt',
  'calculator',
  'chart-line',
  'trending-up',
  'globe',
  'wifi',
  'laptop',
  'printer',
  'palette',
  'brush',
  'pen-tool',
  'ruler',
  'layers',
  'grid',
  'box',
  'archive',
  'search',
  'filter',
  'settings',
  'sliders',
  'zap',
  'flame',
  'droplet',
  'wind',
  'snowflake',
  'mountain',
  'tree',
  'sun-medium',
  'thermometer',
  'stethoscope',
  'pill',
  'syringe',
  'activity',
  'baby',
  'dog',
  'cat',
  'bone',
  'apple',
  'carrot',
  'wine',
  'beer',
  'cup-soda',
  'utensils',
  'chef-hat',
  'store',
  'shopping-bag',
  'shopping-cart',
  'ticket',
  'qr-code',
  'scan-line',
  'headphones',
  'speaker',
  'video',
  'film',
  'mic',
  'radio',
  'tv',
  'gamepad',
  'puzzle',
  'trophy',
  'medal',
  'target',
  'flag',
  'compass',
  'anchor',
  'route',
  'bike',
  'bus',
  'train',
  'fuel',
  'parking',
  'warehouse',
  'factory',
  'briefcase',
  'handshake',
  'id-card',
  'file-text',
  'folder',
  'database',
  'server',
  'cpu',
  'code',
  'terminal'

]

export const AI_ICON_FALLBACK = 'lucide:sparkles'

const ICON_SET = new Set(AI_ICONS)

const GEN_RE = /^gen:[a-z0-9-]{1,24}$/

/** Normaliza a `lucide:<name>` | `gen:<slug>` | `lucide:sparkles`. */
export function resolveAiIcon(value) {
  if (typeof value !== 'string') return AI_ICON_FALLBACK
  const raw = value.trim().toLowerCase()
  if (GEN_RE.test(raw)) return raw
  const name = raw.replace(/^lucide:/, '')
  return ICON_SET.has(name) ? `lucide:${name}` : AI_ICON_FALLBACK
}

/** Nombre pelado (sin prefijo) o `gen:<slug>`; `sparkles` si no es válido. */
export function aiIconName(value) {
  const resolved = resolveAiIcon(value)
  if (resolved.startsWith('gen:')) return resolved
  return resolved.slice('lucide:'.length)
}

/** Elección determinista dentro de `pool` (por defecto AI_ICONS) a partir de un seed. */
export function pickAiIcon(seed, pool = AI_ICONS) {
  const list = (Array.isArray(pool) ? pool : []).map(resolveAiIcon).filter((n) => n !== AI_ICON_FALLBACK)
  const items = list.length ? list : AI_ICONS.map((n) => `lucide:${n}`)
  const text = String(seed ?? '')
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) | 0
  }
  return items[Math.abs(hash) % items.length]
}

// Compat con los bloques solo-IA (AiGlyph): componente de tamaño controlado
// para los `gen:<slug>`; `proceduralIcon` sigue siendo la salida en string.
export function renderProceduralIcon(slug) {
  const body = proceduralIconBody(slug)
  return {
    name: 'ProceduralIcon',
    props: { size: { type: [Number, String], default: 20 } },
    setup(props) {
      return () =>
        h('svg', {
          width: props.size,
          height: props.size,
          viewBox: '0 0 24 24',
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': 1.75,
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'aria-hidden': 'true',
          focusable: 'false',
          innerHTML: body
        })
    }
  }
}

export { proceduralIcon, proceduralIconBody }
