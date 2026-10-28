// Utilidades compartidas por los paneles del Studio: armonías de paleta,
// pares de tipografía recomendados, constructores de fondo y medidores de
// contraste. Lo que sale de acá respeta el contrato cerrado de
// studio/contract.js (charset seguro [A-Za-z0-9 #(),.%\-] para CSS).
import { hslToHex, hexHsl } from '../../../utils/colorTools.js'
import { contrastRatio, fixContrast, textOn, normalizeHex, hexToRgb } from '../../../studio/contract.js'

export { contrastRatio, fixContrast, textOn, normalizeHex, hexToRgb, hslToHex, hexHsl }

export function hexToHsl(hex) {
  const [h, s, l] = hexHsl(normalizeHex(hex) || '#888888')
  return { h, s, l }
}

const shiftHue = (hex, deg) => {
  const { h, s, l } = hexToHsl(hex)
  return hslToHex((h + deg + 360) % 360, s, l)
}

// Generador de paleta desde 1 color. secondary = segundo color de marca
// (los degradados usan primary -> secondary). Devuelve la paleta completa
// por rol + la tira de tonos generados para la vista previa.
export const HARMONIES = [
  { id: 'analogous', label: 'Análoga', hint: 'Tonos vecinos: armónica y tranquila.' },
  { id: 'complementary', label: 'Complementaria', hint: 'Contraste fuerte entre dos polos.' },
  { id: 'triadic', label: 'Triádica', hint: 'Tres colores equilibrados y vivos.' }
]

const HARMONY_STOPS = { analogous: [30, -30], complementary: [180, 30], triadic: [120, 240] }

export function harmonyPalette(baseHex, mode = 'analogous', dark = false) {
  const base = normalizeHex(baseHex) || '#6366f1'
  const [d1, d2] = HARMONY_STOPS[mode] || HARMONY_STOPS.analogous
  const partner = shiftHue(base, d1)
  const third = shiftHue(base, d2)
  const { h, s } = hexToHsl(base)
  const bg = dark ? hslToHex(h, Math.min(s, 0.45), 0.085) : hslToHex(h, Math.min(s * 0.4, 0.35), 0.965)
  const surface = dark ? hslToHex(h, Math.min(s, 0.4), 0.13) : '#ffffff'
  const accent = fixContrast(base, bg, 3)
  return {
    palette: {
      primary: accent,
      secondary: fixContrast(partner, bg, 3),
      accent,
      bg,
      surface,
      text: dark ? '#f1f5fb' : '#0f172a',
      muted: dark ? '#94a0b8' : '#5b6678',
      border: dark ? hslToHex(h, 0.3, 0.22) : '#e2e6f0',
      success: dark ? '#34d399' : '#059669',
      danger: dark ? '#f87171' : '#dc2626'
    },
    tones: [accent, fixContrast(partner, bg, 3), fixContrast(third, bg, 3)]
  }
}

// Pares recomendados título+cuerpo (slugs del catálogo STORE_FONTS).
export const FONT_PAIRS = [
  { id: 'editorial', heading: 'fraunces', body: 'work-sans', label: 'Editorial', hint: 'Titular con carácter, cuerpo moderno.' },
  { id: 'clasica', heading: 'playfair-display', body: 'inter', label: 'Clásica', hint: 'Elegante y legible.' },
  { id: 'moderna', heading: 'sora', body: 'space-grotesk', label: 'Moderna', hint: 'Geométrica y con aire tech.' },
  { id: 'impacto', heading: 'archivo-black', body: 'archivo', label: 'Impacto', hint: 'Pesada y directa.' },
  { id: 'calida', heading: 'comfortaa', body: 'nunito', label: 'Cálida', hint: 'Redonda y cercana.' },
  { id: 'prolija', heading: 'bricolage-grotesque', body: 'figtree', label: 'Prolija', hint: 'Fresca y ordenada.' }
]

// Fondos: `background.value` dentro del charset que whitelistea el backend.
// Las imágenes viajan como URL pura de la tienda (nunca url()).
export function buildGradient(stops, angle = 135) {
  const clean = (stops || []).filter((s) => s && s.color)
  if (clean.length < 2) return null
  const parts = clean.map((s) => `${normalizeHex(s.color)} ${Math.round(s.pos)}%`)
  return `linear-gradient(${Math.round(angle)}deg, ${parts.join(', ')})`
}

export const MESH_LOOKS = [
  { id: 'aurora', label: 'Aurora' },
  { id: 'sunset', label: 'Atardecer' },
  { id: 'ocean', label: 'Océano' }
]

const rgba = (hex, al) => {
  const [r, g, b] = hexToRgb(normalizeHex(hex) || '#6366f1')
  return `rgba(${r},${g},${b},.${al})`
}

export function buildMesh(kind, accentHex, bgHex) {
  const partner = shiftHue(accentHex || '#6366f1', 120)
  const bg = normalizeHex(bgHex) || '#0d1220'
  const a = (al) => rgba(accentHex, al)
  const p = (al) => rgba(partner, al)
  if (kind === 'sunset') {
    return `radial-gradient(60% 50% at 15% 0%, ${a(30)}, transparent 70%), radial-gradient(50% 45% at 85% 10%, ${p(28)}, transparent 72%), ${bg}`
  }
  if (kind === 'ocean') {
    return `radial-gradient(55% 50% at 80% 0%, ${a(26)}, transparent 70%), radial-gradient(60% 55% at 12% 100%, ${p(24)}, transparent 75%), ${bg}`
  }
  return `radial-gradient(60% 50% at 18% 0%, ${a(28)}, transparent 70%), radial-gradient(55% 45% at 85% 8%, ${p(26)}, transparent 72%), ${bg}`
}

export const PATTERN_LOOKS = [
  { id: 'dots', label: 'Puntos' },
  { id: 'lines', label: 'Líneas' },
  { id: 'grid', label: 'Grilla' }
]

export function buildPattern(kind, inkHex, bgHex) {
  const dot = rgba(inkHex || '#0f172a', '08')
  const bg = normalizeHex(bgHex) || '#f4f6fb'
  if (kind === 'lines') {
    return `repeating-linear-gradient(45deg, ${dot} 0px, ${dot} 1px, transparent 1px, transparent 14px), ${bg}`
  }
  if (kind === 'grid') {
    return `repeating-linear-gradient(0deg, ${dot} 0px, ${dot} 1px, transparent 1px, transparent 22px), repeating-linear-gradient(90deg, ${dot} 0px, ${dot} 1px, transparent 1px, transparent 22px), ${bg}`
  }
  return `radial-gradient(${dot} 1.5px, transparent 2px), ${bg}`
}

// Parseo best-effort de un linear-gradient guardado para reabrir el editor.
export function parseGradient(value) {
  if (!value || !value.startsWith('linear-gradient')) return null
  const m = value.match(/^linear-gradient\(\s*(\d+)deg\s*,\s*(.+)\)$/i)
  if (!m) return null
  const stops = []
  const re = /(#[0-9a-fA-F]{6})\s+(\d+(?:\.\d+)?)%/g
  let mm
  while ((mm = re.exec(m[2]))) stops.push({ color: mm[1].toLowerCase(), pos: Number(mm[2]) })
  return stops.length >= 2 ? { angle: Number(m[1]), stops } : null
}

// Medidores de contraste AA (texto 4.5:1, textos grandes/UI 3:1).
export function contrastChecks(p) {
  return [
    { key: 'text-surface', label: 'Texto sobre tarjeta', fg: p.text, bg: p.surface, min: 4.5, fix: 'text' },
    { key: 'text-bg', label: 'Texto sobre el fondo', fg: p.text, bg: p.bg, min: 4.5, fix: 'text' },
    { key: 'muted-bg', label: 'Texto secundario', fg: p.muted, bg: p.bg, min: 3, fix: 'muted' },
    { key: 'accent-surface', label: 'Acento en tarjetas (botones y enlaces)', fg: p.accent, bg: p.surface, min: 4.5, fix: 'accent' },
    { key: 'accent-bg', label: 'Acento sobre el fondo', fg: p.accent, bg: p.bg, min: 3, fix: 'accent' }
  ]
}
