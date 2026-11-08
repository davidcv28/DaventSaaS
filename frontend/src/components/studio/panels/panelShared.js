// Utilidades compartidas por los paneles del Studio: armonías de paleta,
// pares de tipografía recomendados, constructores de fondo y medidores de
// contraste. Lo que sale de acá respeta el contrato cerrado de
// studio/contract.js (charset seguro [A-Za-z0-9 #(),.%\-] para CSS).
import { hslToHex, hexHsl } from '../../../utils/colorTools.js'
import { contrastRatio, fixContrast, textOn, normalizeHex, hexToRgb } from '../../../studio/contract.js'
import { CONTRAST_PAIRS, pairColors } from '../health.js'

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

// ============================================================================
// Tipografía curada por diseño: qué pares y pesos sostiene cada piel.
// TYPO_DESIGN_RULES se indexa por SLUG DE DISEÑO (form.template: slug de
// patrón o plantilla Vue; los estilos heredan la regla de su diseño).
//   block        → pares de FONT_PAIRS que la piel no admite, con el motivo
//                  visible que ve el cliente en el panel.
//   weightFloor  → piso de theme.typography.weightHeading: las pieles de
//                  bloque/condensadas no leen títulos finos.
// Nada se borra del catálogo: solo se deshabilita donde rompe, y un tema ya
// guardado se sigue viendo igual (las reglas limitan la UI, no reescriben).
// ============================================================================
const TYPO_WHY_SERIF = {
  impacto: 'La piel es serif editorial: un grotesque negro la vuelve tosca.',
  calida: 'La redonda no combina con la serif editorial de este diseño.'
}
const TYPO_WHY_SANS = {
  editorial: 'Este diseño es sans de bloque: una serif de título rompe la retícula.',
  clasica: 'La serif clásica no lee bien sobre la piel sans de bloque de este diseño.',
  calida: 'La redonda no combina con la retícula sans de bloque de este diseño.'
}
const TYPO_WHY_CALIDA = {
  calida: 'La redonda no combina con la piel de este diseño.'
}

export const TYPO_DESIGN_RULES = {
  // ---- Serif / editorial: la display con carácter es el gesto. 'impacto'
  // queda habilitado en indumentaria (indumentaria-street lo usa de fábrica)
  // y en expediente (su display es grotesque brutalista).
  portico:      { block: TYPO_WHY_SERIF },
  aurum:        { block: TYPO_WHY_SERIF },
  modista:      { block: TYPO_WHY_SERIF },
  viajero:      { block: TYPO_WHY_SERIF },
  olivium:      { block: TYPO_WHY_SERIF },
  moda:         { block: TYPO_WHY_SERIF },
  'atelier-noir': { block: TYPO_WHY_SERIF },
  ruta:         { block: TYPO_WHY_SERIF },
  sastreria:    { block: TYPO_WHY_SERIF },
  indumentaria: { block: TYPO_WHY_CALIDA },
  expediente:   { block: TYPO_WHY_CALIDA },
  // ---- Sans de bloque / tecnología / retail: la serif rompe la retícula.
  // weightFloor sube el piso del grosor según lo pesada que sea la piel.
  mercado:      { block: TYPO_WHY_SANS, weightFloor: 400 },
  gimnasio:     { block: TYPO_WHY_SANS, weightFloor: 600 },
  moderntec:    { block: TYPO_WHY_SANS, weightFloor: 500 },
  impacto:      { block: TYPO_WHY_SANS, weightFloor: 400 },
  silicio:      { block: TYPO_WHY_SANS, weightFloor: 500 },
  showroom:     { block: TYPO_WHY_SANS, weightFloor: 600 },
  calzado:      { block: TYPO_WHY_SANS, weightFloor: 500 },
  topmodern:    { block: TYPO_WHY_SANS, weightFloor: 600 },
  guardia:      { block: TYPO_WHY_SANS, weightFloor: 600 },
  brigada:      { block: TYPO_WHY_SANS, weightFloor: 600 },
  neon:         { block: TYPO_WHY_CALIDA, weightFloor: 500 },
  movimiento:   { block: TYPO_WHY_CALIDA, weightFloor: 400 }
}

// Regla tipográfica del diseño activo (null = diseño neutro: nada se bloquea).
export function typoDesignRule(templateSlug) {
  return TYPO_DESIGN_RULES[templateSlug] || null
}

// Motivo por el que un par de FONT_PAIRS no se puede aplicar en el diseño
// (null = se puede aplicar).
export function pairBlockReason(pair, rule) {
  return rule?.block?.[pair?.id] || null
}

// Pesos reales de cada fuente del catálogo (espejo de las queries wght@ de
// stores.api.js). min/max en pasos de 100; min === max = un solo peso.
export const FONT_WEIGHT_LIMITS = {
  'bebas-neue':        { min: 400, max: 400 },
  'anton':             { min: 400, max: 400 },
  'archivo-black':     { min: 400, max: 400 },
  'righteous':         { min: 400, max: 400 },
  'pacifico':          { min: 400, max: 400 },
  'lobster':           { min: 400, max: 400 },
  'dm-serif-display':  { min: 400, max: 400 },
  'italiana':          { min: 400, max: 400 },
  'orbitron':          { min: 500, max: 900 },
  'inter-tight':       { min: 500, max: 700 },
  'space-grotesk':     { min: 400, max: 700 },
  'lora':              { min: 400, max: 700 },
  'dancing-script':    { min: 400, max: 700 },
  'caveat':            { min: 400, max: 700 },
  'quicksand':         { min: 400, max: 700 },
  'comfortaa':         { min: 400, max: 700 },
  'jost':              { min: 400, max: 700 },
  'figtree':           { min: 400, max: 700 },
  'source-serif-4':    { min: 400, max: 700 },
  'cormorant-garamond':{ min: 400, max: 700 },
  'oswald':            { min: 400, max: 700 },
  'space-mono':        { min: 400, max: 700 },
  'libre-baskerville': { min: 400, max: 700 },
  'instrument-sans':   { min: 400, max: 700 },
  'open-sans':         { min: 400, max: 800 },
  'montserrat':        { min: 400, max: 800 },
  'raleway':           { min: 400, max: 800 },
  'nunito':            { min: 400, max: 800 },
  'work-sans':         { min: 400, max: 800 },
  'dm-sans':           { min: 400, max: 800 },
  'sora':              { min: 400, max: 800 },
  'rubik':             { min: 400, max: 800 },
  'playfair-display':  { min: 400, max: 800 },
  'merriweather':      { min: 400, max: 800 },
  'cinzel':            { min: 400, max: 800 },
  'jetbrains-mono':    { min: 400, max: 800 },
  'manrope':           { min: 400, max: 800 },
  'hanken-grotesk':    { min: 400, max: 800 },
  'barlow':            { min: 400, max: 800 },
  'barlow-condensed':  { min: 400, max: 800 },
  'bricolage-grotesque': { min: 400, max: 800 },
  'poppins':           { min: 400, max: 800 },
  'plus-jakarta-sans': { min: 300, max: 800 },
  'archivo':           { min: 400, max: 900 },
  'roboto':            { min: 400, max: 900 },
  'lato':              { min: 400, max: 900 }
}

// Rango efectivo de weightHeading para un diseño+fuente: piso de la piel ∩
// pesos que la fuente realmente tiene. Devuelve {min,max} para el slider.
export function headingWeightRange(rule, headingSlug) {
  const lim = FONT_WEIGHT_LIMITS[headingSlug] || null
  let min = 300
  let max = 900
  if (rule?.weightFloor) min = rule.weightFloor
  if (lim) {
    min = Math.max(min, lim.min)
    max = Math.min(max, lim.max)
  }
  if (min > max) {
    min = lim?.min ?? min
    max = min
  }
  return { min, max }
}

// Nota visible cuando la combinación guardada/elegida no existe o la piel
// pide más peso del que tiene el control (null = todo en rango).
export function weightRangeNote(rule, headingSlug, current) {
  const lim = FONT_WEIGHT_LIMITS[headingSlug] || null
  const w = Number(current)
  if (lim && lim.min === lim.max && Number.isFinite(w)) {
    return w === lim.min
      ? null
      : `Esta fuente solo existe en peso ${lim.min}: el grosor elegido (${w}) no existe.`
  }
  const { min, max } = headingWeightRange(rule, headingSlug)
  if (!Number.isFinite(w) || (w >= min && w <= max)) return null
  if (rule?.weightFloor && w < rule.weightFloor) {
    return `Los títulos de este diseño no bajan de ${rule.weightFloor}: más fino rompe la piel de bloque.`
  }
  return `El peso ${w} no existe en esta fuente${lim ? ` (rango ${lim.min}–${lim.max})` : ''}; la web lo ajusta al más cercano.`
}

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

// Medidores de contraste AA. Los pares y umbrales viven en health.js (una
// sola fuente de verdad): el panel Colores y "Salud" nunca pueden decir
// cosas distintas sobre la misma paleta.
export { CONTRAST_PAIRS, palettePasses, repairPalette } from '../health.js'

export function contrastChecks(p) {
  return CONTRAST_PAIRS.map((pair) => {
    const { fg, bg } = pairColors(pair, p)
    return { key: pair.key, label: pair.label, min: pair.min, fg, bg, fix: pair.role || 'primary' }
  })
}
