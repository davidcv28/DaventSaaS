// ============================================================================
// Studio de diseño — CONTRATO ÚNICO (fase contrato, sin UI)
//
// Vocabulario compartido por todas las fases del Studio. Este módulo es
// autocontenido a propósito: no importa nada del app (ni stores.api.js, que
// arrastra window/localStorage), así las herramientas corren igual en el
// navegador, en node (scripts/verify-studio-contract.mjs) y dentro del
// iframe de la vista previa.
//
// Piezas:
//   - STUDIO_ENUMS        catálogos cerrados por campo (lo que la UI ofrece
//                         y lo que el backend va a whitelistear)
//   - SITE_THEME_DEFAULTS esquema siteTheme con los defaults que replican el
//                         look actual: una tienda sin site_theme se ve
//                         IDÉNTICA a hoy (verificación en el script).
//   - resolveSiteTheme    merge profundo + saneo (enum/hex fuera de catálogo
//                         vuelven al default — un preset corrupto no rompe)
//   - themeToCssVars      theme resuelto -> dict '--st-*' listo para :style
//   - themeDataAttrs      variantes discretas -> dict 'data-st-*' (los enums
//                         no viajan como valor CSS: se consumen por atributo)
//   - contrastRatio / fixContrast  WCAG AA (autosuficientes — fórmula
//                         estándar; utils/colorTools.js tiene la misma para
//                         la extracción de color del logo en la fase Look)
//   - studioPreset        { id, name, category, preview, tier, template,
//                         theme, layout } — layout espeja layout_config:
//                         { superficie: { blocks: [{id, enabled, order,
//                         variant?, props?}] } } con superficie en
//                         STUDIO_SURFACES; la whitelist real de ids es
//                         TEMPLATE_BLOCKS / clean_layout_config del backend.
//   - STUDIO_MSG + studioUpdate/studioFocus/isStudioMessage  protocolo
//                         postMessage entre el Studio (host) y la vista
//                         previa en vivo (iframe same-origin).
// ============================================================================

export const STUDIO_SURFACES = ['landing', 'catalog', 'services']
export const STUDIO_DEVICES = ['mobile', 'tablet', 'desktop']
export const STUDIO_TIERS = ['base', 'plus', 'advanced']

// Juego de colores por estilo (fuentes + contenedores) con variante clara y
// oscura. El bloque NO vive en los defaults: se deriva de palette cuando el
// tema no lo trae, así una tienda sin estilo se ve idéntica a hoy.
export const STUDIO_STYLE_MODES = ['light', 'dark']
export const STYLE_FONT_KEYS = ['heading', 'body', 'muted', 'link']
export const STYLE_CONTAINER_KEYS = ['bg', 'surface', 'border', 'onSurface']
// Paletas de color seleccionables: pintan contenedores y fuentes. El acento
// elegido más abajo se fusiona como color de enlace/primario.
export const STYLE_PALETTES = [
  { id: 'original', label: 'Original' },
  { id: 'warm', label: 'Cálida' },
  { id: 'cool', label: 'Fría' },
  { id: 'contrast', label: 'Contraste' }
]

export const STUDIO_ENUMS = {
  radius:     ['none', 'sm', 'md', 'lg', 'xl', 'pill'],
  shadow:     ['none', 'soft', 'medium', 'deep'],
  borderW:    ['none', 'thin', 'bold'],
  density:    ['compact', 'comfortable', 'spacious'],
  surface:    ['flat', 'glass', 'elevated', 'outlined'],
  typeScale:  ['compact', 'balanced', 'editorial'],
  btnShape:   ['square', 'rounded', 'pill'],
  btnStyle:   ['solid', 'outline', 'ghost', 'gradient'],
  btnSize:    ['sm', 'md', 'lg'],
  bgType:     ['solid', 'gradient', 'mesh', 'pattern', 'image'],
  overlay:    ['none', 'soft', 'strong'],
  reveal:     ['none', 'fade', 'rise', 'stagger'],
  hover:      ['none', 'lift', 'glow'],
  intensity:  ['subtle', 'medium', 'bold'],
  nav:        ['top', 'bottom', 'drawer'],
  cardStyle:  ['standard', 'compact', 'overlay'],
  heroHeight: ['compact', 'tall']
}

// Defaults = look actual (tema claro, acento índigo, plantilla classic):
//   palette:   --store-accent/-ink/-soft + --sp-* del store-page.css
//              (bg y border son las mezclas ya resueltas a hex)
//   containers: --sp-radius 16px + --sp-shadow-sm + línea fina + card blanca
//   typography: --store-font 'inter' en todo; títulos 800 / -.02em
//   buttons:    .sp-btn — pill sólido accent-ink, 44–46px
//   background: --sp-bg plano (la aurora es del hero, no del fondo de página)
//   motion:     v-reveal (opacity+translate) y cards con translateY(-2px)
//   mobile:     .sp-top fijo, .sp-grid a 1 col, hero en banda
export const SITE_THEME_DEFAULTS = deepFreeze({
  palette: {
    primary: '#4f46e5',
    secondary: '#4338ca',
    accent: '#4f46e5',
    bg: '#eaeef8',
    surface: '#ffffff',
    text: '#0f172a',
    muted: '#5b6678',
    border: '#aeb3dc',
    success: '#059669',
    danger: '#dc2626'
  },
  containers: {
    radius: 'lg',
    shadow: 'soft',
    border: 'thin',
    density: 'comfortable',
    surface: 'elevated'
  },
  typography: {
    heading: 'inter',
    body: 'inter',
    scale: 'balanced',
    weightHeading: 800,
    letterSpacing: '-0.02em'
  },
  buttons: {
    shape: 'pill',
    style: 'solid',
    size: 'md'
  },
  background: {
    type: 'solid',
    value: null,
    overlay: 'none'
  },
  motion: {
    reveal: 'rise',
    hover: 'lift',
    intensity: 'subtle'
  },
  mobile: {
    nav: 'top',
    gridCols: 1,
    cardStyle: 'standard',
    stickyCta: false,
    heroHeight: 'compact'
  }
})

// Valores CSS concretos de cada enum (una sola fuente de verdad: los
// componentes jamás hardcodean su propia tabla).
const RADIUS_PX = { none: '0', sm: '6px', md: '10px', lg: '16px', xl: '24px', pill: '999px' }
const SHADOW_CSS = {
  none: 'none',
  soft: '0 1px 2px rgba(15, 23, 42, .08), 0 1px 1px rgba(15, 23, 42, .04)',
  medium: '0 1px 3px rgba(15, 23, 42, .08), 0 10px 28px -12px rgba(15, 23, 42, .28)',
  deep: '0 24px 60px -20px rgba(15, 23, 42, .45)'
}
const BORDER_PX = { none: '0', thin: '1px', bold: '2px' }
const DENSITY_CSS = {
  compact: { pad: '12px 14px', gap: '16px' },
  comfortable: { pad: '18px 20px', gap: '28px' },
  spacious: { pad: '28px 32px', gap: '44px' }
}
const SCALE_CSS = {
  compact: { h1: 'clamp(26px, 4vw, 36px)', h2: 'clamp(20px, 3vw, 26px)', base: '14px', leading: '1.45' },
  balanced: { h1: 'clamp(30px, 4.8vw, 50px)', h2: 'clamp(24px, 3.4vw, 34px)', base: '15px', leading: '1.5' },
  editorial: { h1: 'clamp(36px, 6vw, 64px)', h2: 'clamp(28px, 4vw, 44px)', base: '16px', leading: '1.6' }
}
const BTN_RADIUS = { square: '8px', rounded: '14px', pill: '999px' }
const BTN_SIZE = {
  sm: { h: '38px', px: '16px', fs: '13px' },
  md: { h: '46px', px: '22px', fs: '14.5px' },
  lg: { h: '54px', px: '28px', fs: '16px' }
}
const OVERLAY_CSS = { none: 'transparent', soft: 'rgba(9, 12, 24, .32)', strong: 'rgba(9, 12, 24, .6)' }
const MOTION_MS = { subtle: '160ms', medium: '240ms', bold: '360ms' }

// ---------------------------------------------------------------------------
// Saneo de valores
// ---------------------------------------------------------------------------

const HEX_RE = /^#?[0-9a-fA-F]{6}$/
const HEX3_RE = /^#?[0-9a-fA-F]{3}$/

export function normalizeHex(value) {
  if (typeof value !== 'string') return null
  const v = value.trim()
  if (HEX_RE.test(v)) return `#${v.replace('#', '').toLowerCase()}`
  if (HEX3_RE.test(v)) return `#${v.replace('#', '').toLowerCase().replace(/./g, (c) => c + c)}`
  return null
}

function pickEnum(list, value, fallback) {
  return list.includes(value) ? value : fallback
}

function pickCssText(value, fallback, max = 200) {
  return typeof value === 'string' && value.trim() && value.length <= max ? value.trim() : fallback
}

// ---------------------------------------------------------------------------
// resolveSiteTheme: merge profundo sobre defaults + saneo por campo.
// Acepta parciales de cualquier profundidad; nunca muta el input.
// ---------------------------------------------------------------------------

export function resolveSiteTheme(partial = {}) {
  const p = partial && typeof partial === 'object' ? partial : {}
  const d = SITE_THEME_DEFAULTS
  const pal = p.palette && typeof p.palette === 'object' ? p.palette : {}
  const con = p.containers && typeof p.containers === 'object' ? p.containers : {}
  const typ = p.typography && typeof p.typography === 'object' ? p.typography : {}
  const btn = p.buttons && typeof p.buttons === 'object' ? p.buttons : {}
  const bg = p.background && typeof p.background === 'object' ? p.background : {}
  const mo = p.motion && typeof p.motion === 'object' ? p.motion : {}
  const mb = p.mobile && typeof p.mobile === 'object' ? p.mobile : {}

  const palette = {}
  for (const key of Object.keys(d.palette)) {
    palette[key] = normalizeHex(pal[key]) || d.palette[key]
  }

  const weight = Number(typ.weightHeading)
  const cols = Number(mb.gridCols)

  const resolved = {
    palette,
    containers: {
      radius: pickEnum(STUDIO_ENUMS.radius, con.radius, d.containers.radius),
      shadow: pickEnum(STUDIO_ENUMS.shadow, con.shadow, d.containers.shadow),
      border: pickEnum(STUDIO_ENUMS.borderW, con.border, d.containers.border),
      density: pickEnum(STUDIO_ENUMS.density, con.density, d.containers.density),
      surface: pickEnum(STUDIO_ENUMS.surface, con.surface, d.containers.surface)
    },
    typography: {
      heading: pickCssText(typ.heading, d.typography.heading, 120),
      body: pickCssText(typ.body, d.typography.body, 120),
      scale: pickEnum(STUDIO_ENUMS.typeScale, typ.scale, d.typography.scale),
      weightHeading: Number.isFinite(weight) ? Math.min(900, Math.max(100, Math.round(weight))) : d.typography.weightHeading,
      letterSpacing: pickCssText(typ.letterSpacing, d.typography.letterSpacing, 16)
    },
    buttons: {
      shape: pickEnum(STUDIO_ENUMS.btnShape, btn.shape, d.buttons.shape),
      style: pickEnum(STUDIO_ENUMS.btnStyle, btn.style, d.buttons.style),
      size: pickEnum(STUDIO_ENUMS.btnSize, btn.size, d.buttons.size)
    },
    background: {
      type: pickEnum(STUDIO_ENUMS.bgType, bg.type, d.background.type),
      value: bg.value === null || bg.value === undefined || bg.value === '' ? null : pickCssText(bg.value, null, 600),
      overlay: pickEnum(STUDIO_ENUMS.overlay, bg.overlay, d.background.overlay)
    },
    motion: {
      reveal: pickEnum(STUDIO_ENUMS.reveal, mo.reveal, d.motion.reveal),
      hover: pickEnum(STUDIO_ENUMS.hover, mo.hover, d.motion.hover),
      intensity: pickEnum(STUDIO_ENUMS.intensity, mo.intensity, d.motion.intensity)
    },
    mobile: {
      nav: pickEnum(STUDIO_ENUMS.nav, mb.nav, d.mobile.nav),
      gridCols: cols === 2 ? 2 : 1,
      cardStyle: pickEnum(STUDIO_ENUMS.cardStyle, mb.cardStyle, d.mobile.cardStyle),
      stickyCta: mb.stickyCta === true,
      heroHeight: pickEnum(STUDIO_ENUMS.heroHeight, mb.heroHeight, d.mobile.heroHeight)
    }
  }
  // Juego de colores del estilo: solo viaja si el tema lo trae (parcial,
  // sembrado desde el preset elegido). Las claves ausentes se completan con
  // la derivación del palette para que un bloque incompleto no rompa.
  if (p.styleColors && typeof p.styleColors === 'object') {
    const block = {}
    for (const mode of STUDIO_STYLE_MODES) {
      const set = sanitizeStyleSet(p.styleColors[mode])
      if (!set) continue
      const derived = styleColorsFromPalette(palette, mode)
      block[mode] = {
        fonts: { ...derived.fonts, ...set.fonts },
        containers: { ...derived.containers, ...set.containers }
      }
    }
    if (Object.keys(block).length) resolved.styleColors = block
  }
  if (p.style && typeof p.style === 'object' && typeof p.style.id === 'string' && p.style.id.trim()) {
    resolved.style = { id: p.style.id.trim().slice(0, 60) }
    const paletteDef = STYLE_PALETTES.find((x) => x.id === p.style.palette)
    if (paletteDef && paletteDef.id !== 'original') resolved.style.palette = paletteDef.id
  }
  return resolved
}

// ---------------------------------------------------------------------------
// WCAG contraste (autosuficiente: misma fórmula que utils/colorTools.js)
// ---------------------------------------------------------------------------

export function hexToRgb(hex) {
  const h = String(hex).replace('#', '')
  const n = parseInt(h.length === 3 ? h.replace(/./g, '$&$&') : h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export function rgbToHex([r, g, b]) {
  return `#${[r, g, b].map((v) => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, '0')).join('')}`
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

// Acerca `fg` al extremo (negro o blanco) que mejor contraste con `bg` hasta
// alcanzar `min` (AA texto normal = 4.5). Devuelve hex #rrggbb.
export function fixContrast(fg, bg, min = 4.5) {
  const f = normalizeHex(fg)
  const b = normalizeHex(bg)
  if (!f || !b) return f || '#0f172a'
  if (contrastRatio(f, b) >= min) return f
  // El extremo con mejor contraste real (el cruce negro/blanco está en
  // L≈0.179, no en 0.5: un gris medio contrasta más con negro que con blanco).
  const target = contrastRatio('#000000', b) >= contrastRatio('#ffffff', b)
    ? [0, 0, 0]
    : [255, 255, 255]
  const rgb = hexToRgb(f)
  for (let t = 0.02; t <= 1.0001; t += 0.02) {
    const hex = rgbToHex(rgb.map((c, i) => c + (target[i] - c) * t))
    if (contrastRatio(hex, b) >= min) return hex
  }
  return rgbToHex(target)
}

// Texto garantizado legible sobre `bg` (para --st-on-primary y cía).
export function textOn(bg, min = 4.5) {
  const b = normalizeHex(bg) || '#ffffff'
  return contrastRatio('#ffffff', b) >= min ? '#ffffff' : fixContrast('#ffffff', b, min)
}

// ---------------------------------------------------------------------------
// Juego de colores del estilo: fuentes + contenedores por modo. El set
// "nativo" sale del palette del preset; el modo opuesto usa una base neutra
// (clara u oscura) con el acento del preset. Todo texto pasa AA contra
// containers.surface y containers.bg (fixContrast 4.5).
// ---------------------------------------------------------------------------

const STYLE_NEUTRAL = {
  light: { bg: '#f4f6fb', surface: '#ffffff', text: '#0f172a', muted: '#5b6678', border: '#e2e6f0' },
  dark: { bg: '#0b1220', surface: '#111a2c', text: '#f1f5f9', muted: '#94a3b8', border: '#243049' }
}

function paletteMode(palette) {
  return luminance(normalizeHex(palette?.bg) || '#ffffff') < 0.5 ? 'dark' : 'light'
}

// Contenedores/fuentes de cada paleta por modo. El acento NO vive acá: se
// toma del color elegido en Ajustes rápidos (se fusiona al derivar el set).
const STYLE_PALETTE_TINTS = {
  warm: {
    light: { bg: '#f7f2ea', surface: '#fffdf9', border: '#e3d9cb', text: '#1f1a14', muted: '#6b5f50' },
    dark: { bg: '#14100c', surface: '#1c1712', border: '#3a3027', text: '#f7f2ea', muted: '#bfae98' }
  },
  cool: {
    light: { bg: '#eef3f9', surface: '#ffffff', border: '#d9e3ee', text: '#0f172a', muted: '#5b6678' },
    dark: { bg: '#0b1220', surface: '#111a2c', border: '#243049', text: '#e6ecf7', muted: '#94a3b8' }
  },
  contrast: {
    light: { bg: '#ffffff', surface: '#ffffff', border: '#111827', text: '#000000', muted: '#374151' },
    dark: { bg: '#000000', surface: '#0a0a0a', border: '#e5e7eb', text: '#ffffff', muted: '#d1d5db' }
  }
}

// Set de un modo para una paleta elegida (original = la del estilo). El
// acento opcional pisa el del preset y se garantiza AA por fixContrast.
export function stylePaletteColors(palette, paletteId = 'original', mode = 'light', accent = null) {
  const target = mode === 'dark' ? 'dark' : 'light'
  const p = palette && typeof palette === 'object' ? palette : SITE_THEME_DEFAULTS.palette
  const tint = STYLE_PALETTE_TINTS[paletteId]?.[target]
  const accentHex = normalizeHex(accent)
  const base = tint
    ? { ...STYLE_NEUTRAL[target], ...tint, accent: accentHex || p.accent }
    : { ...p, ...(accentHex ? { accent: accentHex } : {}) }
  return styleColorsFromPalette(base, target)
}

function legibleOn(fg, bg, surface) {
  let out = fixContrast(fg, bg, 4.5)
  out = fixContrast(out, surface, 4.5)
  if (contrastRatio(out, bg) < 4.5) out = fixContrast(out, bg, 4.5)
  return out
}

export function styleColorsFromPalette(palette = SITE_THEME_DEFAULTS.palette, mode = 'light') {
  const target = mode === 'dark' ? 'dark' : 'light'
  const p = palette && typeof palette === 'object' ? palette : {}
  const base = paletteMode(p) === target
    ? { bg: p.bg, surface: p.surface, text: p.text, muted: p.muted, border: p.border, accent: p.accent }
    : { ...STYLE_NEUTRAL[target], accent: p.accent }
  const bg = normalizeHex(base.bg) || STYLE_NEUTRAL[target].bg
  const surface = normalizeHex(base.surface) || STYLE_NEUTRAL[target].surface
  const text = normalizeHex(base.text) || STYLE_NEUTRAL[target].text
  const muted = normalizeHex(base.muted) || STYLE_NEUTRAL[target].muted
  const border = normalizeHex(base.border) || STYLE_NEUTRAL[target].border
  const accent = normalizeHex(base.accent) || SITE_THEME_DEFAULTS.palette.accent
  const heading = legibleOn(text, bg, surface)
  return {
    fonts: {
      heading,
      body: heading,
      muted: legibleOn(muted, bg, surface),
      link: legibleOn(accent, bg, surface)
    },
    containers: { bg, surface, border, onSurface: heading }
  }
}

export function styleColorsBlock(palette = SITE_THEME_DEFAULTS.palette, paletteId = 'original', accent = null) {
  return {
    light: stylePaletteColors(palette, paletteId, 'light', accent),
    dark: stylePaletteColors(palette, paletteId, 'dark', accent)
  }
}

// Sanea un set (enum cerrado de claves + hex). null = no había nada válido.
export function sanitizeStyleSet(raw) {
  if (!raw || typeof raw !== 'object') return null
  const fonts = raw.fonts && typeof raw.fonts === 'object' ? raw.fonts : {}
  const con = raw.containers && typeof raw.containers === 'object' ? raw.containers : {}
  const out = { fonts: {}, containers: {} }
  let any = false
  for (const key of STYLE_FONT_KEYS) {
    const hex = normalizeHex(fonts[key])
    if (hex) { out.fonts[key] = hex; any = true }
  }
  for (const key of STYLE_CONTAINER_KEYS) {
    const hex = normalizeHex(con[key])
    if (hex) { out.containers[key] = hex; any = true }
  }
  return any ? out : null
}

// Set del modo pedido para un tema (resuelto o parcial). Sin bloque, se
// deriva del palette: el preset se ve igual que hoy.
export function resolveStyleColors(theme, mode = 'light') {
  const t = theme && typeof theme === 'object' ? theme : {}
  const key = mode === 'dark' ? 'dark' : 'light'
  const set = sanitizeStyleSet(t.styleColors?.[key])
  const palette = resolveSiteTheme(t).palette
  if (!set) return styleColorsFromPalette(palette, key)
  const derived = styleColorsFromPalette(palette, key)
  return {
    fonts: { ...derived.fonts, ...set.fonts },
    containers: { ...derived.containers, ...set.containers }
  }
}

// ---------------------------------------------------------------------------
// themeToCssVars: tema resuelto -> '--st-*' para :style en el contenedor.
// resolveFont: opcional — pasar storeFontFamily (stores.api.js) para que los
// slugs del catálogo salgan como familia real; un valor con ','/'"' ya se
// considera stack CSS y viaja tal cual.
// ---------------------------------------------------------------------------

function fontOf(value, resolveFont) {
  const v = String(value || '').trim()
  if (!v) return 'Inter, system-ui, sans-serif'
  if (v.includes(',') || v.includes("'") || v.includes('"')) return v
  return typeof resolveFont === 'function' ? resolveFont(v) : v
}

export function themeToCssVars(theme, resolveFont, mode = 'light') {
  const t = resolveSiteTheme(theme)
  const p = t.palette
  const style = resolveStyleColors(t, mode)
  const scale = SCALE_CSS[t.typography.scale]
  const density = DENSITY_CSS[t.containers.density]
  const btn = BTN_SIZE[t.buttons.size]
  const bgv = t.background

  let bgLayer = 'none'
  if (bgv.type === 'image' && bgv.value) bgLayer = `url("${bgv.value.replace(/"/g, '%22')}")`
  else if (bgv.value && bgv.type !== 'solid') bgLayer = bgv.value

  return {
    '--st-primary': p.primary,
    '--st-secondary': p.secondary,
    '--st-accent': p.accent,
    '--st-primary-soft': `color-mix(in srgb, ${p.primary} 10%, #fff)`,
    '--st-bg': p.bg,
    '--st-surface': p.surface,
    '--st-text': p.text,
    '--st-muted': p.muted,
    '--st-border': p.border,
    '--st-success': p.success,
    '--st-danger': p.danger,
    '--st-on-primary': textOn(p.primary),
    '--st-on-secondary': textOn(p.secondary),
    '--st-radius': RADIUS_PX[t.containers.radius],
    '--st-shadow': SHADOW_CSS[t.containers.shadow],
    '--st-border-w': BORDER_PX[t.containers.border],
    '--st-card-pad': density.pad,
    '--st-section-gap': density.gap,
    '--st-font-heading': fontOf(t.typography.heading, resolveFont),
    '--st-font-body': fontOf(t.typography.body, resolveFont),
    '--st-h1-size': scale.h1,
    '--st-h2-size': scale.h2,
    '--st-text-size': scale.base,
    '--st-leading': scale.leading,
    '--st-weight-heading': String(t.typography.weightHeading),
    '--st-tracking': t.typography.letterSpacing,
    '--st-btn-radius': BTN_RADIUS[t.buttons.shape],
    '--st-btn-h': btn.h,
    '--st-btn-px': btn.px,
    '--st-btn-fs': btn.fs,
    '--st-bg-layer': bgLayer,
    '--st-bg-overlay': OVERLAY_CSS[t.background.overlay],
    '--st-motion-dur': MOTION_MS[t.motion.intensity],
    '--st-grid-cols': String(t.mobile.gridCols),
    '--st-style-font-heading': style.fonts.heading,
    '--st-style-font-body': style.fonts.body,
    '--st-style-font-muted': style.fonts.muted,
    '--st-style-font-link': style.fonts.link,
    '--st-style-container-bg': style.containers.bg,
    '--st-style-container-surface': style.containers.surface,
    '--st-style-container-border': style.containers.border,
    '--st-style-container-on-surface': style.containers.onSurface
  }
}

// ---------------------------------------------------------------------------
// Claves realmente presentes en un site_theme parcial ('seccion.clave').
// La web publicada guarda solo lo que el usuario eligió (el merge con los
// defaults corre al render); con esto el consumo CSS sabe qué campos puede
// pisar: una clave ausente deja el fallback de la hoja intacto, así una
// tienda sin tema —o con un tema parcial— conserva el look de su plantilla.
// ---------------------------------------------------------------------------
const THEME_SECTION_KEYS = {
  palette: Object.keys(SITE_THEME_DEFAULTS.palette),
  containers: Object.keys(SITE_THEME_DEFAULTS.containers),
  typography: Object.keys(SITE_THEME_DEFAULTS.typography),
  buttons: Object.keys(SITE_THEME_DEFAULTS.buttons),
  background: Object.keys(SITE_THEME_DEFAULTS.background),
  motion: Object.keys(SITE_THEME_DEFAULTS.motion),
  mobile: Object.keys(SITE_THEME_DEFAULTS.mobile)
}

export function themeExplicitKeys(partial) {
  const out = new Set()
  if (!partial || typeof partial !== 'object') return out
  for (const [section, keys] of Object.entries(THEME_SECTION_KEYS)) {
    const content = partial[section]
    if (!content || typeof content !== 'object') continue
    for (const key of keys) {
      if (content[key] !== undefined && content[key] !== null) out.add(`${section}.${key}`)
    }
  }
  // Bloques anidados: viajan como una sola clave (el juego de colores se
  // elige entero por modo).
  if (partial.styleColors && typeof partial.styleColors === 'object'
    && Object.keys(partial.styleColors).length) out.add('styleColors')
  if (partial.style && typeof partial.style === 'object' && partial.style.id) out.add('style.id')
  return out
}

// Variable CSS del contrato -> campo(s) que la justifican. themeToCssVars
// emite siempre el set completo; quien pinta con un tema parcial (la web
// publicada) filtra con esto para no pisar tokens de la plantilla.
export const STUDIO_VAR_KEYS = {
  '--st-primary': ['palette.primary'],
  '--st-primary-soft': ['palette.primary'],
  '--st-on-primary': ['palette.primary'],
  '--st-secondary': ['palette.secondary'],
  '--st-on-secondary': ['palette.secondary'],
  '--st-accent': ['palette.accent'],
  '--st-bg': ['palette.bg'],
  '--st-surface': ['palette.surface'],
  '--st-text': ['palette.text'],
  '--st-muted': ['palette.muted'],
  '--st-border': ['palette.border'],
  '--st-success': ['palette.success'],
  '--st-danger': ['palette.danger'],
  '--st-radius': ['containers.radius'],
  '--st-shadow': ['containers.shadow'],
  '--st-border-w': ['containers.border'],
  '--st-card-pad': ['containers.density'],
  '--st-section-gap': ['containers.density'],
  '--st-font-heading': ['typography.heading'],
  '--st-font-body': ['typography.body'],
  '--st-h1-size': ['typography.scale'],
  '--st-h2-size': ['typography.scale'],
  '--st-text-size': ['typography.scale'],
  '--st-leading': ['typography.scale'],
  '--st-weight-heading': ['typography.weightHeading'],
  '--st-tracking': ['typography.letterSpacing'],
  '--st-btn-radius': ['buttons.shape'],
  '--st-btn-h': ['buttons.size'],
  '--st-btn-px': ['buttons.size'],
  '--st-btn-fs': ['buttons.size'],
  '--st-bg-layer': ['background.type', 'background.value'],
  '--st-bg-overlay': ['background.overlay'],
  '--st-motion-dur': ['motion.intensity'],
  '--st-grid-cols': ['mobile.gridCols'],
  '--st-style-font-heading': ['styleColors'],
  '--st-style-font-body': ['styleColors'],
  '--st-style-font-muted': ['styleColors'],
  '--st-style-font-link': ['styleColors'],
  '--st-style-container-bg': ['styleColors'],
  '--st-style-container-surface': ['styleColors'],
  '--st-style-container-border': ['styleColors'],
  '--st-style-container-on-surface': ['styleColors']
}

// Filtra el set completo de themeToCssVars a las variables cuyo campo está
// presente. `explicit` null = set completo (contrato / presets / preview
// sin seguimiento, comportamiento histórico).
export function pickThemeVars(vars, explicit = null) {
  if (!explicit) return { ...vars }
  const keys = explicit instanceof Set ? explicit : new Set(explicit)
  const out = {}
  for (const [name, fields] of Object.entries(STUDIO_VAR_KEYS)) {
    if (fields.some((f) => keys.has(f)) && vars[name] !== undefined) out[name] = vars[name]
  }
  return out
}

// Variantes discretas (no son valores CSS): van como atributos data-st-* en
// el contenedor para que el CSS seleccione por [data-st-btn-style='ghost'].
// Con `explicit`, solo viaja la variante de un campo elegido: sin el
// atributo el CSS no toca el look de la plantilla.
export function themeDataAttrs(theme, explicit = null, mode = 'light') {
  const t = resolveSiteTheme(theme)
  const keys = explicit ? (explicit instanceof Set ? explicit : new Set(explicit)) : null
  const on = (key) => !keys || keys.has(key)
  return {
    'data-st-style': on('styleColors') ? (mode === 'dark' ? 'dark' : 'light') : null,
    'data-st-surface': on('containers.surface') ? t.containers.surface : null,
    'data-st-density': on('containers.density') ? t.containers.density : null,
    'data-st-radius': on('containers.radius') ? t.containers.radius : null,
    'data-st-border': on('containers.border') ? t.containers.border : null,
    'data-st-shadow': on('containers.shadow') ? t.containers.shadow : null,
    'data-st-grid': on('mobile.gridCols') ? String(t.mobile.gridCols) : null,
    'data-st-brand': on('palette.primary') || on('palette.accent') ? '' : null,
    'data-st-font-heading': on('typography.heading') ? '' : null,
    'data-st-font-body': on('typography.body') ? '' : null,
    'data-st-scale': on('typography.scale') ? '' : null,
    'data-st-weight': on('typography.weightHeading') ? '' : null,
    'data-st-tracking': on('typography.letterSpacing') ? '' : null,
    'data-st-btn-shape': on('buttons.shape') ? '' : null,
    'data-st-btn-size': on('buttons.size') ? '' : null,
    'data-st-btn-style': on('buttons.style') ? t.buttons.style : null,
    'data-st-bgtype': on('background.type') ? t.background.type : null,
    'data-st-palette': on('palette.text') || on('palette.muted') || on('palette.surface') || on('palette.border') || on('palette.bg') || on('palette.accent') || on('palette.primary') ? '' : null,
    'data-st-bgrole': on('palette.bg') ? '' : null,
    'data-st-reveal': on('motion.reveal') ? t.motion.reveal : null,
    'data-st-hover': on('motion.hover') ? t.motion.hover : null,
    'data-st-nav': on('mobile.nav') ? t.mobile.nav : null,
    'data-st-card': on('mobile.cardStyle') ? t.mobile.cardStyle : null,
    'data-st-hero': on('mobile.heroHeight') ? t.mobile.heroHeight : null,
    'data-st-sticky-cta': on('mobile.stickyCta') && t.mobile.stickyCta ? 'true' : null
  }
}

// ---------------------------------------------------------------------------
// studioPreset: preset aplicable del catálogo del Studio.
//   { id, name, category, preview, tier, template, theme, layout }
// preview: miniatura — hex, gradiente CSS o URL de imagen.
// layout: misma forma que customization.layout_config (la whitelist de ids
// y variantes la fuerza clean_layout_config en el backend).
// ---------------------------------------------------------------------------

export function resolveStudioPreset(preset = {}) {
  const p = preset && typeof preset === 'object' ? preset : {}
  const id = String(p.id || p.name || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
  const layout = {}
  const src = p.layout && typeof p.layout === 'object' ? p.layout : {}
  for (const surface of STUDIO_SURFACES) {
    const blocks = Array.isArray(src[surface]?.blocks) ? src[surface].blocks : []
    layout[surface] = {
      blocks: blocks
        .filter((b) => b && typeof b === 'object' && typeof b.id === 'string' && b.id)
        .map((b, i) => ({
          id: b.id.slice(0, 60),
          enabled: b.enabled !== false,
          order: Number.isFinite(Number(b.order)) ? Number(b.order) : i,
          ...(typeof b.variant === 'string' && b.variant ? { variant: b.variant.slice(0, 40) } : {}),
          ...(b.props && typeof b.props === 'object' ? { props: b.props } : {})
        }))
    }
  }
  return {
    id: id || 'preset',
    name: pickCssText(p.name, 'Preset', 60),
    category: pickCssText(p.category, 'general', 40),
    preview: pickCssText(p.preview, null, 600),
    tier: pickEnum(STUDIO_TIERS, p.tier, 'base'),
    template: pickCssText(p.template, 'classic', 40),
    theme: resolveSiteTheme(p.theme || p.siteTheme || {}),
    layout
  }
}

// Payload para PATCH /api/stores/customization/. `site_theme` todavía no es
// campo del modelo: el serializer lo ignora (DRF descarta claves no
// declaradas) hasta que la fase backend lo habilite — quien aplique el
// preset mientras tanto usa `theme` solo para la vista previa.
export function presetToPatch(preset) {
  const p = resolveStudioPreset(preset)
  return {
    template: p.template,
    layout_config: p.layout,
    site_theme: { ...p.theme, style: { id: p.id } }
  }
}

// ---------------------------------------------------------------------------
// Protocolo postMessage Studio <-> iframe de vista previa (same-origin).
//   studio:ready   iframe -> host  al montar: el host responde con update
//   studio:update  host -> iframe  { type, theme, layout, template, device }
//   studio:focus   ambos sentidos  { type, target }  (resaltar/seleccionar
//                  un bloque o sección; target = data-blk o selector)
// ---------------------------------------------------------------------------

export const STUDIO_MSG = {
  READY: 'studio:ready',
  UPDATE: 'studio:update',
  FOCUS: 'studio:focus'
}

export function studioUpdate({ theme, layout, template, device } = {}) {
  return {
    type: STUDIO_MSG.UPDATE,
    theme: resolveSiteTheme(theme),
    layout: layout && typeof layout === 'object' ? layout : {},
    template: pickCssText(template, 'classic', 40),
    device: pickEnum(STUDIO_DEVICES, device, 'desktop')
  }
}

export function studioFocus(target) {
  return { type: STUDIO_MSG.FOCUS, target: pickCssText(target, '', 200) }
}

export function studioReady() {
  return { type: STUDIO_MSG.READY }
}

export function isStudioMessage(data) {
  return Boolean(data && typeof data === 'object' && typeof data.type === 'string' && data.type.startsWith('studio:'))
}

function deepFreeze(obj) {
  if (obj && typeof obj === 'object') {
    for (const v of Object.values(obj)) deepFreeze(v)
    Object.freeze(obj)
  }
  return obj
}
