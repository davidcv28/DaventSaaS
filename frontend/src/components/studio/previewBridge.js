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
  resolveSiteTheme, hexToRgb, rgbToHex, textOn
} from '../../studio/contract.js'
import { STORE_FONTS, ensureStoreFont, effectiveAccent } from '../../api/stores.api.js'
import { deriveAccent, bandPalette } from '../../utils/colorTools.js'
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
  // Con resolvedor: --st-font-* sale como familia real (no el slug del
  // catálogo), así el CSS puede consumirlo directo sin perder la fuente.
  const all = themeToCssVars(t, fontFamilyOf)
  const vars = pickThemeVars(all, keys)
  const p = t.palette

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
  if (on('palette.accent') || on('palette.primary')) vars['--sp-soft'] = mixHex(p.accent, '#ffffff', 0.8)
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
  return vars
}

// Atributos data-st-* del contrato (variantes discretas) para .store-page.
export function studioPreviewAttrs(theme, explicit = null) {
  return { ...themeDataAttrs(theme, explicit), 'data-st-themed': '' }
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

export function storeSiteThemeAttrs(customization) {
  const theme = customization?.site_theme
  if (!theme || typeof theme !== 'object' || !Object.keys(theme).length) return {}
  return studioPreviewAttrs(theme, themeExplicitKeys(theme))
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

export function installPreviewBridge(iframe, { onPick } = {}) {
  const doc = iframe?.contentDocument
  if (!doc) return () => {}
  const style = doc.createElement('style')
  style.id = 'studio-bridge'
  style.textContent = BRIDGE_CSS
  doc.head.appendChild(style)
  const onClick = (e) => {
    const target = pickTargetFor(e.target)
    if (target && onPick) {
      // El clic queda a 300ms de cooldown por target para no martillear el
      // panel cuando el usuario navega dentro de la preview.
      const now = Date.now()
      if (now - lastPick > 200) {
        lastPick = now
        onPick(target)
      }
    }
  }
  doc.addEventListener('click', onClick, true)
  return () => {
    doc.removeEventListener('click', onClick, true)
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
