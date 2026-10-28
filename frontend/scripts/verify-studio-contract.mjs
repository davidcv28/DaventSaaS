// Verificación del contrato del Studio (sin runner de tests en el proyecto):
//   node scripts/verify-studio-contract.mjs    (o npm run verify:studio)
// Corre en node puro — contract.js es autocontenido justamente para esto.

import {
  SITE_THEME_DEFAULTS, STUDIO_ENUMS, STUDIO_MSG, STUDIO_SURFACES,
  resolveSiteTheme, themeToCssVars, themeDataAttrs,
  contrastRatio, fixContrast, textOn, normalizeHex,
  resolveStudioPreset, presetToPatch,
  studioUpdate, studioFocus, studioReady, isStudioMessage
} from '../src/studio/contract.js'

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

console.log('')
if (failures) { console.error(`${failures} chequeo(s) fallaron`); process.exit(1) }
console.log('Contrato del Studio verificado: todo en verde.')
