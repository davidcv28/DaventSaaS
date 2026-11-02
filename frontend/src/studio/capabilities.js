// ============================================================================
// Capacidades del DesignStyle activo — qué opciones del Studio ofrece cada
// diseño. Espejo de clean_style_capabilities del backend
// (StoreApp/domains/design/models.py):
//   capabilities = { seccion: True | False | [ids soportados] }
// Ausente/vacío = el estilo soporta TODO (los estilos sin el campo se ven
// idénticos a hoy: ninguna opción se oculta).
// ============================================================================

const CAP_KEYS = {
  palette: 'bool',
  typography: ['heading', 'subheading', 'body', 'scale', 'weightHeading', 'letterSpacing'],
  containers: ['radius', 'shadow', 'border', 'density', 'surface'],
  buttons: ['shape', 'style', 'size'],
  background: ['solid', 'gradient', 'mesh', 'pattern', 'image', 'overlay'],
  motion: ['reveal', 'hover', 'intensity'],
  mobile: ['nav', 'gridCols', 'cardStyle', 'heroHeight', 'stickyCta'],
  icons: 'bool',
  images: ['logo', 'focus', 'overlay', 'filters'],
  decorations: 'bool'
}

// Estilo (o preset mapeado) -> mapa normalizado de capacidades.
// null/{} = todo soportado. Devuelve el dict saneado (sección -> true|false|[ids]).
export function resolveCapabilities(style) {
  const raw = style && typeof style === 'object' ? style.capabilities : null
  if (!raw || typeof raw !== 'object' || !Object.keys(raw).length) return {}
  const out = {}
  for (const [section, spec] of Object.entries(CAP_KEYS)) {
    const value = raw[section]
    if (value === true) { out[section] = true; continue }
    if (spec === 'bool') { if (value === false) out[section] = false; continue }
    if (Array.isArray(value)) out[section] = value.filter((v) => spec.includes(v))
  }
  return out
}

// ¿La sección existe para este estilo? Sin mapa (o sin la clave) = sí.
// Una lista vacía = la sección no ofrece nada.
export function capSection(caps, section) {
  const value = caps?.[section]
  if (value === undefined) return true
  if (Array.isArray(value)) return value.length > 0
  return value === true
}

// ¿La opción `id` de la sección está soportada? Sección bool: true/false
// deciden entera; lista: solo los ids declarados.
export function capOption(caps, section, id) {
  const value = caps?.[section]
  if (value === undefined) return true
  if (Array.isArray(value)) return value.includes(id)
  return value === true
}

// Filtra un array de opciones [{id}] al subconjunto soportado.
export function capOptions(caps, section, list) {
  return (list || []).filter((o) => capOption(caps, section, o.id))
}
