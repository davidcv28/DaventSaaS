// Puente Studio <-> iframe de vista previa (same-origin).
//  - studioPreviewVars/Attrs: consumo del theme EN EL IFRAME (las importa
//    StorePublicLayout): variables --st-* del contrato + equivalentes de
//    las variables que ya usa la hoja pública (--store-*/--sp-*), así el
//    tema se ve hoy sin esperar la fase de rewire de store-page.css.
//  - installPreviewBridge / applyFocusRing / syncFontLink: herramientas
//    del lado HOST (operan sobre el document del iframe): hover y click
//    para elegir elementos, anillo animado al editar un control, tema
//    claro/oscuro del visor y carga de la fuente elegida.
import { themeToCssVars, themeDataAttrs, resolveSiteTheme, hexToRgb, rgbToHex, textOn } from '../../studio/contract.js'
import { STORE_FONTS, ensureStoreFont } from '../../api/stores.api.js'
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

// theme resuelto -> {vars} para :style de .store-page. pageTheme='dark'
// omite el mapeo --sp-* (la hoja ya pinta su propia paleta oscura y el
// inline ganaría): en oscuro solo viajan acento/fuente + --st-*.
export function studioPreviewVars(theme, pageTheme = 'light') {
  const t = resolveSiteTheme(theme)
  const vars = { ...themeToCssVars(t) }
  const p = t.palette
  vars['--store-accent'] = p.accent
  vars['--store-accent-ink'] = mixHex(p.accent, '#000000', 0.3)
  vars['--store-accent-soft'] = mixHex(p.accent, '#ffffff', 0.88)
  vars['--store-font'] = fontFamilyOf(t.typography.body)
  vars['--sp-btn-radius'] = vars['--st-btn-radius']
  if (pageTheme !== 'dark') {
    vars['--sp-bg'] = t.background.type === 'solid' ? p.bg : (t.background.value || p.bg)
    vars['--sp-card'] = p.surface
    vars['--sp-card-solid'] = p.surface
    vars['--sp-surface'] = p.surface
    vars['--sp-ink'] = p.text
    vars['--sp-ink-2'] = mixHex(p.text, p.muted, 0.45)
    vars['--sp-muted'] = p.muted
    vars['--sp-line'] = p.border
    vars['--sp-soft'] = mixHex(p.accent, '#ffffff', 0.8)
    vars['--sp-accent-text'] = vars['--store-accent-ink']
    vars['--sp-radius'] = vars['--st-radius']
    vars['--sp-shadow-sm'] = vars['--st-shadow']
    vars['--sp-shadow-md'] = vars['--st-shadow']
    if (t.background.type !== 'solid' && t.background.value) {
      vars['--sp-bg'] = t.background.value
    }
  }
  return vars
}

// Atributos data-st-* del contrato (variantes discretas) para .store-page.
export function studioPreviewAttrs(theme) {
  return themeDataAttrs(theme)
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
   contrato (shape -> --st-btn-radius -> --sp-btn-radius). El resto de
   --st-* queda listo para la fase que rewire la hoja pública. */
.store-page .sp-btn { border-radius: var(--sp-btn-radius, 99px); }
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
