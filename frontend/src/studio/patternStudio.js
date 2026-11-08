// Espejo de `studio_theme_css`/`studio_font_css` (pattern_render.py):
// traduce el site_theme del Studio a CSS que los documentos de diseño
// (DesignPattern) entienden — hooks compartidos .btn/.ds-product*/
// section.hero/barra fijada/footer/body. La web publicada la hornea el
// backend en el documento; la vista previa del Studio la inyecta en vivo
// por postMessage (`davent:ds-studio-css`) porque el iframe es de origen
// opaco y no puede leer el tema del host.
import { STORE_FONTS } from '../api/stores.api.js'
import { STUDIO_ROLE_KEYS } from './contract.js'

// Selectores — espejo de los _STUDIO_*_SEL de pattern_render.py.
const BTN_SEL = '.btn, .svc-cta, .pdp-buy, .nav-cta, .top-cta, .rail-btn, .deck-btn'
const CARD_SEL = '.ds-product, .ds-cat, .ds-service, .ds-plan, .ds-faq, .ds-guar, .ds-offer, .ds-contact'
const IMG_SEL = '.ds-product-img'
const NAV_SEL = '[data-ds-pin="top"], header.top, header.head'
const FOOT_SEL = 'footer, .foot'
const HERO_SEL = 'section.hero, .hero'

const ROLE_SEL = {
  display: 'section.hero h1, .hero h1, h1.display',
  h1: 'h1',
  h2: 'h2',
  h3: 'h3',
  body: 'body',
  lead: '.lead, section.hero p, .hero p',
  eyebrow: '.eyebrow, .kicker, [class*="kicker"], [class*="eyebrow"]',
  label: '.label, [class*="label"]',
  quote: 'blockquote, .quote, q',
  price: '.ds-product-price, .ds-product-amount, .ds-plan-price',
  nav: '.nav a, nav a',
  button: '.btn',
  footer: 'footer, .foot'
}

const BTN_RADIUS = { square: '8px', rounded: '14px', pill: '999px' }
const BTN_SIZE = {
  sm: ['38px', '16px', '13px'],
  md: ['46px', '22px', '14.5px'],
  lg: ['54px', '28px', '16px']
}
const IMG_ASPECT = { square: '1 / 1', portrait: '4 / 5', tall: '3 / 4', wide: '16 / 10' }
const IMG_RADIUS = { none: '0', sm: '8px', md: '14px', lg: '20px' }
const IMG_BORDER = { none: '0', thin: '1px', bold: '2px' }
const ROLE_SIZE = {
  xs: '0.75rem', sm: '0.875rem', md: '1rem', lg: '1.25rem',
  xl: '1.5rem', '2xl': '2rem', '3xl': '2.75rem',
  display: 'clamp(2.5rem, 6vw, 4.5rem)'
}
const ROLE_TRACKING = { tighter: '-0.03em', tight: '-0.015em', normal: '0', wide: '0.04em', wider: '0.09em' }
const ROLE_LEADING = { tight: '1.08', snug: '1.25', normal: '1.55', relaxed: '1.75' }
const ROLE_CASE = { none: 'none', upper: 'uppercase' }
const OVERLAY_CSS = { soft: 'rgba(9, 12, 24, .32)', strong: 'rgba(9, 12, 24, .6)' }

// Familias del catálogo de roles -> query css2 (espejo de _STUDIO_FONT_FACE).
const FONT_QUERY = {
  'inter': 'Inter:opsz,wght@14..32,100..900',
  'manrope': 'Manrope:wght@400..800',
  'figtree': 'Figtree:wght@400..700',
  'dm-sans': 'DM+Sans:wght@400..800',
  'space-grotesk': 'Space+Grotesk:wght@400..700',
  'archivo': 'Archivo:wdth,wght@62..125,400..900',
  'sora': 'Sora:wght@400..800',
  'work-sans': 'Work+Sans:wght@400..800',
  'outfit': 'Outfit:wght@300..900',
  'plus-jakarta-sans': 'Plus+Jakarta+Sans:wght@300..800',
  'nunito': 'Nunito:wght@400..800',
  'raleway': 'Raleway:wght@400..800',
  'playfair-display': 'Playfair+Display:ital,wght@0,400..800;1,400..800',
  'fraunces': 'Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900',
  'lora': 'Lora:ital,wght@0,400..700;1,400..700',
  'cormorant-garamond': 'Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400',
  'dm-serif-display': 'DM+Serif+Display',
  'libre-baskerville': 'Libre+Baskerville:ital,wght@0,400;0,700;1,400',
  'cinzel': 'Cinzel:wght@400..800',
  'oswald': 'Oswald:wght@400..700',
  'archivo-black': 'Archivo+Black',
  'bebas-neue': 'Bebas+Neue',
  'space-mono': 'Space+Mono:ital,wght@0,400;0,700;1,400;1,700',
  'jetbrains-mono': 'JetBrains+Mono:ital,wght@0,400..800;1,400..800'
}

const fontFamilyOf = (slug) => STORE_FONTS[slug]?.family || ''

// Tinta sobre una superficie: espejo de _studio_ink (pattern_render.py) —
// los dos extremos de _contrast_ink por luminancia relativa.
function studioInk(hex) {
  const m = /^#([0-9a-f]{6}|[0-9a-f]{3})$/i.exec(String(hex || '').trim())
  if (!m) return '#191611'
  let d = m[1]
  if (d.length === 3) d = d.split('').map((c) => c + c).join('')
  const lin = (i) => {
    const c = parseInt(d.slice(i, i + 2), 16) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  const lum = 0.2126 * lin(0) + 0.7152 * lin(2) + 0.0722 * lin(4)
  return lum > 0.1833 ? '#191611' : '#FFFDF8'
}

function sect(theme, name) {
  const v = theme?.[name]
  return v && typeof v === 'object' ? v : {}
}

// Slugs del catálogo usados por los roles (para las @font-face).
export function patternStudioFontQueries(theme) {
  const roles = sect(theme, 'typography').roles
  const out = []
  if (roles && typeof roles === 'object') {
    for (const key of STUDIO_ROLE_KEYS) {
      const slug = roles[key]?.font
      if (slug && FONT_QUERY[slug] && !out.includes(slug)) out.push(slug)
    }
  }
  return out.map((slug) => FONT_QUERY[slug])
}

// CSS2 de Google Fonts para las familias de los roles — el host sí puede
// salir a internet (el documento sandbox no); el texto viaja por
// postMessage y el puente lo inlinea como <style>.
const fontCssCache = new Map()
export async function patternStudioFontsCss(theme) {
  const queries = patternStudioFontQueries(theme)
  const missing = queries.filter((q) => !fontCssCache.has(q))
  await Promise.all(missing.map(async (q) => {
    try {
      const res = await fetch(`https://fonts.googleapis.com/css2?family=${q}&display=swap`)
      fontCssCache.set(q, res.ok ? await res.text() : '')
    } catch {
      fontCssCache.set(q, '')
    }
  }))
  return queries.map((q) => fontCssCache.get(q) || '').join('\n')
}

// CSS completo del Studio para documentos de diseño. `fontsCss` son las
// @font-face ya resueltas (patternStudioFontsCss); vacío = sin fuentes
// nuevas (caen a las pilas de fallback).
export function patternStudioCss(theme, fontsCss = '') {
  theme = theme && typeof theme === 'object' ? theme : {}
  const surfaces = sect(theme, 'surfaces')
  const images = sect(theme, 'images')
  const buttons = sect(theme, 'buttons')
  const background = sect(theme, 'background')
  const roles = sect(theme, 'typography').roles
  const rules = []

  // Roles primero: a igual especificidad las reglas de secciones ganan
  // después (buttons.size manda sobre el font-size del rol 'button').
  if (roles && typeof roles === 'object') {
    for (const [role, sel] of Object.entries(ROLE_SEL)) {
      const spec = roles[role]
      if (!spec || typeof spec !== 'object') continue
      const decl = []
      const family = fontFamilyOf(spec.font)
      if (family) decl.push(`font-family:${family}`)
      if (ROLE_SIZE[spec.size]) decl.push(`font-size:${ROLE_SIZE[spec.size]}`)
      const weight = Number(spec.weight)
      if (Number.isFinite(weight) && weight >= 300 && weight <= 900) {
        decl.push(`font-weight:${Math.round(weight / 100) * 100}`)
      }
      if (ROLE_TRACKING[spec.tracking]) decl.push(`letter-spacing:${ROLE_TRACKING[spec.tracking]}`)
      if (ROLE_LEADING[spec.leading]) decl.push(`line-height:${ROLE_LEADING[spec.leading]}`)
      if (ROLE_CASE[spec.case]) decl.push(`text-transform:${ROLE_CASE[spec.case]}`)
      if (decl.length) rules.push(`${sel}{${decl.map((d) => `${d}!important`).join(';')}}`)
    }
  }

  const surfSel = { card: CARD_SEL, nav: NAV_SEL, footer: FOOT_SEL, hero: HERO_SEL }
  for (const [key, sel] of Object.entries(surfSel)) {
    const hex = String(surfaces[key] || '')
    if (!/^#[0-9a-f]{6}$/i.test(hex)) continue
    const ink = studioInk(hex)
    rules.push(`${sel}{background:${hex}!important;color:${ink}!important}`)
  }

  const imgDecl = {}
  if (IMG_ASPECT[images.ratio]) imgDecl['aspect-ratio'] = IMG_ASPECT[images.ratio]
  if (images.fit === 'cover' || images.fit === 'contain') imgDecl['object-fit'] = images.fit
  if (/^#[0-9a-f]{6}$/i.test(String(images.bg || ''))) imgDecl.background = images.bg
  if (IMG_RADIUS[images.radius] !== undefined) imgDecl['border-radius'] = IMG_RADIUS[images.radius]
  if (IMG_BORDER[images.border] !== undefined) {
    imgDecl.border = IMG_BORDER[images.border] === '0'
      ? '0'
      : `${IMG_BORDER[images.border]} solid var(--ds-border, currentColor)`
  }
  if (Object.keys(imgDecl).length) {
    rules.push(`${IMG_SEL}{${Object.entries(imgDecl).map(([k, v]) => `${k}:${v}!important`).join(';')}}`)
  }

  const bgType = background.type
  const bgValue = String(background.value || '')
  if (bgType === 'image' && bgValue) {
    rules.push(`body, main{background:url("${bgValue.replace(/"/g, '%22')}") center / cover no-repeat!important}`)
  } else if ((bgType === 'gradient' || bgType === 'mesh' || bgType === 'pattern') && bgValue) {
    rules.push(`body, main{background:${bgValue}!important}`)
  }
  const overlay = OVERLAY_CSS[background.overlay]
  if (overlay) {
    rules.push(`body::after{content:"";position:fixed;inset:0;background:${overlay};pointer-events:none;z-index:2147483000}`)
  }

  const style = buttons.style
  if (['solid', 'outline', 'ghost', 'gradient', 'transparent'].includes(style)) {
    let decl
    if (style === 'solid') {
      decl = 'background:var(--ds-accent, currentColor)!important;color:var(--ds-accent-ink, #fff)!important;border-color:transparent!important'
    } else if (style === 'outline') {
      decl = 'background:transparent!important;color:var(--ds-accent, currentColor)!important;border-color:var(--ds-accent, currentColor)!important'
    } else if (style === 'ghost') {
      decl = 'background:color-mix(in srgb, var(--ds-accent, currentColor) 12%, transparent)!important;color:var(--ds-accent, currentColor)!important;border-color:transparent!important'
    } else if (style === 'gradient') {
      decl = 'background:linear-gradient(120deg, var(--ds-primary, var(--ds-accent, currentColor)), var(--ds-secondary, var(--ds-accent, currentColor)))!important;color:#fff!important;border-color:transparent!important'
    } else {
      decl = 'background:color-mix(in srgb, var(--ds-accent, currentColor) 8%, transparent)!important;color:var(--ds-accent, currentColor)!important;border-color:transparent!important'
    }
    rules.push(`${BTN_SEL}{${decl}}`)
  }
  const bBorder = buttons.borderStyle
  if (['solid', 'dashed', 'dotted', 'none'].includes(bBorder)) {
    const decl = bBorder === 'none'
      ? 'border-color:transparent!important'
      : `border-style:${bBorder}!important;border-width:${bBorder === 'solid' ? '1.5px' : '2px'}!important;border-color:color-mix(in srgb, currentColor 72%, transparent)!important`
    rules.push(`${BTN_SEL}{${decl}}`)
  }
  if (BTN_RADIUS[buttons.shape]) {
    rules.push(`${BTN_SEL}{border-radius:${BTN_RADIUS[buttons.shape]}!important}`)
  }
  if (BTN_SIZE[buttons.size]) {
    const [h, px, fs] = BTN_SIZE[buttons.size]
    rules.push(`${BTN_SEL}{min-height:${h}!important;padding-inline:${px}!important;font-size:${fs}!important}`)
  }

  const css = rules.join('\n')
  return fontsCss ? `${fontsCss}\n${css}` : css
}
