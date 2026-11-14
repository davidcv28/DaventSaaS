// Espejo JS de studio_theme_css (pattern_render.py): el site_theme del
// Studio se traduce a reglas sobre los hooks compartidos de los
// documentos de diseño (.btn/.ds-product*/section.hero/...). La web
// publicada la hornea el backend; la vista previa la inyecta por
// postMessage — este test fija el contrato de ambas salidas.
import { describe, expect, it } from 'vitest'
import { patternStudioCss, patternStudioFontQueries } from '../src/studio/patternStudio.js'

const theme = {
  surfaces: { card: '#F4F2EC', nav: '#111111', footer: '#1C1A17', hero: '#FF4B1F' },
  images: { ratio: 'wide', fit: 'contain', bg: '#EEEEEE', radius: 'md', border: 'bold' },
  background: { type: 'gradient', value: 'linear-gradient(120deg,#111,#333)', overlay: 'soft' },
  buttons: { style: 'outline', shape: 'pill', size: 'lg', borderStyle: 'dotted' },
  typography: { roles: {
    h2: { font: 'oswald', size: '2xl', weight: 700, tracking: 'tight' },
    price: { font: 'archivo-black', size: 'lg' },
    eyebrow: { case: 'upper', tracking: 'wider' }
  } }
}

describe('patternStudioCss (documentos de diseño)', () => {
  const css = patternStudioCss(theme)

  it('devuelve vacío sin tema ni acento', () => {
    expect(patternStudioCss({})).toBe('')
    expect(patternStudioCss(null)).toBe('')
    expect(patternStudioCss({ surfaces: {} })).toBe('')
  })

  it('paleta -> vars --ds-* en vivo (espejo de theme_css)', () => {
    const out = patternStudioCss({
      palette: {
        accent: '#f5d90a', primary: '#f5d90a', secondary: '#847505',
        bg: '#ffffff', surface: '#ffffff', text: '#111111'
      }
    })
    expect(out).toContain('--ds-accent:#f5d90a')
    expect(out).toContain('--ds-accent-ink:')
    expect(out).toContain('--ds-primary:#f5d90a')
    expect(out).toContain('--ds-secondary:#847505')
    expect(out).toContain('--ds-bg:#ffffff')
    expect(out).toContain('--ds-surface:#ffffff')
    expect(out).toContain('--ds-text:#111111')
    expect(out).toContain('--ds-primary-ink:')
    expect(out).toContain('--ds-secondary-ink:')
  })

  it('accent_custom tiene prioridad sobre palette.accent (como theme_css)', () => {
    const out = patternStudioCss(
      { palette: { accent: '#123456', surface: '#ffffff' } },
      '',
      '#ff0000'
    )
    expect(out).toContain('--ds-accent:#ff0000')
    expect(out).not.toContain('--ds-accent:#123456')
  })

  it('accent_custom solo (sin site_theme) igual emite --ds-accent', () => {
    const out = patternStudioCss(null, '', '#0f766e')
    expect(out).toContain(':root{--ds-accent:#0f766e')
    expect(out).toContain('--ds-accent-ink:')
  })

  it('superficies: fondo + tinta derivada sobre los hooks del diseño', () => {
    expect(css).toContain('.ds-product, .ds-cat')
    expect(css).toContain('background:#F4F2EC!important')
    expect(css).toContain('[data-ds-pin="top"], header.top, header.head{background:#111111!important')
    expect(css).toContain('footer, .foot{background:#1C1A17!important')
    expect(css).toContain('section.hero, .hero{background:#FF4B1F!important')
  })

  it('fotos de producto: aspecto, encaje, fondo, radio y borde', () => {
    expect(css).toContain('.ds-product-img{aspect-ratio:16 / 10!important')
    expect(css).toContain('object-fit:contain!important')
    expect(css).toContain('background:#EEEEEE!important')
    expect(css).toContain('border-radius:14px!important')
    expect(css).toContain('border:2px solid var(--ds-border, currentColor)!important')
  })

  it('fondo: la declaración del tipo elegido + overlay', () => {
    expect(css).toContain('body, main{background:linear-gradient(120deg,#111,#333)!important}')
    expect(css).toContain('body::after{content:"";position:fixed;inset:0;background:rgba(9, 12, 24, .32)')
  })

  it('fondo imagen: url propia con comillas escapadas', () => {
    const out = patternStudioCss({ background: { type: 'image', value: 'https://x.test/a"b.webp' } })
    expect(out).toContain('background:url("https://x.test/a%22b.webp") center / cover no-repeat!important')
  })

  it('botones: estilo, borde, forma y tamaño sobre .btn y CTAs', () => {
    expect(css).toContain('.btn:not(.pdp-buy *), .svc-cta, .pdp-buy:is(a, button)')
    expect(css).toContain('background:transparent!important')
    expect(css).toContain('border-style:dotted!important')
    expect(css).toContain('border-width:2px!important')
    expect(css).toContain('border-radius:999px!important')
    expect(css).toContain('min-height:54px!important')
    expect(css).toContain('font-size:16px!important')
  })

  it('roles tipográficos: familia del catálogo + specs', () => {
    expect(css).toContain("font-family:'Oswald', sans-serif")
    expect(css).toContain('font-size:2rem!important')
    expect(css).toContain('font-weight:700!important')
    expect(css).toContain('letter-spacing:-0.015em!important')
    expect(css).toContain('text-transform:uppercase!important')
    expect(css).toContain("font-family:'Archivo Black', sans-serif")
  })

  it('los roles van antes que las reglas de botones (buttons.size gana font-size)', () => {
    const roleAt = css.indexOf('h2{')
    const btnAt = css.indexOf('.btn:not(.pdp-buy *)')
    expect(roleAt).toBeGreaterThan(-1)
    expect(btnAt).toBeGreaterThan(roleAt)
  })

  it('fonts de roles -> queries css2 para las @font-face', () => {
    const queries = patternStudioFontQueries(theme)
    expect(queries).toContain('Oswald:wght@400..700')
    expect(queries).toContain('Archivo+Black')
    expect(patternStudioFontQueries({})).toEqual([])
  })

  it('acento como texto: --ds-accent-text se ajusta a AA contra la superficie', () => {
    // Amarillo claro sobre superficie blanca: el texto NO puede quedar
    // amarillo — se oscurece hasta cumplir contraste.
    const out = patternStudioCss({
      palette: { accent: '#f5d90a', surface: '#ffffff' },
      buttons: { style: 'outline' }
    })
    const m = out.match(/--ds-accent-text:(#[0-9a-f]{6})/)
    expect(m).toBeTruthy()
    expect(m[1]).not.toBe('#f5d90a')
    expect(out).toContain('color:var(--ds-accent-text, var(--ds-accent, currentColor))!important')
  })

  it('acento ya legible sobre la superficie se conserva', () => {
    const out = patternStudioCss({
      palette: { accent: '#1d4ed8', surface: '#ffffff' },
      buttons: { style: 'ghost' }
    })
    expect(out).toContain('--ds-accent-text:#1d4ed8')
    expect(out).toContain('color:var(--ds-accent-text, var(--ds-accent, currentColor))!important')
  })

  it('sin superficie conocida no se emite --ds-accent-text', () => {
    const out = patternStudioCss({ palette: { accent: '#f5d90a' }, buttons: { style: 'outline' } })
    expect(out).not.toContain('--ds-accent-text:')
    expect(out).toContain('color:var(--ds-accent-text, var(--ds-accent, currentColor))!important')
  })
})
