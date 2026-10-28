// Espejo del contrato del backend (AI_ICONS en AdminApp/domains/stores).
// Los nombres válidos son los del set Lucide bundleado en assets/icons/lucide.
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
  'quote'
]

export const AI_ICON_FALLBACK = 'sparkles'

const ICON_SET = new Set(AI_ICONS)

/** Nombre pelado (sin prefijo `lucide:`) o 'sparkles' si no es un ícono del set. */
export function aiIconName(value) {
  if (typeof value !== 'string') return AI_ICON_FALLBACK
  const name = value.trim().toLowerCase().replace(/^lucide:/, '')
  return ICON_SET.has(name) ? name : AI_ICON_FALLBACK
}

/** Nombre listo para <AppIcon name="...">. */
export function resolveAiIcon(name) {
  return `lucide:${aiIconName(name)}`
}

/** Elección determinista dentro de `pool` (por defecto AI_ICONS) a partir de un seed. */
export function pickAiIcon(seed, pool = AI_ICONS) {
  const list = Array.isArray(pool) ? pool.filter((n) => ICON_SET.has(n)) : []
  if (!list.length) return AI_ICON_FALLBACK
  const text = String(seed ?? '')
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) | 0
  }
  return list[Math.abs(hash) % list.length]
}
