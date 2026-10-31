// Verificación del contrato del Studio (sin runner de tests en el proyecto):
//   node scripts/verify-studio-contract.mjs    (o npm run verify:studio)
// Corre en node puro — contract.js es autocontenido justamente para esto.

import {
  SITE_THEME_DEFAULTS, STUDIO_ENUMS, STUDIO_MSG, STUDIO_SURFACES,
  resolveSiteTheme, themeToCssVars, themeDataAttrs, themeExplicitKeys, pickThemeVars,
  contrastRatio, fixContrast, textOn, normalizeHex,
  resolveStudioPreset, presetToPatch,
  studioUpdate, studioFocus, studioReady, isStudioMessage
} from '../src/studio/contract.js'
import {
  analyzeStudioHealth, repairPalette, palettePasses, CONTRAST_PAIRS, pairColors
} from '../src/components/studio/health.js'
import { bandPalette, adaptPalette } from '../src/utils/colorTools.js'
import { patternChoice, styleChoice, iconChoice, savePayloadPlan } from '../src/studio/designChoice.js'

let failures = 0
function check(name, cond, extra = '') {
  if (cond) console.log(`  ok   ${name}`)
  else { failures++; console.error(`  FAIL ${name} ${extra}`) }
}
function eq(name, a, b) {
  check(name, JSON.stringify(a) === JSON.stringify(b), `\n     got: ${JSON.stringify(a)}\n     exp: ${JSON.stringify(b)}`)
}
const near = (name, a, b, eps = 0.05) => check(name, Math.abs(a - b) <= eps, `got ${a} exp ~${b}`)

console.log('— resolveSiteTheme —')
eq('sin parcial devuelve los defaults', resolveSiteTheme(), SITE_THEME_DEFAULTS)
eq('null/undefined/string caen a defaults', resolveSiteTheme(null), SITE_THEME_DEFAULTS)
const merged = resolveSiteTheme({ palette: { primary: '#FF0000' } })
check('merge parcial conserva el resto', merged.palette.primary === '#ff0000' && merged.palette.bg === SITE_THEME_DEFAULTS.palette.bg && merged.containers.radius === 'lg')
check('normaliza hex a minúsculas', merged.palette.primary === '#ff0000')
eq('hex inválido -> default', resolveSiteTheme({ palette: { accent: 'rojo' } }).palette.accent, SITE_THEME_DEFAULTS.palette.accent)
eq('hex de 3 dígitos se expande', resolveSiteTheme({ palette: { primary: '#f00' } }).palette.primary, '#ff0000')
eq('enum inválido -> default', resolveSiteTheme({ containers: { radius: 'gigante' } }).containers.radius, 'lg')
eq('enum en mayúsculas -> default', resolveSiteTheme({ buttons: { style: 'SOLID' } }).buttons.style, 'solid')
eq('weightHeading clampea', resolveSiteTheme({ typography: { weightHeading: 1200 } }).typography.weightHeading, 900)
eq('weightHeading inválido -> default', resolveSiteTheme({ typography: { weightHeading: 'x' } }).typography.weightHeading, 800)
eq('gridCols solo admite 1|2', resolveSiteTheme({ mobile: { gridCols: 3 } }).mobile.gridCols, 1)
eq('gridCols 2 se conserva', resolveSiteTheme({ mobile: { gridCols: 2 } }).mobile.gridCols, 2)
eq('stickyCta inválido -> false', resolveSiteTheme({ mobile: { stickyCta: 'si' } }).mobile.stickyCta, false)
const input = { palette: { primary: '#123456' } }
resolveSiteTheme(input)
eq('no muta el input', input, { palette: { primary: '#123456' } })
try { SITE_THEME_DEFAULTS.palette.primary = '#000'; check('defaults congelados', SITE_THEME_DEFAULTS.palette.primary === '#4f46e5') } catch { check('defaults congelados (strict)', true) }

console.log('— contraste WCAG —')
near('blanco/negro = 21', contrastRatio('#ffffff', '#000000'), 21)
near('mismo color = 1', contrastRatio('#4f46e5', '#4f46e5'), 1)
check('body claro sobre indigo AA', contrastRatio('#ffffff', '#4338ca') >= 4.5)
eq('ya conforme no se toca', fixContrast('#0f172a', '#ffffff'), '#0f172a')
check('blanco sobre blanco -> alcanza AA', contrastRatio(fixContrast('#ffffff', '#ffffff'), '#ffffff') >= 4.5)
check('negro sobre negro -> alcanza AA', contrastRatio(fixContrast('#000000', '#000000'), '#000000') >= 4.5)
check('acento sobre bg -> alcanza 3:1 (gráficos)', contrastRatio(fixContrast('#eaeef8', '#eaeef8', 3), '#eaeef8') >= 3)
eq('textOn sobre oscuro da blanco', textOn('#0f172a'), '#ffffff')
check('textOn sobre claro da legible', contrastRatio(textOn('#ffffff'), '#ffffff') >= 4.5)
eq('normalizeHex acepta #RGB', normalizeHex('#ABC'), '#aabbcc')
eq('normalizeHex rechaza basura', normalizeHex('red'), null)

console.log('— themeToCssVars —')
const vars = themeToCssVars({ containers: { radius: 'pill' }, typography: { heading: 'oswald' } }, (k) => ({ oswald: 'Oswald, sans-serif' }[k] || 'Inter, system-ui, sans-serif'))
eq('radius pill -> 999px', vars['--st-radius'], '999px')
eq('shadow soft es la actual', vars['--st-shadow'], '0 1px 2px rgba(15, 23, 42, .08), 0 1px 1px rgba(15, 23, 42, .04)')
eq('slug de fuente vía resolver', vars['--st-font-heading'], 'Oswald, sans-serif')
eq('stack CSS viaja tal cual', themeToCssVars({ typography: { heading: "'Mi Fonta', serif" } })['--st-font-heading'], "'Mi Fonta', serif")
eq('bg image -> url()', themeToCssVars({ background: { type: 'image', value: 'https://x.test/a.webp' } })['--st-bg-layer'], 'url("https://x.test/a.webp")')
eq('gradient viaja como capa', themeToCssVars({ background: { type: 'gradient', value: 'linear-gradient(red, blue)' } })['--st-bg-layer'], 'linear-gradient(red, blue)')
eq('overlay strong', themeToCssVars({ background: { overlay: 'strong' } })['--st-bg-overlay'], 'rgba(9, 12, 24, .6)')
eq('gridCols -> --st-grid-cols', themeToCssVars({ mobile: { gridCols: 2 } })['--st-grid-cols'], '2')
check('emite todo el set --st-*', ['--st-primary', '--st-bg', '--st-surface', '--st-text', '--st-muted', '--st-border', '--st-success', '--st-danger', '--st-on-primary', '--st-radius', '--st-shadow', '--st-border-w', '--st-card-pad', '--st-section-gap', '--st-font-heading', '--st-font-body', '--st-h1-size', '--st-h2-size', '--st-text-size', '--st-leading', '--st-weight-heading', '--st-tracking', '--st-btn-radius', '--st-btn-h', '--st-btn-px', '--st-btn-fs', '--st-bg-layer', '--st-bg-overlay', '--st-motion-dur', '--st-grid-cols'].every((k) => typeof vars[k] === 'string' && vars[k] !== ''))

console.log('— themeDataAttrs —')
const attrs = themeDataAttrs({ containers: { surface: 'glass' }, buttons: { style: 'gradient' }, motion: { reveal: 'stagger' }, mobile: { stickyCta: true } })
eq('variantes a data-st-*', { 'data-st-surface': attrs['data-st-surface'], 'data-st-btn-style': attrs['data-st-btn-style'], 'data-st-reveal': attrs['data-st-reveal'] }, { 'data-st-surface': 'glass', 'data-st-btn-style': 'gradient', 'data-st-reveal': 'stagger' })
eq('stickyCta true -> "true"', attrs['data-st-sticky-cta'], 'true')
eq('stickyCta false -> null (omitir)', themeDataAttrs({})['data-st-sticky-cta'], null)

console.log('— tema parcial: claves explícitas —')
const partial = { containers: { radius: 'xl' }, palette: { accent: '#ff0000' }, mobile: { stickyCta: false } }
const keys = themeExplicitKeys(partial)
eq('detecta solo lo presente', [...keys].sort(), ['containers.radius', 'mobile.stickyCta', 'palette.accent'])
check('ignora secciones vacías', themeExplicitKeys({ containers: {} }).size === 0)
check('null no cuenta como elegido', !themeExplicitKeys({ background: { value: null } }).has('background.value'))
const full = themeToCssVars(partial)
const only = pickThemeVars(full, keys)
eq('filtra vars a los campos elegidos', Object.keys(only).sort(), ['--st-accent', '--st-on-accent', '--st-radius'])
eq('radius explícito llega', only['--st-radius'], '24px')
eq('sin explícitas = set completo', Object.keys(pickThemeVars(full)).length, Object.keys(full).length)
const attrsOnly = themeDataAttrs(partial, keys)
eq('atributo de campo elegido', attrsOnly['data-st-radius'], 'xl')
eq('atributo de campo ausente se omite', attrsOnly['data-st-surface'], null)
eq('stickyCta false no emite atributo', attrsOnly['data-st-sticky-cta'], null)
check('sin tema no hay atributos', Object.values(themeDataAttrs({}, new Set())).every((v) => v === null))

console.log('— studioPreset —')
const preset = resolveStudioPreset({
  name: 'Serena Índigo', category: 'belleza', tier: 'plus', template: 'calma',
  preview: 'linear-gradient(#fff, #eee)',
  theme: { palette: { primary: '#7c3aed' } },
  layout: {
    landing: { blocks: [
      { id: 'hero', enabled: true, order: 0, variant: 'full' },
      { id: 'offers', enabled: false },
      { id: '', enabled: true },
      'basura'
    ] },
    extra: { blocks: [{ id: 'x' }] }
  }
})
eq('id slug con acentos', preset.id, 'serena-indigo')
eq('category', preset.category, 'belleza')
eq('tier válido', preset.tier, 'plus')
eq('tier inválido -> base', resolveStudioPreset({ tier: 'oro' }).tier, 'base')
eq('template libre (whitelist del backend)', preset.template, 'calma')
eq('theme parcial resuelto', preset.theme.palette.primary, '#7c3aed')
eq('layout: bloques sin id descartados', preset.layout.landing.blocks.map((b) => b.id), ['hero', 'offers'])
eq('layout: order implícito', preset.layout.landing.blocks[1].order, 1)
eq('layout: variant conservada', preset.layout.landing.blocks[0].variant, 'full')
check('layout: solo superficies conocidas', Object.keys(preset.layout).join(',') === STUDIO_SURFACES.join(',') && !('extra' in preset.layout))
eq('preset vacío sanea', resolveStudioPreset().id, 'preset')
const patch = presetToPatch(preset)
check('presetToPatch emite template+layout+site_theme', patch.template === 'calma' && patch.layout_config === patch.layout_config && patch.site_theme.palette.primary === '#7c3aed')
eq('patch.template', patch.template, 'calma')

console.log('— protocolo postMessage —')
const upd = studioUpdate({ theme: { palette: { primary: '#123123' } }, template: 'street', device: 'mobile' })
eq('update.type', upd.type, STUDIO_MSG.UPDATE)
eq('update.theme resuelto', upd.theme.palette.primary, '#123123')
eq('update.device enum', upd.device, 'mobile')
eq('device inválido -> desktop', studioUpdate({ device: 'watch' }).device, 'desktop')
eq('focus', studioFocus('contact'), { type: STUDIO_MSG.FOCUS, target: 'contact' })
eq('ready', studioReady(), { type: STUDIO_MSG.READY })
check('isStudioMessage', isStudioMessage(upd) && isStudioMessage(studioFocus('x')) && !isStudioMessage({ type: 'otro' }) && !isStudioMessage(null) && !isStudioMessage('studio:update'))

console.log('— salud de la web (health.js) —')
const CONTRAST_KEYS = CONTRAST_PAIRS.map((p) => p.key)
const contrastIssues = (issues) => issues.filter((i) => i.id.startsWith('contrast-'))
function healthOf(theme, extra = {}) {
  return analyzeStudioHealth({ theme, form: {}, layout: null, ...extra })
}
function applyPaletteFix(palette, issues) {
  const next = { ...palette }
  for (const i of issues) {
    if (i.fix?.kind === 'palette') Object.assign(next, i.fix.values)
  }
  return next
}
function ratiosOk(palette) {
  return CONTRAST_PAIRS.every((pair) => {
    const { fg, bg } = pairColors(pair, palette)
    return contrastRatio(fg, bg) >= pair.min
  })
}
function isHexPalette(palette) {
  return Object.keys(SITE_THEME_DEFAULTS.palette).every((k) => normalizeHex(palette[k]) !== null)
}

// PRNG determinista (mulberry32) para reproducir las paletas aleatorias.
function rng(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6D2B79F5) >>> 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const randHex = (r) => `#${[0, 0, 0].map(() => Math.floor(r() * 256).toString(16).padStart(2, '0')).join('')}`
function randomPalette(r, dark) {
  const base = {
    primary: randHex(r),
    secondary: randHex(r),
    accent: randHex(r),
    bg: dark ? '#0b1020' : '#f4f6fb',
    surface: dark ? '#121a2b' : '#ffffff',
    text: dark ? '#f1f5fb' : '#0f172a',
    muted: randHex(r),
    border: randHex(r),
    success: '#059669',
    danger: '#dc2626'
  }
  // Algunos roles llegan corruptos: el saneo del contrato los devuelve a un
  // hex válido y la reparación no puede dejarlos fuera del catálogo.
  if (r() < 0.35) base.bg = 'no-es-un-color'
  if (r() < 0.25) base.surface = 'rgb(1,2,3)'
  if (r() < 0.3) base.text = '#12'
  return base
}

let randomFailures = 0
let regressionFailures = 0
for (let n = 0; n < 60; n += 1) {
  const r = rng(1000 + n)
  const palette = randomPalette(r, n % 2 === 1)
  let cur = { ...palette }
  for (let pass = 0; pass < 5; pass += 1) {
    const issues = healthOf({ palette: cur }).filter((i) => i.fix?.kind === 'palette')
    if (!issues.length) break
    const before = cur
    const fixed = applyPaletteFix(cur, issues)
    // Ningún fix puede dejar un par que antes pasaba por debajo del umbral.
    const merged = { ...SITE_THEME_DEFAULTS.palette, ...before, ...fixed }
    if (!ratiosOk(merged)) regressionFailures += 1
    if (JSON.stringify(fixed) === JSON.stringify(before)) { randomFailures += 1; break }
    cur = fixed
  }
  const left = contrastIssues(healthOf({ palette: cur }))
  if (left.length) randomFailures += 1
  if (!isHexPalette({ ...SITE_THEME_DEFAULTS.palette, ...cur })) randomFailures += 1
}
check('60 paletas aleatorias convergen a 0 hallazgos de contraste', randomFailures === 0, `fallas: ${randomFailures}`)
check('ningún arreglo deja pares por debajo del umbral', regressionFailures === 0, `fallas: ${regressionFailures}`)

const fixedDark = repairPalette({ ...SITE_THEME_DEFAULTS.palette, bg: '#0b1020', surface: '#121a2b', text: '#111111', muted: '#222222' })
check('paleta oscura repara texto y secundarios', ratiosOk(fixedDark))
check('reparar dos veces es idempotente', JSON.stringify(repairPalette(fixedDark)) === JSON.stringify(fixedDark))
const midPrimary = repairPalette({ ...SITE_THEME_DEFAULTS.palette, primary: '#808080', accent: '#808080' })
check('gris medio como primario converge', ratiosOk(midPrimary))

const noCatalog = analyzeStudioHealth({
  theme: { ...SITE_THEME_DEFAULTS, palette: SITE_THEME_DEFAULTS.palette },
  form: { site_templates: ['catalog', 'services'] },
  layout: {
    landing: { blocks: [{ id: 'featured', enabled: true }] },
    catalog: { blocks: [{ id: 'grid', enabled: true }, { id: 'promo', enabled: true }] },
    services: { blocks: [{ id: 'band', enabled: true }] }
  },
  catalogLoaded: false,
  servicesLoaded: false,
  products: [],
  categories: [],
  servicesCount: 0
})
check('catálogo/servicios sin cargar no reportan secciones vacías', !noCatalog.some((i) => i.id.startsWith('empty-')), JSON.stringify(noCatalog.map((i) => i.id)))

const noLayout = analyzeStudioHealth({
  theme: { ...SITE_THEME_DEFAULTS, palette: SITE_THEME_DEFAULTS.palette },
  form: { site_templates: ['catalog', 'services'] },
  layout: null,
  catalogLoaded: true,
  servicesLoaded: true,
  products: [],
  categories: [],
  servicesCount: 0
})
check('sin layout no se ofrecen fixes de bloque', !noLayout.some((i) => i.fix?.kind === 'block'), JSON.stringify(noLayout.map((i) => i.fix?.kind || null)))
check('todos los pares de contraste tienen clave única', new Set(CONTRAST_KEYS).size === CONTRAST_KEYS.length)
check('palettePasses acepta la paleta default', palettePasses(SITE_THEME_DEFAULTS.palette))

console.log('— banda de acento (nombre de la empresa legible) —')
for (const accent of ['#eab308', '#38bdf8', '#4ade80', '#00e67a', '#e11d48', '#4f46e5', '#000000', '#ffffff', 'no-es-color']) {
  const band = bandPalette(accent)
  const layers = ['c1', 'c2', 'c3', 'c4', 'base1', 'base2']
  check(`banda ${accent} mantiene texto blanco AA`, layers.every((k) => contrastRatio('#ffffff', band[k]) >= 4.5),
    JSON.stringify(band))
  check(`marca de acento ${accent} legible sobre el velo`, contrastRatio(band.mark, '#0d1220') >= 3,
    `${band.mark}`)
}

console.log('— cambio de modo claro/oscuro —')
const lightPal = { ...SITE_THEME_DEFAULTS.palette, bg: '#fafaf9', surface: '#ffffff', text: '#0f172a', muted: '#5b6678' }
const darkPal = adaptPalette(lightPal, 'dark')
check('paleta clara -> oscura cambia fondo y texto', darkPal && darkPal.bg !== lightPal.bg && darkPal.text !== lightPal.text)
check('paleta oscura mantiene AA texto/superficie', darkPal && contrastRatio(darkPal.text, darkPal.surface) >= 4.5)
check('paleta oscura mantiene AA acento/superficie', darkPal && contrastRatio(darkPal.primary, darkPal.surface) >= 4.5)
check('paleta ya oscura no se reescribe', adaptPalette(darkPal, 'dark') === null)
const backLight = adaptPalette(darkPal, 'light')
check('paleta oscura -> clara recupera fondo claro', backLight && contrastRatio(backLight.text, backLight.surface) >= 4.5 && contrastRatio(backLight.primary, backLight.surface) >= 4.5)
check('paleta ya clara no se reescribe', adaptPalette(backLight, 'light') === null)

console.log('— elección de diseño / estilo / iconos —')
const pat = { slug: 'atelier', template: 'atelier', layout: { landing: { blocks: [{ id: 'hero' }] } }, tokens: { accent: '#2d4a3e', fonts: ['hanken-grotesk', 'bricolage-grotesque'] } }
const okPat = patternChoice(pat, { allowed: ['raiz', 'atelier'] })
check('diseño permitido aplica template y layout', okPat && !okPat.locked && okPat.template === 'atelier' && !!okPat.layout_config.landing)
check('diseño de otro nivel queda bloqueado', patternChoice(pat, { allowed: ['raiz'] }).locked === true)
check('con estilo aplicado el diseño no pisa la piel', patternChoice(pat, { allowed: ['atelier'], hasStyle: true }).site_theme === undefined)
const sty = { slug: 'papel-riso', template: 'raiz', page_theme: 'light', tokens: { palette: { accent: '#0f766e' } }, layout: { landing: { blocks: [{ id: 'x' }] } } }
const okSty = styleChoice(sty, { allowed: ['raiz'] })
check('estilo aplica tema sin layout ni template', okSty && !okSty.locked && !okSty.layout_config && !okSty.template && okSty.site_theme.style.id === 'papel-riso')
check('estilo fuera del plan queda bloqueado', styleChoice({ ...sty, template: 'boutique' }, { allowed: ['raiz'] }).locked === true)
eq('icono del catálogo se guarda', iconChoice('lineal', { options: ['lineal'] }), { icon_style: 'lineal' })
eq('icono retirado vuelve a heredar', iconChoice('viejo', { options: ['lineal'] }), { icon_style: '' })
const draftPlan = savePayloadPlan({ asDraft: true, formTemplate: 'atelier', savedTemplate: 'raiz', siteTheme: { palette: { accent: '#0f766e' } }, layoutConfig: { landing: { blocks: [{ id: 'hero' }] } } })
check('el borrador guarda en columnas *_draft', !!draftPlan.template_draft && !!draftPlan.site_theme_draft && !!draftPlan.layout_config_draft && draftPlan.template === undefined)
const pubPlan = savePayloadPlan({ asDraft: false, formTemplate: 'atelier', savedTemplate: 'raiz', siteTheme: { palette: { accent: '#0f766e' } }, layoutConfig: { landing: { blocks: [{ id: 'hero' }] } } })
check('publicar guarda en las columnas definitivas', pubPlan.template === 'atelier' && !!pubPlan.site_theme && !!pubPlan.layout_config && pubPlan.template_draft === undefined)
eq('borrador sin cambio de diseño no manda template_draft', savePayloadPlan({ asDraft: true, formTemplate: 'raiz', savedTemplate: 'raiz' }), {})

console.log('')
if (failures) { console.error(`${failures} chequeo(s) fallaron`); process.exit(1) }
console.log('Contrato del Studio verificado: todo en verde.')
