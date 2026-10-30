// Puente Studio <-> iframe de vista previa (same-origin).
//  - studioPreviewVars/Attrs: consumo del theme EN EL IFRAME (las importa
//    StorePublicLayout): variables --st-* del contrato + equivalentes de
//    las variables que ya usa la hoja pública (--store-*/--sp-*), así el
//    tema se ve hoy sin esperar la fase de rewire de store-page.css.
//  - installPreviewBridge / applyFocusRing / syncFontLink: herramientas
//    del lado HOST (operan sobre el document del iframe): hover y click
//    para elegir elementos, anillo animado al editar un control, tema
//    claro/oscuro del visor y carga de la fuente elegida.
import {
  themeToCssVars, themeDataAttrs, themeExplicitKeys, pickThemeVars,
  resolveSiteTheme, resolveStyleColors, hexToRgb, rgbToHex, textOn
} from '../../studio/contract.js'
import { STORE_FONTS, ensureStoreFont, effectiveAccent } from '../../api/stores.api.js'
import { deriveAccent, bandPalette, adaptPalette } from '../../utils/colorTools.js'
import { pickTargetFor } from './studioModel.js'

function mixHex(a, b, t) {
  const [ar, ag, ab] = hexToRgb(a)
  const [br, bg, bb] = hexToRgb(b)
  return rgbToHex([ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t])
}

function fontFamilyOf(value) {
  const v = String(value || '').trim()
  if (!v) return 'Inter, system-ui, sans-serif'
  if (v.includes(',') || v.includes("'") || v.includes('"')) return v
  return STORE_FONTS[v]?.family || v
}

// Fondo compuesto del tema: velo + capa (imagen/degradado/malla/patrón) +
// color base. Viaja entero por --sp-bg (la hoja hace `background: var(--sp-bg)`),
// así una imagen propia no necesita url() suelto y el overlay siempre queda
// encima de la capa elegida.
function backgroundStack(t, all) {
  const bg = t.background
  const p = t.palette
  const layers = []
  const overlay = all['--st-bg-overlay']
  if (overlay && overlay !== 'transparent') layers.push(`linear-gradient(${overlay}, ${overlay})`)
  if (bg.type === 'image' && bg.value) {
    layers.push(`url("${bg.value.replace(/"/g, '%22')}") center / cover no-repeat`)
    layers.push(p.bg)
  } else if (bg.type !== 'solid' && bg.value) {
    layers.push(bg.value)
  } else {
    layers.push(p.bg)
  }
  return layers.join(', ')
}

// ---------------------------------------------------------------------------
// Contrato v4: typography.roles + layout + skin.
// resolveSiteTheme() sanea solo los campos v1/v2/v3, así que roles/layout/skin
// se leen del theme PARCIAL (el que llega del backend) y se traducen acá.
// Todo sale por variables CSS y atributos data-st-*: la hoja pública consume
// tokens, nunca CSS arbitrario.
// ---------------------------------------------------------------------------
export const ROLE_KEYS = [
  'display', 'h1', 'h2', 'h3', 'body', 'lead', 'eyebrow', 'label',
  'quote', 'price', 'nav', 'button', 'footer'
]

// Espejo de SKIN_FAMILIES de ai_design_skins.py (32: las 26 de la v5 + las 6
// exclusivas de la IA, que el Studio no ofrece pero el motor sí propone).
// Un id desconocido no carga hoja y la tienda queda como está.
export const SKIN_FAMILIES = [
  'glass', 'editorial', 'brutal', 'soft', 'tech', 'warm', 'luxury', 'kinetic',
  'paper', 'neon', 'minimal', 'organic', 'retro', 'corporate', 'playful',
  'mono', 'gradient', 'cinematic',
  'swiss', 'magazine', 'pop', 'aurora', 'craft', 'nostalgia', 'prestige', 'showcase',
  'atelier', 'terminal', 'riso', 'vitrina', 'cobre', 'lumen'
]

const ROLE_SIZES = {
  xs: '0.75rem', sm: '0.875rem', md: '1rem', lg: '1.25rem',
  xl: '1.5rem', '2xl': '2rem', '3xl': '2.75rem',
  display: 'clamp(2.5rem, 6vw, 4.5rem)'
}
const ROLE_TRACKING = { tighter: '-0.03em', tight: '-0.015em', normal: '0', wide: '0.04em', wider: '0.09em' }
const ROLE_LEADING = { tight: '1.08', snug: '1.25', normal: '1.55', relaxed: '1.75' }
const ROLE_CASE = { none: 'none', upper: 'uppercase' }

// roles -> --st-f-<rol>-{family,size,weight,tracking,leading,case}
// Devuelve además la lista de roles realmente definidos: la hoja pública
// gatea cada regla con [data-st-roles~='<rol>'], así un rol ausente deja
// intacto el look de la plantilla (tienda vieja = idéntica a hoy).
export function roleVars(theme) {
  const roles = theme?.typography?.roles
  const vars = {}
  const defined = []
  if (!roles || typeof roles !== 'object') return { vars, roles: defined }
  for (const key of ROLE_KEYS) {
    const r = roles[key]
    if (!r || typeof r !== 'object') continue
    const family = r.font ? fontFamilyOf(r.font) : ''
    const size = ROLE_SIZES[r.size]
    const weight = Number(r.weight)
    const tracking = ROLE_TRACKING[r.tracking]
    const leading = ROLE_LEADING[r.leading]
    const textCase = ROLE_CASE[r.case]
    if (!family && !size && !Number.isFinite(weight) && !tracking && !leading && !textCase) continue
    defined.push(key)
    if (family) vars[`--st-f-${key}-family`] = family
    if (size) vars[`--st-f-${key}-size`] = size
    if (Number.isFinite(weight) && weight >= 300 && weight <= 900) {
      vars[`--st-f-${key}-weight`] = String(Math.round(weight / 100) * 100)
    }
    if (tracking) vars[`--st-f-${key}-tracking`] = tracking
    if (leading) vars[`--st-f-${key}-leading`] = leading
    if (textCase) vars[`--st-f-${key}-case`] = textCase
  }
  return { vars, roles: defined }
}

const LAYOUT_DENSITY = { compact: '1', comfortable: '1.35', spacious: '1.8' }
const LAYOUT_GUTTER = {
  sm: 'clamp(12px, 3vw, 20px)',
  md: 'clamp(16px, 5vw, 40px)',
  lg: 'clamp(24px, 7vw, 64px)'
}
const LAYOUT_MEASURE = { narrow: '52ch', normal: '66ch', wide: '80ch' }
const LAYOUT_RADIUS = { none: '0px', sm: '8px', md: '16px', lg: '24px', xl: '34px' }
const LAYOUT_GRID = ['12', 'asym', 'split', 'bento', 'editorial']
const LAYOUT_HERO = ['centered', 'split', 'cinema', 'logo', 'editorial']

// layout -> --st-l-* (tokens) + data-st-l-* (variantes discretas).
export function layoutVars(theme) {
  const lay = theme?.layout
  const vars = {}
  const attrs = {}
  if (!lay || typeof lay !== 'object') return { vars, attrs }
  if (LAYOUT_DENSITY[lay.density]) {
    vars['--st-l-density'] = LAYOUT_DENSITY[lay.density]
    attrs['data-st-l-density'] = lay.density
  }
  if (LAYOUT_GUTTER[lay.gutter]) {
    vars['--st-l-gutter'] = LAYOUT_GUTTER[lay.gutter]
    attrs['data-st-l-gutter'] = lay.gutter
  }
  if (LAYOUT_MEASURE[lay.measure]) {
    vars['--st-l-measure'] = LAYOUT_MEASURE[lay.measure]
    attrs['data-st-l-measure'] = lay.measure
  }
  if (LAYOUT_RADIUS[lay.radiusScale]) {
    vars['--st-l-radius'] = LAYOUT_RADIUS[lay.radiusScale]
    attrs['data-st-l-radius'] = lay.radiusScale
  }
  if (LAYOUT_GRID.includes(lay.grid)) {
    vars['--st-l-grid'] = lay.grid
    attrs['data-st-l-grid'] = lay.grid
  }
  if (LAYOUT_HERO.includes(lay.hero)) {
    vars['--st-l-hero'] = lay.hero
    attrs['data-st-l-hero'] = lay.hero
  }
  return { vars, attrs }
}

// skin del contrato: {id, family}. La familia manda (hoja skin-<family>.css).
export function skinOf(theme) {
  const skin = theme?.skin
  if (!skin || typeof skin !== 'object') return ''
  const family = String(skin.family || skin.id || '').trim().toLowerCase()
  return SKIN_FAMILIES.includes(family) ? family : ''
}

// theme resuelto -> {vars} para :style de .store-page.
//  - `--st-*`: el contrato completo (o solo los campos de `explicit`).
//  - `--store-accent*`/`--store-font`: espejo de los campos que ya persiste
//    la web (acento/fuente) para que la hoja clásica y las plantillas lo
//    consuman sin cambios.
//  - `--sp-*`: tokens de la hoja pública derivados del contrato (colores,
//    radios, sombras, tipografía, botones, grilla).
// `explicit` (Set/array de 'seccion.clave') limita el mapeo a lo que el
// tema fija de verdad: sin clave no se emite la variable y el CSS cae a su
// fallback (tienda sin tema o plantilla con su propio look).
// Los roles de color se aplican igual en claro y en oscuro; pageTheme se
// conserva por compatibilidad de la firma.
export function studioPreviewVars(theme, pageTheme = 'light', explicit = null) {
  const t = resolveSiteTheme(theme)
  const keys = explicit ? (explicit instanceof Set ? explicit : new Set(explicit)) : null
  const on = (key) => !keys || keys.has(key)
  // Paleta fijada por el tema + modo de página opuesto (p. ej. un preset
  // claro guardado con la página en oscuro): se adapta al modo para que el
  // fondo no quede blanco sobre una página nocturna.
  if (['palette.bg', 'palette.surface', 'palette.text', 'palette.muted'].some(on)) {
    const adapted = adaptPalette(t.palette, pageTheme)
    if (adapted) t.palette = { ...t.palette, ...adapted }
  }
  // Con resolvedor: --st-font-* sale como familia real (no el slug del
  // catálogo), así el CSS puede consumirlo directo sin perder la fuente.
  const all = themeToCssVars(t, fontFamilyOf, pageTheme)
  const vars = pickThemeVars(all, keys)
  const p = t.palette
  // v4: roles tipográficos + layout. Salen siempre que el tema parcial los
  // defina (themeExplicitKeys no conoce estas secciones; el gate es la
  // presencia del dato). Sin roles/layout el objeto no cambia.
  Object.assign(vars, roleVars(theme).vars, layoutVars(theme).vars)

  if (on('palette.accent') || on('palette.primary')) {
    const accent = on('palette.accent') ? p.accent : p.primary
    // La tinta se deriva del acento hasta garantizar texto blanco (AA): un
    // acento claro (amarillo/celeste) ya no deja el nombre ilegible en la
    // barra superior ni en los botones.
    const ink = deriveAccent(accent).ink
    vars['--store-accent'] = accent
    vars['--store-accent-ink'] = ink
    vars['--store-accent-soft'] = deriveAccent(accent).soft
    // Banda del hero y superficies de acento con texto blanco.
    const band = bandPalette(accent)
    vars['--sp-band-c1'] = band.c1
    vars['--sp-band-c2'] = band.c2
    vars['--sp-band-c3'] = band.c3
    vars['--sp-band-c4'] = band.c4
    vars['--sp-band-base1'] = band.base1
    vars['--sp-band-base2'] = band.base2
    vars['--sp-band-mark'] = band.mark
    // Tinta de la banda (hero, cifras, CTA, barra superior): un solo token
    // para todo el texto que va arriba del acento. Antes cada regla de
    // store-page.css escribía #fff a mano y la piel no podía corregirlo; sin
    // tema el token cae al mismo blanco de siempre (regresión cero).
    const onBand = textOn(band.base1)
    vars['--sp-on-band'] = onBand
    vars['--sp-on-band-2'] = `color-mix(in srgb, ${onBand} 88%, transparent)`
    vars['--sp-on-band-muted'] = `color-mix(in srgb, ${onBand} 78%, transparent)`
  }
  // El rol "Primario" manda en botones sólidos (el acento queda para
  // enlaces y detalles): si el tema lo fija, pisa el accent-ink de siempre.
  if (on('palette.primary')) vars['--sp-btn-bg'] = p.primary
  if (on('typography.body')) vars['--store-font'] = fontFamilyOf(t.typography.body)
  if (on('typography.heading')) vars['--sp-display'] = fontFamilyOf(t.typography.heading)
  if (on('typography.body')) vars['--sp-body'] = fontFamilyOf(t.typography.body)

  // La paleta se aplica en claro y en oscuro, pero SOLO para los roles que
  // el tema fija: un rol ausente conserva la paleta propia de la hoja.
  if (on('palette.surface')) {
    vars['--sp-card'] = p.surface
    vars['--sp-card-solid'] = p.surface
    vars['--sp-surface'] = p.surface
  }
  if (on('palette.text') || on('palette.muted')) {
    if (on('palette.text')) vars['--sp-ink'] = p.text
    vars['--sp-ink-2'] = mixHex(p.text, p.muted, 0.45)
  }
  if (on('palette.muted')) vars['--sp-muted'] = p.muted
  if (on('palette.border')) vars['--sp-line'] = p.border
  if (on('palette.accent') || on('palette.primary')) {
    // El velo suave se mezcla contra la superficie del modo vigente: en
    // oscuro, mezclar contra blanco dejaba contenedores (p. ej. la misión)
    // casi blancos con el texto claro encima.
    const softBase = pageTheme === 'dark'
      ? (p.surface || p.bg || '#0b1220')
      : '#ffffff'
    vars['--sp-soft'] = mixHex(p.accent, softBase, 0.8)
  }
  if (on('palette.accent') || on('palette.primary')) vars['--sp-accent-text'] = vars['--store-accent-ink']
  const bgStackOn = on('background.type') || on('background.value') || on('background.overlay')
  if (bgStackOn || on('palette.bg')) vars['--sp-bg'] = backgroundStack(t, all)

  if (on('containers.radius')) vars['--sp-radius'] = all['--st-radius']
  if (on('containers.shadow')) {
    vars['--sp-shadow-sm'] = all['--st-shadow']
    vars['--sp-shadow-md'] = all['--st-shadow']
  }
  if (on('containers.density')) {
    vars['--sp-card-pad'] = all['--st-card-pad']
    vars['--sp-section-gap'] = all['--st-section-gap']
  }
  if (on('buttons.shape')) vars['--sp-btn-radius'] = all['--st-btn-radius']
  if (on('buttons.size')) {
    vars['--sp-btn-h'] = all['--st-btn-h']
    vars['--sp-btn-px'] = all['--st-btn-px']
    vars['--sp-btn-fs'] = all['--st-btn-fs']
  }
  if (on('typography.scale')) {
    vars['--sp-h1-size'] = all['--st-h1-size']
    vars['--sp-h2-size'] = all['--st-h2-size']
    vars['--sp-text-size'] = all['--st-text-size']
    vars['--sp-leading'] = all['--st-leading']
  }
  if (on('mobile.gridCols')) vars['--sp-grid-cols'] = all['--st-grid-cols']
  if (on('motion.intensity')) vars['--sp-motion-dur'] = all['--st-motion-dur']
  // Juego de colores del estilo elegido (fuentes + contenedores) del modo
  // vigente: manda sobre los roles de palette para que el estilo se vea
  // completo aun cuando el plan solo persiste este subconjunto (Básico).
  if (on('styleColors')) {
    const sc = resolveStyleColors(t, pageTheme)
    vars['--sp-ink'] = sc.fonts.heading
    vars['--sp-ink-2'] = sc.fonts.body
    vars['--sp-muted'] = sc.fonts.muted
    vars['--sp-accent-text'] = sc.fonts.link
    vars['--sp-card'] = sc.containers.surface
    vars['--sp-card-solid'] = sc.containers.surface
    vars['--sp-surface'] = sc.containers.surface
    vars['--sp-line'] = sc.containers.border
    // Solo con fondo sólido: una malla/degradado/imagen propia se conserva.
    if (t.background.type === 'solid' && !t.background.value) vars['--sp-bg'] = sc.containers.bg
  }
  return vars
}

// Atributos data-st-* del contrato (variantes discretas) para .store-page.
export function studioPreviewAttrs(theme, explicit = null, mode = 'light') {
  const attrs = { ...themeDataAttrs(theme, explicit, mode), 'data-st-themed': '' }
  // v4: roles definidos (lista separada por espacios), layout y skin. La
  // hoja pública gatea cada regla con estos atributos: sin ellos, nada cambia.
  const roles = roleVars(theme).roles
  if (roles.length) attrs['data-st-roles'] = roles.join(' ')
  Object.assign(attrs, layoutVars(theme).attrs)
  const skin = skinOf(theme)
  if (skin) attrs['data-st-skin'] = skin
  return attrs
}

// ---------------------------------------------------------------------------
// Web publicada: las mismas variables, SIEMPRE (no solo en modo Studio).
// `site_theme` es parcial; se siembra con el acento/fuente que ya persiste
// la tienda para que un tema sin paleta no pise el look actual. Sin tema
// guardado devuelve {} — la página queda exactamente como hoy.
// ---------------------------------------------------------------------------
export function storeSiteThemeVars(customization, pageTheme = 'light') {
  const theme = customization?.site_theme
  if (!theme || typeof theme !== 'object' || !Object.keys(theme).length) return {}
  const accent = effectiveAccent(customization || {})
  const nameFont = customization?.name_font || 'inter'
  const merged = {
    ...theme,
    palette: { primary: accent.hex, secondary: accent.ink, accent: accent.hex, ...(theme.palette || {}) },
    typography: { heading: nameFont, body: nameFont, ...(theme.typography || {}) }
  }
  return studioPreviewVars(merged, pageTheme, themeExplicitKeys(theme))
}

// Atributos del tema PUBLICADO (web real, no solo el iframe del Studio).
// `skin`/`styleColors` no son claves de campo del contrato (viajan como
// bloque entero), así que se agregan a mano: sin ellos la hoja no carga la
// piel ni gatea las reglas `[data-st-*]` y la web vuelve al look base.
export function storeSiteThemeAttrs(customization, pageTheme = 'light') {
  const theme = customization?.site_theme
  if (!theme || typeof theme !== 'object' || !Object.keys(theme).length) return {}
  const keys = themeExplicitKeys(theme)
  if (theme.skin && typeof theme.skin === 'object') keys.add('skin')
  if (theme.styleColors && typeof theme.styleColors === 'object') keys.add('styleColors')
  if (theme.typography?.roles) keys.add('typography.roles')
  if (theme.layout && typeof theme.layout === 'object') keys.add('layout')
  const attrs = studioPreviewAttrs(theme, keys, pageTheme)
  // El set de colores del estilo es de un modo concreto: la hoja usa
  // data-st-style para saber qué juego está vigente.
  if (theme.styleColors) attrs['data-st-style'] = pageTheme === 'dark' ? 'dark' : 'light'
  return attrs
}

// ---------------------------------------------------------------------------
// Lado host: interacción sobre el document del iframe
// ---------------------------------------------------------------------------

// Selectores que traducen un target del contrato a elementos reales de la
// página pública (bloques por data-blk; el resto por clases semánticas).
const TARGET_SELECTORS = {
  hero: '.sp-hero, .sp-hero-band, .sd-hero, [class*="-hero"], [class*="hero-"]',
  'chrome.nav': '.sp-top, .sp-shop-nav, .sp-dock',
  card: '.tpc, .sp-card, [class*="-card"]',
  typo: 'h1, h2, h3',
  buttons: '.sp-btn, [class*="-cta"], [class*="-btn"]',
  media: '.sp-logo.lg, .sp-hero img, figure img, img',
  page: '.store-page'
}

export function resolveTargetEl(doc, target) {
  if (!doc || !target) return null
  if (target.startsWith('blk:')) {
    const wrap = doc.querySelector(`[data-blk="${target.slice(4)}"]`)
    return wrap?.firstElementChild || wrap
  }
  if (target.startsWith('sec:')) return doc.getElementById(target.slice(4))
  const sel = TARGET_SELECTORS[target]
  if (sel) return doc.querySelector(sel)
  try { return doc.querySelector(target) } catch { return null }
}

// CSS mínimo inyectado en el iframe en modo Studio: hover punteado para
// ubicar elementos clickeables y el anillo animado de foco.
const BRIDGE_CSS = `
.store-page [data-blk] > :hover { outline: 2px dashed color-mix(in srgb, var(--store-accent, #6366f1) 80%, transparent); outline-offset: 2px; }
.store-page .st-ring { outline: 3px solid var(--store-accent, #6366f1); outline-offset: 3px; animation: st-ring 1s ease-out; }
@keyframes st-ring { 0% { outline-color: var(--store-accent, #6366f1); } 70% { outline-color: var(--store-accent, #6366f1); } 100% { outline-color: transparent; } }
@media (prefers-reduced-motion: reduce) { .store-page .st-ring { animation: none; } }
/* Pistas del tema Studio sobre el look actual: radio de botones del
   contrato. La hoja pública ya consume --st-* con fallback; esto mantiene
   el anillo/hover del editor fiel aun si la hoja cambia. */
.store-page .sp-btn { border-radius: var(--sp-btn-radius, var(--st-btn-radius, 99px)); }
.store-page .sp-icon-btn { border-radius: var(--sp-btn-radius, 50%); }
`

let lastPick = 0

export function installPreviewBridge(iframe, { onPick, onBlockedNav } = {}) {
  const doc = iframe?.contentDocument
  if (!doc) return () => {}
  const style = doc.createElement('style')
  style.id = 'studio-bridge'
  style.textContent = BRIDGE_CSS
  doc.head.appendChild(style)
  // Marca el documento como vista previa: la hoja puede apagar efectos que
  // solo tienen sentido en la web publicada (p. ej. autoplay de video).
  doc.documentElement?.setAttribute('data-studio-preview', '')

  let lastNotice = 0
  const notifyBlocked = () => {
    const now = Date.now()
    if (now - lastNotice < 1600) return
    lastNotice = now
    onBlockedNav?.()
  }
  const pick = (el) => {
    const target = pickTargetFor(el)
    if (!target || !onPick) return
    // El clic queda a 200ms de cooldown por target para no martillear el
    // panel cuando el usuario navega dentro de la preview.
    const now = Date.now()
    if (now - lastPick <= 200) return
    lastPick = now
    onPick(target)
  }
  // Sandbox de interacción: un enlace o un envío de formulario NO navega el
  // iframe (perdería ?studio=1 y el editor). El clic igual elige el elemento
  // para abrir el control que lo edita, así el gesto no queda muerto.
  const onClick = (e) => {
    const link = e.target?.closest?.('a[href], area[href]')
    if (link) {
      e.preventDefault()
      e.stopPropagation()
      pick(e.target)
      notifyBlocked()
      return
    }
    const submit = e.target?.closest?.('button[type="submit"], input[type="submit"], input[type="image"]')
    if (submit) {
      e.preventDefault()
      pick(e.target)
      notifyBlocked()
      return
    }
    pick(e.target)
  }
  const onSubmit = (e) => {
    e.preventDefault()
    e.stopPropagation()
    notifyBlocked()
  }
  const onAuxClick = (e) => {
    if (e.target?.closest?.('a[href]')) e.preventDefault()
  }
  doc.addEventListener('click', onClick, true)
  doc.addEventListener('submit', onSubmit, true)
  doc.addEventListener('auxclick', onAuxClick, true)
  return () => {
    doc.removeEventListener('click', onClick, true)
    doc.removeEventListener('submit', onSubmit, true)
    doc.removeEventListener('auxclick', onAuxClick, true)
    doc.documentElement?.removeAttribute('data-studio-preview')
    style.remove()
  }
}

// Anillo animado sobre el elemento asociado al control que se está
// editando. Sin scroll brusco: solo acerca si quedó fuera de vista.
export function applyFocusRing(doc, target) {
  const el = resolveTargetEl(doc, target)
  if (!el) return false
  el.classList.remove('st-ring')
  void el.offsetWidth
  el.classList.add('st-ring')
  const r = el.getBoundingClientRect()
  const vh = doc.defaultView?.innerHeight || 800
  if (r.top < 0 || r.bottom > vh) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  clearTimeout(el.__stRingT)
  el.__stRingT = setTimeout(() => el.classList.remove('st-ring'), 1100)
  return true
}

// Tema claro/oscuro del VISOR: actúa sobre data-store-theme de la página
// (atributo bindeado por Vue — el modo también viaja en studio:update y
// el layout lo respeta, así el DOM set es el canal de respaldo).
export function setPreviewPageTheme(doc, mode) {
  doc?.querySelector('.store-page')?.setAttribute('data-store-theme', mode === 'dark' ? 'dark' : 'light')
}

// La fuente elegida vive en el document del host (ensureStoreFont); el
// iframe necesita su propio <link> para dibujarla en la vista previa.
export function syncFontLink(doc, slug) {
  const font = STORE_FONTS[slug]
  ensureStoreFont(slug)
  if (!doc || !font?.google) return
  const id = `studio-font-${slug}`
  if (doc.getElementById(id)) return
  const link = doc.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = `https://fonts.googleapis.com/css2?family=${font.google}&display=swap`
  doc.head.appendChild(link)
}

// textOn queda disponible para las fases que pinten swatches en el panel.
export { textOn }
