const SAMPLE_SIZE = 56

export function hexToRgb(hex) {
  const h = String(hex).replace('#', '')
  const n = parseInt(h.length === 3 ? h.replace(/./g, '$&$&') : h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export function rgbToHex([r, g, b]) {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`
}

function channel(v) {
  const s = v / 255
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}

export function luminance(hex) {
  const [r, g, b] = hexToRgb(hex)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

export function contrastRatio(a, b) {
  const la = luminance(a)
  const lb = luminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

function saturation([r, g, b]) {
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  return max === 0 ? 0 : (max - min) / max
}

function rgbToLab([r, g, b]) {
  const [lr, lg, lb] = [r, g, b].map(channel)
  const x = (lr * 0.4124 + lg * 0.3576 + lb * 0.1805) / 0.95047
  const y = lr * 0.2126 + lg * 0.7152 + lb * 0.0722
  const z = (lr * 0.0193 + lg * 0.1192 + lb * 0.9505) / 1.08883
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116)
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))]
}

function labDistance(a, b) {
  const la = rgbToLab(a)
  const lb = rgbToLab(b)
  return Math.hypot(la[0] - lb[0], la[1] - lb[1], la[2] - lb[2])
}

export function nearestAccent(rgb, accents) {
  let best = null
  let bestDist = Infinity
  for (const [key, a] of Object.entries(accents)) {
    const d = labDistance(rgb, hexToRgb(a.hex))
    if (d < bestDist) { best = key; bestDist = d }
  }
  return best
}

function loadImage(src, cors) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    if (cors) img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('image'))
    img.src = src
  })
}
export function quantizeColors(data, max = 5) {
  const buckets = new Map()
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 128) continue
    const key = ((data[i] >> 4) << 8) | ((data[i + 1] >> 4) << 4) | (data[i + 2] >> 4)
    const b = buckets.get(key) || { n: 0, r: 0, g: 0, b: 0 }
    b.n += 1
    b.r += data[i]
    b.g += data[i + 1]
    b.b += data[i + 2]
    buckets.set(key, b)
  }
  const ranked = [...buckets.values()]
    .map((b) => {
      const rgb = [b.r / b.n, b.g / b.n, b.b / b.n]
      const max3 = Math.max(...rgb)
      const min3 = Math.min(...rgb)
      const neutral = max3 > 235 && min3 > 225
      return { rgb, score: b.n * (neutral ? 0.15 : 0.35 + saturation(rgb)) }
    })
    .sort((a, b) => b.score - a.score)
  const picked = []
  for (const c of ranked) {
    if (picked.every((p) => labDistance(p.rgb, c.rgb) > 18)) picked.push(c)
    if (picked.length === max) break
  }
  return picked.map((c) => rgbToHex(c.rgb))
}

export async function extractLogoColors(src, { cors = false, max = 5 } = {}) {
  // Los logos guardados viven en Cloudflare R2 (pub-*.r2.dev). Ese bucket no
  // expone Access-Control-Allow-Origin: pedir la imagen con crossOrigin
  // 'anonymous' la bloquea por CORS (ERR_FAILED + ruido en consola) y el
  // canvas queda tainted igual. Sin crossOrigin la imagen carga y solo falla
  // el getImageData — se degrada a [] (paleta por defecto) sin error de red.
  const img = await loadImage(src, cors)
  const scale = Math.min(1, SAMPLE_SIZE / Math.max(img.naturalWidth, img.naturalHeight, 1))
  const w = Math.max(1, Math.round(img.naturalWidth * scale))
  const h = Math.max(1, Math.round(img.naturalHeight * scale))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.drawImage(img, 0, 0, w, h)
  let data
  try {
    data = ctx.getImageData(0, 0, w, h).data
  } catch {
    // Canvas tainted (imagen remota sin CORS en el bucket): no hay forma de
    // leer píxeles. Devolver [] deja que la UI use la paleta por defecto.
    return []
  }
  return quantizeColors(data, max)
}

const PAGE_BG = { light: '#f4f6fb', dark: '#0d1220' }

export const isHex = (v) => /^#[0-9a-fA-F]{6}$/.test(String(v || ''))

export function normalizeHex(value) {
  let h = String(value || '').trim().replace(/^#/, '').toLowerCase()
  if (/^[0-9a-f]{3}$/.test(h)) h = h.replace(/./g, '$&$&')
  return /^[0-9a-f]{6}$/.test(h) ? `#${h}` : ''
}

export function rgbToHsl([r, g, b]) {
  const [x, y, z] = [r / 255, g / 255, b / 255]
  const max = Math.max(x, y, z)
  const min = Math.min(x, y, z)
  const l = (max + min) / 2
  if (max === min) return [0, 0, l]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  const h = max === x ? (y - z) / d + (y < z ? 6 : 0) : max === y ? (z - x) / d + 2 : (x - y) / d + 4
  return [h * 60, s, l]
}

export function hslToHex(h, s, l) {
  const a = s * Math.min(l, 1 - l)
  const f = (n) => {
    const k = (n + h / 30) % 12
    return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
  }
  return rgbToHex([f(0) * 255, f(8) * 255, f(4) * 255])
}

export function hexHsl(hex) {
  return rgbToHsl(hexToRgb(hex))
}

export function deriveAccent(hex) {
  const [h, s, l] = hexHsl(hex)
  let il = Math.max(0.08, l - 0.07)
  let ink = hslToHex(h, s, il)
  while (contrastRatio('#ffffff', ink) < 4.5 && il > 0.05) {
    il -= 0.02
    ink = hslToHex(h, s, il)
  }
  return { hex: hex.toLowerCase(), ink, soft: hslToHex(h, Math.min(s, 0.9), 0.96) }
}

const mixHex = (a, b, t) => rgbToHex(hexToRgb(a).map((c, i) => c + (hexToRgb(b)[i] - c) * t))

// Aclara `hex` (mismo tono) hasta cumplir `min` contra un fondo oscuro.
function onDark(hex, bg = '#0d1220', min = 3) {
  if (contrastRatio(hex, bg) >= min) return hex
  const [h, s, l0] = hexHsl(hex)
  for (let l = Math.max(l0, 0.02); l <= 1; l += 0.02) {
    const c = hslToHex(h, s, l)
    if (contrastRatio(c, bg) >= min) return c
  }
  return '#ffffff'
}

// Colores de una banda de acento (hero, inicial, placas) SIEMPRE legibles con
// texto blanco: si el acento es claro (amarillo, celeste, lima) se usa su
// tinta oscurecida como base. Devuelve tonos del mismo lado de la escala para
// que el nombre de la empresa no desaparezca sobre el fondo.
export function bandPalette(accentHex) {
  const hex = isHex(accentHex) ? accentHex.toLowerCase() : '#4f46e5'
  const safe = contrastRatio('#ffffff', hex) >= 4.5 ? hex : deriveAccent(hex).ink
  return {
    c1: safe,
    c2: mixHex(safe, '#000000', 0.22),
    c3: mixHex(safe, '#000000', 0.1),
    c4: mixHex(safe, '#000000', 0.42),
    base1: safe,
    base2: mixHex(safe, '#000000', 0.28),
    // Acento para texto sobre el velo oscuro de una portada (última palabra
    // del nombre en los dise�os retirados): se aclara hasta 3:1 (texto
    // grande) si el acento es oscuro.
    mark: onDark(safe)
  }
}

// Oscurece `hex` (mismo tono) hasta cumplir `min` contra un fondo claro.
function onLight(hex, bg = '#ffffff', min = 4.5) {
  if (contrastRatio(hex, bg) >= min) return hex
  const [h, s, l0] = hexHsl(hex)
  for (let l = Math.min(l0, 0.98); l >= 0; l -= 0.02) {
    const c = hslToHex(h, s, l)
    if (contrastRatio(c, bg) >= min) return c
  }
  return '#000000'
}

// Paleta coherente para el modo pedido. Devuelve null si la paleta ya está
// en ese modo. Al cambiar claro/oscuro el Studio reescribe la paleta (no la
// deja clara con fondo blanco sobre una página nocturna).
export function adaptPalette(palette, mode) {
  const p = palette || {}
  const hex = (v, f) => (isHex(v) ? v.toLowerCase() : f)
  const surface = hex(p.surface, '#ffffff')
  const isDark = luminance(surface) < 0.5
  if ((mode === 'dark') === isDark) return null
  const bg = hex(p.bg, '#f4f6fb')
  const accent = hex(p.accent || p.primary, '#4f46e5')
  const [h, s] = hexHsl(bg)
  if (mode === 'dark') {
    const surfaceDark = hslToHex(h, Math.min(s, 0.4), 0.11)
    const accentDark = onDark(accent, surfaceDark, 4.5)
    return {
      bg: hslToHex(h, Math.min(s, 0.45), 0.07),
      surface: surfaceDark,
      text: '#f1f5fb',
      muted: hslToHex(h, Math.min(s, 0.2), 0.68),
      border: hslToHex(h, Math.min(s, 0.3), 0.22),
      primary: accentDark,
      accent: accentDark,
      secondary: deriveAccent(accentDark).ink
    }
  }
  const surfaceLight = '#ffffff'
  const accentLight = onLight(accent, surfaceLight, 4.5)
  return {
    bg: hslToHex(h, Math.min(s * 0.4, 0.35), 0.965),
    surface: surfaceLight,
    text: '#0f172a',
    muted: '#5b6678',
    border: hslToHex(h, Math.min(s, 0.3), 0.88),
    primary: accentLight,
    accent: accentLight,
    secondary: deriveAccent(accentLight).ink
  }
}

export function fixAccent(hex, theme = 'light') {
  const bg = PAGE_BG[theme] || PAGE_BG.light
  const [h, s, l0] = hexHsl(hex)
  const dir = theme === 'dark' ? 1 : -1
  let l = l0
  let cur = hex.toLowerCase()
  for (let i = 0; i < 60 && contrastRatio(cur, bg) < 3 && l > 0.04 && l < 0.96; i += 1) {
    l += dir * 0.02
    cur = hslToHex(h, s, l)
  }
  return { hex: cur, changed: cur !== hex.toLowerCase() }
}

export function harmonicAccent(currentHex, theme = 'light') {
  const [h, s] = hexHsl(currentHex || '#4f46e5')
  const turn = [30, 150, 180, 210][Math.floor(Math.random() * 4)]
  const sat = Math.min(0.8, Math.max(0.5, s + (Math.random() - 0.5) * 0.2))
  const light = 0.36 + Math.random() * 0.12
  return fixAccent(hslToHex((h + turn) % 360, sat, light), theme).hex
}
