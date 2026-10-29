// Glifos procedurales determinísticos para el contrato `gen:<slug>` del
// diseño con IA. Mismo slug → mismo dibujo, siempre, sin estado ni azar real.
// Se dibuja una formación de 3 a 6 formas sobre una grilla de 3×3 o 4×4,
// con trazo `currentColor` para heredar el color del contenedor.

const VIEW = 24
const STROKE = 1.75
const SLUG_RE = /^[a-z0-9-]{1,24}$/

const DIRECTIONS = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
  [1, 1],
  [1, -1],
  [-1, 1],
  [-1, -1]
]

function hash32(text) {
  let h = 0x811c9dc5
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

// PRNG mulberry32: determinístico a partir del hash del slug.
function rng(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function n(value) {
  return Number(value.toFixed(2))
}

function normalizeSlug(slug) {
  const text = String(slug ?? '')
    .trim()
    .toLowerCase()
    .replace(/^gen:/, '')
  return SLUG_RE.test(text) ? text : 'glifo'
}

// Caminata sobre la grilla desde la celda central: la formación queda
// conectada (se lee como un símbolo, no como puntos sueltos).
function walk(rnd, size, count, minCol = 0) {
  const mid = Math.floor((size - 1) / 2)
  const start = { c: Math.max(mid, minCol), r: mid }
  const cells = [start]
  const seen = new Set([`${start.c},${start.r}`])
  while (cells.length < count) {
    const from = cells[cells.length - 1]
    const options = DIRECTIONS.map(([dc, dr]) => ({ c: from.c + dc, r: from.r + dr })).filter(
      (p) => p.c >= minCol && p.c < size && p.r >= 0 && p.r < size && !seen.has(`${p.c},${p.r}`)
    )
    if (!options.length) break
    const next = options[Math.floor(rnd() * options.length)]
    seen.add(`${next.c},${next.r}`)
    cells.push(next)
  }
  return cells
}

const SHAPES = ['circle', 'square', 'triangle', 'arc', 'dot']

function shapeAt(kind, cx, cy, cell, rnd) {
  const half = cell * 0.31
  switch (kind) {
    case 'square': {
      const s = n(cell * 0.62)
      return `<rect x="${n(cx - s / 2)}" y="${n(cy - s / 2)}" width="${s}" height="${s}" rx="${n(cell * 0.1)}"/>`
    }
    case 'triangle': {
      const dir = Math.floor(rnd() * 4)
      const pts = [
        [cx, cy - half],
        [cx + half, cy + half * 0.8],
        [cx - half, cy + half * 0.8]
      ]
      const rotated = pts.map(([x, y]) => {
        const dx = x - cx
        const dy = y - cy
        const a = (Math.PI / 2) * dir
        return `${n(cx + dx * Math.cos(a) - dy * Math.sin(a))},${n(cy + dx * Math.sin(a) + dy * Math.cos(a))}`
      })
      return `<polygon points="${rotated.join(' ')}"/>`
    }
    case 'arc': {
      const r = n(cell * 0.32)
      const quarter = Math.floor(rnd() * 4)
      const start = -Math.PI / 2 + (Math.PI / 2) * quarter
      const end = start + Math.PI
      return `<path d="M ${n(cx + r * Math.cos(start))} ${n(cy + r * Math.sin(start))} A ${r} ${r} 0 0 1 ${n(
        cx + r * Math.cos(end)
      )} ${n(cy + r * Math.sin(end))}"/>`
    }
    case 'dot':
      return `<circle cx="${n(cx)}" cy="${n(cy)}" r="${n(cell * 0.17)}" fill="currentColor" stroke="none"/>`
    default:
      return `<circle cx="${n(cx)}" cy="${n(cy)}" r="${n(cell * 0.32)}"/>`
  }
}

/** Cuerpo interno (sin `<svg>`) del glifo, listo para `v-html` o AppIcon. */
export function proceduralIconBody(slug) {
  const text = normalizeSlug(slug)
  const rnd = rng(hash32(text))
  const size = rnd() < 0.55 ? 3 : 4
  const cell = VIEW / size
  const total = 3 + Math.floor(rnd() * 4)
  const mirrored = size === 3 && rnd() < 0.4
  const mid = Math.floor((size - 1) / 2)

  // Con simetría la formación se construye en la mitad derecha y se refleja:
  // nunca queda en la columna central (donde el reflejo no agregaría formas).
  let cells = mirrored ? walk(rnd, size, Math.ceil(total / 2), mid + 1) : walk(rnd, size, total)
  if (mirrored) {
    const extra = cells
      .map((p) => ({ c: size - 1 - p.c, r: p.r }))
      .filter((p) => !cells.some((q) => q.c === p.c && q.r === p.r))
    cells = cells.concat(extra).slice(0, total)
  }
  if (cells.length < 3) cells = walk(rnd, size, total)

  const parts = cells.map((p, i) => {
    const cx = cell * (p.c + 0.5)
    const cy = cell * (p.r + 0.5)
    // La primera forma es el ancla: siempre una figura cerrada y grande.
    const kind = i === 0 ? (rnd() < 0.5 ? 'circle' : 'square') : SHAPES[Math.floor(rnd() * SHAPES.length)]
    return shapeAt(kind, cx, cy, cell, rnd)
  })

  return parts.join('')
}

/** SVG completo (string) determinístico para el slug dado. */
export function proceduralIcon(slug) {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VIEW} ${VIEW}" fill="none" ` +
    `stroke="currentColor" stroke-width="${STROKE}" stroke-linecap="round" stroke-linejoin="round" ` +
    `aria-hidden="true" focusable="false">${proceduralIconBody(slug)}</svg>`
  )
}

/** Slug válido para el contrato `gen:<slug>` (mismo regex que valida el backend). */
export function isProceduralSlug(slug) {
  return SLUG_RE.test(String(slug ?? '').trim().toLowerCase())
}

export const PROCEDURAL_SLUG_RE = SLUG_RE
