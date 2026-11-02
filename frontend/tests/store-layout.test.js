// Composición por diseño: el render monta lo que declara la plantilla y
// `layout_config` pisa enabled/variant/props de los bloques declarados
// (un id que el diseño no trae no se agrega; el orden lo fija el diseño).
import { describe, expect, it } from 'vitest'
import { resolveLayout, templateBlock, templateBlocks, TEMPLATE_DEFS } from '../src/templates/index.js'

describe('composición de las superficies', () => {
  it('templateBlocks devuelve la lista canónica con order/enabled', () => {
    const blocks = templateBlocks('raiz', 'landing')
    expect(blocks.map((b) => b.id)).toEqual(TEMPLATE_DEFS.raiz.blocks.landing)
    expect(blocks.every((b, i) => b.order === i && b.enabled)).toBe(true)
  })

  it('layout_config apaga y reconfigura bloques declarados', () => {
    const config = { landing: { blocks: [{ id: 'cta', enabled: false, variant: 'band' }] } }
    const effective = resolveLayout('raiz', 'landing', config)
    expect(effective.find((b) => b.id === 'cta')).toMatchObject({ enabled: false, variant: 'band' })
    // El resto conserva la composición canónica, en el orden del diseño.
    expect(effective.map((b) => b.id)).toEqual(TEMPLATE_DEFS.raiz.blocks.landing)
    expect(effective.find((b) => b.id === 'hero').enabled).toBe(true)
  })

  it('layout_config no agrega ids que el diseño no declara', () => {
    const config = { landing: { blocks: [{ id: 'inexistente', enabled: true }] } }
    expect(resolveLayout('raiz', 'landing', config).some((b) => b.id === 'inexistente')).toBe(false)
  })

  it('un diseño desconocido cae en la composición de raíz', () => {
    expect(templateBlocks('no-existe', 'landing')).toEqual(templateBlocks('raiz', 'landing'))
  })

  it('templateBlock resuelve un id puntual y tolera ids ausentes', () => {
    const hero = templateBlock('raiz', 'services', 'hero')
    expect(hero.id).toBe('hero')
    expect(hero.order).toBe(0)
    expect(templateBlock('raiz', 'services', 'inexistente')).toEqual({ id: 'inexistente', enabled: true })
  })
})
