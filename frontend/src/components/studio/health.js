// "Salud de tu web" — verificador de calidad del Studio.
// analyzeStudioHealth() es pura: recibe el tema resuelto (borrador), los
// campos publicados del customizer, el layout en borrador y el contenido
// (imágenes, productos, servicios) y devuelve findings con fix opcional.
// Fixes: {kind:'palette'|'theme'|'nav'} — los aplica StudioShell sobre el
// borrador (palette/theme) o navega a la sección dueña (nav).
import {
  contrastRatio, textOn, normalizeHex, hexToRgb, rgbToHex,
  SITE_THEME_DEFAULTS
} from '../../studio/contract.js'
import { hexHsl, hslToHex, luminance } from '../../utils/colorTools.js'

const AA_NORMAL = 4.5
const HEAVY_BYTES = 350 * 1024
const TEXT_LIMITS = [
  ['headline',      'Titular de portada',  90],
  ['description',   'Descripción',        300],
  ['cta_text',      'Texto del llamado',   80],
  ['catalog_note',  'Aviso del catálogo', 140],
  ['footer_text',   'Texto del pie',      140],
  ['about_text',    'Sobre nosotros',     800]
]

const rowText = (v) => String(v || '').trim()
const hasRows = (v) => Array.isArray(v) && v.length > 0

function enabledBlocks(layout, surface) {
  const blocks = layout?.[surface]?.blocks
  return Array.isArray(blocks) ? blocks.filter((b) => b && b.enabled !== false) : []
}
const hasBlock = (layout, surface, id) => enabledBlocks(layout, surface).some((b) => b.id === id)

// Contenido que alimenta cada bloque de la portada. value=true → revisar
// que exista contenido; 'auto' → la web ya lo oculta solo (no es hallazgo).
const LANDING_SOURCES = {
  announcements: { label: 'Cinta de anuncios',      has: (c) => hasRows(c.form.announcements) },
  about:         { label: 'Sobre nosotros',         has: (c) => Boolean(rowText(c.form.about_title) || rowText(c.form.about_text) || c.form.about_years || rowText(c.form.about_mission) || rowText(c.form.about_specialties)) },
  services:      { label: 'Qué ofrecemos',          has: (c) => hasRows(c.form.services) },
  stats:         { label: 'Cifras del negocio',     has: (c) => hasRows(c.form.stats) },
  benefits:      { label: 'Garantías',              has: (c) => hasRows(c.form.benefits) },
  timeline:      { label: 'Trayectoria',            has: (c) => hasRows(c.form.timeline) },
  team:          { label: 'Equipo',                 has: (c) => hasRows(c.form.team) },
  gallery:       { label: 'Galería',                has: (c) => hasRows(c.gallery) },
  testimonials:  { label: 'Testimonios',            has: (c) => hasRows(c.form.testimonials) },
  faq:           { label: 'Preguntas frecuentes',   has: (c) => hasRows(c.form.faqs) },
  video:         { label: 'Video',                  has: (c) => Boolean(rowText(c.form.video_url)) },
  featured:      { label: 'Vitrina de productos',   has: (c) => !c.catalogLoaded || c.products.length > 0, nav: 'catalogs' },
  categories:    { label: 'Departamentos',          has: (c) => !c.catalogLoaded || c.categories.length > 0, nav: 'catalogs' },
  cta:           { label: 'Llamado a la acción',    has: (c) => hasContact(c), nav: 'company' },
  contact:       { label: 'Contacto',               has: (c) => hasContact(c), nav: 'company' }
}
const CATALOG_SOURCES = {
  note:   { label: 'Aviso del catálogo',   has: (c) => Boolean(rowText(c.form.catalog_note)) },
  banner: { label: 'Carrusel de portada',  has: (c) => hasRows(c.carousel) },
  promo:  { label: 'Promociones vigentes', has: (c) => !c.catalogLoaded || c.products.some((p) => Number(p?.offer_price) > 0) },
  grid:   { label: 'Grilla de productos',  has: (c) => !c.catalogLoaded || c.products.length > 0, nav: 'catalogs' }
}
const SERVICES_SOURCES = {
  band:  { label: 'Cinta de servicios',    has: (c) => !c.servicesLoaded || c.servicesCount > 0, nav: 'services' },
  steps: { label: 'Cómo funciona',         has: (c) => hasRows(c.form.service_steps) },
  form:  { label: 'Formulario de pedido',  has: (c) => hasContact(c), nav: 'company' },
  faq:   { label: 'Preguntas frecuentes',  has: (c) => hasRows(c.form.faqs) }
}

function hasContact(c) {
  const f = c.form
  return Boolean(rowText(f.whatsapp) || rowText(f.contact_email) || rowText(f.instagram) || rowText(f.facebook) || rowText(f.tiktok) || rowText(f.address))
}

const issue = (id, sev, icon, title, detail, fix = null) => ({ id, sev, icon, title, detail, fix })
const fmtKb = (bytes) => `${Math.round(bytes / 1024)} KB`

// ---------------------------------------------------------------------------
// Contraste: UNA sola fuente de verdad. El panel Colores y Salud consumen
// esta tabla (panelShared.contrastChecks la reexporta) para que nunca digan
// cosas distintas sobre la misma paleta.
// `role` = rol del tema que hace de primer plano; `bgRole` = fondo.
// ---------------------------------------------------------------------------
export const CONTRAST_PAIRS = [
  { key: 'text-surface',    role: 'text',    bgRole: 'surface', min: AA_NORMAL, label: 'Texto sobre tarjetas' },
  { key: 'text-bg',         role: 'text',    bgRole: 'bg',      min: AA_NORMAL, label: 'Texto sobre el fondo' },
  { key: 'muted-surface',   role: 'muted',   bgRole: 'surface', min: AA_NORMAL, label: 'Texto secundario sobre tarjetas' },
  { key: 'muted-bg',        role: 'muted',   bgRole: 'bg',      min: AA_NORMAL, label: 'Texto secundario sobre el fondo' },
  { key: 'primary-surface', role: 'primary', bgRole: 'surface', min: AA_NORMAL, label: 'Color principal sobre tarjetas' },
  { key: 'primary-bg',      role: 'primary', bgRole: 'bg',      min: 3,          label: 'Color principal sobre el fondo' },
  { key: 'on-primary',      role: null,      bgRole: 'primary', min: AA_NORMAL, label: 'Texto de los botones' }
]

// Colores efectivos de un par (on-primary deriva el texto con textOn).
export function pairColors(pair, palette) {
  const bg = palette?.[pair.bgRole]
  const fg = pair.role ? palette?.[pair.role] : textOn(bg)
  return { fg, bg }
}

const FG_ROLES = ['text', 'muted', 'primary']
const SIDE_SPLIT = 0.1792 // luminancia donde negro y blanco empatan (≈4.58:1)

function normPalette(palette) {
  const out = { ...(palette || {}) }
  for (const key of Object.keys(SITE_THEME_DEFAULTS.palette)) {
    out[key] = normalizeHex(out[key]) || SITE_THEME_DEFAULTS.palette[key]
  }
  return out
}

function sideOf(hex) {
  return luminance(hex) >= SIDE_SPLIT ? 'light' : 'dark'
}

function toneFor(hex, side) {
  const [h, s] = hexHsl(hex)
  return side === 'light'
    ? hslToHex(h, Math.min(s, 0.35), 0.965)
    : hslToHex(h, Math.min(s, 0.45), 0.09)
}

// Mueve un rol hacia el extremo (negro/blanco) que mejor cumple TODOS sus
// pares a la vez: así corregir "muted" no rompe muted/bg al arreglar
// muted/surface.
function fixRole(role, palette) {
  const pairs = CONTRAST_PAIRS.filter((p) => p.role === role)
  const bgs = pairs.map((p) => palette[p.bgRole])
  const mins = pairs.map((p) => p.min)
  const fg = palette[role]
  if (pairs.every((p, i) => contrastRatio(fg, bgs[i]) >= mins[i])) return fg
  const worst = (hex) => Math.min(...bgs.map((bg, i) => contrastRatio(hex, bg) / mins[i]))
  const black = [0, 0, 0]
  const white = [255, 255, 255]
  const target = worst('#000000') >= worst('#ffffff') ? black : white
  const rgb = hexToRgb(fg)
  for (let t = 0.02; t <= 1.0001; t += 0.02) {
    const hex = rgbToHex(rgb.map((c, i) => c + (target[i] - c) * t))
    if (bgs.every((bg, i) => contrastRatio(hex, bg) >= mins[i])) return hex
  }
  return rgbToHex(target)
}

// Paleta reparada: converge en ≤4 pasadas. Si fondo y superficie quedan en
// lados opuestos del punto de cruce, alinea el fondo al lado de la
// superficie (con el tono original) para que un único color de texto sirva
// en ambos.
export function repairPalette(palette) {
  const p = normPalette(palette)
  const side = sideOf(p.surface)
  if (sideOf(p.bg) !== side) p.bg = toneFor(p.bg, side)
  for (let pass = 0; pass < 4; pass += 1) {
    let changed = false
    for (const role of FG_ROLES) {
      const next = fixRole(role, p)
      if (next !== p[role]) { p[role] = next; changed = true }
    }
    if (!changed) break
  }
  // El acento y el primario son el mismo color de marca en todo el Studio
  // (ColorsPanel.setRole los mantiene sincronizados).
  p.accent = p.primary
  return p
}

export function palettePasses(palette) {
  const p = normPalette(palette)
  return CONTRAST_PAIRS.every((pair) => {
    const { fg, bg } = pairColors(pair, p)
    return contrastRatio(fg, bg) >= pair.min
  })
}

function palettePatch(before, after) {
  const out = {}
  for (const [key, value] of Object.entries(after)) {
    if (normalizeHex(before?.[key]) !== value) out[key] = value
  }
  return out
}

// --- 1. Contraste AA ---------------------------------------------------
function checkContrast(theme, out) {
  const p = theme?.palette || {}
  const repaired = repairPalette(p)
  const values = palettePatch(p, repaired)
  const invalid = Object.keys(SITE_THEME_DEFAULTS.palette).filter((k) => normalizeHex(p[k]) === null)
  if (invalid.length) {
    out.push(issue('palette-invalid', 'warn', 'palette', 'Hay colores inválidos en tu paleta',
      `${invalid.length} color${invalid.length > 1 ? 'es no tienen' : ' no tiene'} un formato hexadecimal válido (#rrggbb).`,
      Object.keys(values).length ? { kind: 'palette', values, label: 'Corregir colores' } : null))
  }
  CONTRAST_PAIRS.forEach((pair) => {
    const { fg, bg } = pairColors(pair, p)
    const ratio = contrastRatio(fg, bg)
    if (ratio >= pair.min) return
    const fix = Object.keys(values).length
      ? { kind: 'palette', values, label: 'Corregir contraste' }
      : null
    out.push(issue(`contrast-${pair.key}`, 'warn', 'palette', `${pair.label}: contraste bajo`,
      `La relación es ${ratio.toFixed(1)}:1 y WCAG AA pide ${pair.min}:1. Se dificulta la lectura.`, fix))
  })
}

// --- 2. Imágenes pesadas ------------------------------------------------
function checkImages(c, out) {
  const heavy = []
  const push = (label, size) => { if (Number(size) > HEAVY_BYTES) heavy.push(`${label} (${fmtKb(size)})`) }
  push('Logo', c.logoSize)
  push('Portada', c.coverSize)
  ;(c.carousel || []).forEach((img, i) => push(`Carrusel ${i + 1}`, img?.size))
  ;(c.gallery || []).forEach((img, i) => push(`Galería ${i + 1}`, img?.size))
  if (heavy.length) {
    out.push(issue('heavy-images', 'info', 'images', `${heavy.length} imagen${heavy.length > 1 ? 'es pesada' : ' pesada'}`,
      `${heavy.join(', ')}. Superan ${fmtKb(HEAVY_BYTES)} y pueden frenar la carga; volvé a subirlas comprimidas.`,
      { kind: 'nav', target: 'images', label: 'Ir a mis fotos' }))
  }
}

// --- 3. Textos largos ---------------------------------------------------
function checkLongTexts(c, out) {
  for (const [field, label, max] of TEXT_LIMITS) {
    const len = rowText(c.form[field]).length
    if (len > max) {
      out.push(issue(`long-${field}`, 'info', 'type', `${label} muy largo`,
        `${len} caracteres (recomendado ${max} o menos). Los textos largos pierden lectores.`,
        { kind: 'nav', target: 'content', label: 'Editar textos' }))
    }
  }
}

// --- 4. Secciones vacías ------------------------------------------------
function checkEmptySections(c, out) {
  const templates = Array.isArray(c.form.site_templates) ? c.form.site_templates : []
  const scan = (surface, sources) => {
    for (const block of enabledBlocks(c.layout, surface)) {
      const src = sources[block.id]
      if (!src || src.has(c)) continue
      out.push(issue(`empty-${surface}-${block.id}`, 'warn', 'layout-grid', `"${src.label}" está vacío`,
        `La sección está activada pero no tiene contenido, así que puede verse vacía.`,
        { kind: 'nav', target: src.nav || 'content', label: 'Cargar contenido' }))
    }
  }
  scan('landing', LANDING_SOURCES)
  if (templates.includes('catalog')) scan('catalog', CATALOG_SOURCES)
  if (templates.includes('services')) scan('services', SERVICES_SOURCES)
}

// --- 5. CTA ausente -----------------------------------------------------
function checkCta(c, out) {
  if (hasContact(c)) return
  const hasCtaBlock = hasBlock(c.layout, 'landing', 'cta') || hasBlock(c.layout, 'landing', 'contact')
  out.push(issue('no-cta', 'warn', 'megaphone', 'Tu web no tiene cómo contactarte',
    `No cargaste WhatsApp, email ni redes${hasCtaBlock ? ' y el llamado a la acción queda sin destino' : ''}. Sin contacto no hay ventas.`,
    { kind: 'nav', target: 'company', label: 'Cargar contacto' }))
}

// --- 6. Tamaños táctiles -------------------------------------------------
function checkTouch(c, out) {
  if (c.theme?.buttons?.size === 'sm') {
    out.push(issue('touch-buttons', 'info', 'smartphone', 'Botones chicos para el dedo',
      'El tamaño S queda por debajo del área táctil recomendada (44px) en celulares.',
      { kind: 'theme', group: 'buttons', key: 'size', value: 'md', label: 'Pasar a tamaño M' }))
  }
  if (c.form.whatsapp && c.theme?.mobile?.stickyCta === false) {
    out.push(issue('touch-sticky', 'info', 'smartphone', 'Botón de contacto escondido',
      'Tenés WhatsApp pero el botón fijo está apagado: en celular el contacto queda a un scroll de distancia.',
      { kind: 'theme', group: 'mobile', key: 'stickyCta', value: true, label: 'Activar botón fijo' }))
  }
}

export function analyzeStudioHealth(ctx) {
  // ctx: {theme (resuelto), form (campos publicados), layout (borrador),
  // carousel, gallery, logoSize, coverSize, products, categories,
  // servicesCount, catalogLoaded, servicesLoaded}
  // catalogLoaded/servicesLoaded=false (stores sin cargar) desactiva los
  // chequeos de productos/servicios: vacío por no-cargado no es hallazgo.
  const c = { products: [], categories: [], servicesCount: 0, carousel: [], gallery: [], ...ctx }
  const out = []
  checkContrast(c.theme, out)
  checkImages(c, out)
  checkLongTexts(c, out)
  checkEmptySections(c, out)
  checkCta(c, out)
  checkTouch(c, out)
  return out.sort((a, b) => (a.sev === b.sev ? 0 : a.sev === 'warn' ? -1 : 1))
}

// Puntaje 0-100 para la cabecera del panel (warn −12, info −4).
export function healthScore(issues) {
  return Math.max(0, 100 - issues.reduce((acc, i) => acc + (i.sev === 'warn' ? 12 : 4), 0))
}
