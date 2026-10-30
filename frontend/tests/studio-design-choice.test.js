// Elección de diseño/estilo/iconos y payload del guardado del Studio.
// Cubre el gating por plan (un diseño de otro nivel no se aplica) y que el
// borrador y la publicación usen cada uno sus columnas.
import { describe, expect, it } from 'vitest'
import {
  iconChoice, isTemplateAllowed, patternChoice, savePayloadPlan, styleChoice
} from '../src/studio/designChoice.js'

const pattern = {
  slug: 'atelier',
  template: 'atelier',
  layout: { landing: { blocks: [{ id: 'hero' }] } },
  tokens: { accent: '#2d4a3e', fonts: ['hanken-grotesk', 'bricolage-grotesque'] }
}
const style = {
  slug: 'papel-riso',
  template: 'raiz',
  page_theme: 'light',
  tokens: { palette: { accent: '#0f766e' }, containers: { radius: 'sm' } },
  layout: { landing: { blocks: [{ id: 'otra' }] } }
}

describe('elección de diseño', () => {
  it('aplica template + layout cuando el plan lo permite', () => {
    const choice = patternChoice(pattern, { allowed: ['raiz', 'atelier'] })
    expect(choice.locked).toBe(false)
    expect(choice.template).toBe('atelier')
    expect(choice.layout_config).toEqual(pattern.layout)
  })

  it('bloquea un diseño de otro nivel sin tocar el borrador', () => {
    const choice = patternChoice(pattern, { allowed: ['raiz'] })
    expect(choice).toEqual({ locked: true, template: 'atelier' })
  })

  it('sin estilo aplicado trae la piel del diseño (fuentes y acento)', () => {
    const choice = patternChoice(pattern, { allowed: ['atelier'] })
    expect(choice.site_theme.typography).toEqual({ body: 'hanken-grotesk', heading: 'bricolage-grotesque' })
    expect(choice.site_theme.palette.accent).toBe('#2d4a3e')
  })

  it('con estilo aplicado el diseño solo cambia la estructura', () => {
    const choice = patternChoice(pattern, { allowed: ['atelier'], hasStyle: true })
    expect(choice.site_theme).toBeUndefined()
    expect(choice.layout_config).toEqual(pattern.layout)
  })

  it('sin plantilla no hay elección', () => {
    expect(patternChoice({}, { allowed: ['raiz'] })).toBeNull()
    expect(isTemplateAllowed('', ['raiz'])).toBe(false)
  })
})

describe('elección de estilo', () => {
  it('aplica el tema del estilo y nunca su layout', () => {
    const choice = styleChoice(style, { allowed: ['raiz'] })
    expect(choice.locked).toBe(false)
    expect(choice.site_theme.style).toEqual({ id: 'papel-riso' })
    expect(choice.site_theme.containers).toEqual({ radius: 'sm' })
    expect(choice.layout_config).toBeUndefined()
    expect(choice.template).toBeUndefined()
    expect(choice.page_theme).toBe('light')
  })

  it('bloquea estilos fuera del plan', () => {
    const premium = { ...style, slug: 'lujo-serif', template: 'boutique' }
    expect(styleChoice(premium, { allowed: ['raiz'] })).toEqual({ locked: true, template: 'boutique' })
  })
})

describe('set de iconos', () => {
  it('vacío hereda el del diseño', () => {
    expect(iconChoice('', { options: ['lineal'] })).toEqual({ icon_style: '' })
  })

  it('un slug del catálogo se guarda y uno retirado vuelve a heredar', () => {
    expect(iconChoice('lineal', { options: ['lineal'] })).toEqual({ icon_style: 'lineal' })
    expect(iconChoice('viejo', { options: ['lineal'] })).toEqual({ icon_style: '' })
  })
})

describe('payload del guardado', () => {
  const theme = { palette: { accent: '#0f766e' } }
  const layout = { landing: { blocks: [{ id: 'hero' }] } }

  it('el borrador escribe columnas *_draft y no toca lo publicado', () => {
    const plan = savePayloadPlan({
      asDraft: true, formTemplate: 'atelier', savedTemplate: 'raiz',
      siteTheme: theme, layoutConfig: layout
    })
    expect(plan).toEqual({
      template_draft: 'atelier',
      site_theme_draft: theme,
      layout_config_draft: layout
    })
  })

  it('publicar escribe las columnas definitivas', () => {
    const plan = savePayloadPlan({
      asDraft: false, formTemplate: 'atelier', savedTemplate: 'raiz',
      siteTheme: theme, layoutConfig: layout
    })
    expect(plan).toEqual({ template: 'atelier', site_theme: theme, layout_config: layout })
  })

  it('un borrador sin cambio de diseño no manda template_draft', () => {
    const plan = savePayloadPlan({ asDraft: true, formTemplate: 'raiz', savedTemplate: 'raiz' })
    expect(plan.template_draft).toBeUndefined()
    expect(plan).toEqual({})
  })

  it('el ensayo de plantilla manda sobre el form', () => {
    const plan = savePayloadPlan({
      asDraft: true, formTemplate: 'raiz', savedTemplate: 'raiz', trialTemplate: 'atelier'
    })
    expect(plan.template_draft).toBe('atelier')
  })
})
