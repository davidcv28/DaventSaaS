// Paridad Studio ↔ web publicada: el mismo site_theme parcial tiene que
// producir las mismas variables y atributos en el lienzo y en la página real.
// Lo que se controla acá es el contrato (no el CSS): cada control del panel
// escribe una clave y esa clave tiene que salir como token/atributo.
import { describe, expect, it } from 'vitest'
import { themeExplicitKeys, studioUpdate } from '../src/studio/contract.js'
import {
  studioPreviewVars, studioPreviewAttrs, storeSiteThemeVars, storeSiteThemeAttrs
} from '../src/components/studio/previewBridge.js'

const theme = {
  palette: { accent: '#0f766e', text: '#0b1220' },
  typography: { heading: 'inter', body: 'inter', weightHeading: 800, letterSpacing: '-0.02em' },
  containers: { radius: 'lg', shadow: 'deep', border: 'bold', density: 'spacious', surface: 'glass' },
  buttons: { shape: 'pill', style: 'outline', size: 'lg' },
  background: { type: 'gradient', value: 'linear-gradient(120deg, #0f766e, #042f2e)', overlay: 'rgba(0,0,0,.2)' },
  motion: { reveal: 'fade', hover: 'glow', intensity: 'subtle' },
  mobile: { nav: 'bottom', gridCols: 2, cardStyle: 'compact', heroHeight: 'tall', stickyCta: true }
}

describe('paridad tema Studio / web publicada', () => {
  it('emite los mismos tokens en el lienzo y en lo publicado', () => {
    const keys = themeExplicitKeys(theme)
    const canvas = studioPreviewVars(theme, 'light', keys)
    const published = storeSiteThemeVars({ site_theme: theme, accent: 'teal', name_font: 'inter' }, 'light')
    for (const [key, value] of Object.entries(canvas)) {
      if (key === '--sp-accent-text') continue
      expect(published[key], `token ${key}`).toBe(value)
    }
  })

  it('los controles de móvil llegan como atributos a la página', () => {
    const attrs = studioPreviewAttrs(theme, themeExplicitKeys(theme), 'light')
    expect(attrs['data-st-nav']).toBe('bottom')
    expect(attrs['data-st-card']).toBe('compact')
    expect(attrs['data-st-hero']).toBe('tall')
    expect(attrs['data-st-grid']).toBe('2')
    expect(attrs['data-st-sticky-cta']).toBe('true')
  })

  it('lo publicado aplica el tema de los diseños del catálogo (sin gate)', () => {
    const attrs = storeSiteThemeAttrs({ site_theme: theme, template: 'raiz' }, 'light')
    expect(attrs['data-st-themed']).toBe('')
    expect(attrs['data-st-nav']).toBe('bottom')
    expect(attrs['data-st-skin']).toBeUndefined()
  })

  it('studioUpdate resuelve el tema completo y mantiene el device', () => {
    const msg = studioUpdate({ theme, layout: { landing: { blocks: [] } }, template: 'raiz', device: 'mobile' })
    expect(msg.theme.mobile.nav).toBe('bottom')
    expect(msg.device).toBe('mobile')
    expect(msg.layout.landing.blocks).toEqual([])
  })
})
