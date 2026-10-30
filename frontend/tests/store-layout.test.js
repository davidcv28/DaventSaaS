// Composición canónica por diseño: el render monta lo que declara la
// plantilla y `layout_config` ya no reordena ni apaga nada.
import { describe, expect, it } from 'vitest'
import { resolveLayout, templateBlock, templateBlocks, TEMPLATE_DEFS } from '../src/templates/index.js'

describe('composición de las superficies', () => {
  it('templateBlocks devuelve la lista canónica con order/enabled', () => {
    const blocks = templateBlocks('raiz', 'landing')
    expect(blocks.map((b) => b.id)).toEqual(TEMPLATE_DEFS.raiz.blocks.landing)
    expect(blocks.every((b, i) => b.order === i && b.enabled)).toBe(true)
  })

  it('layout_config no altera la composición', () => {
    const config = { landing: { blocks: [{ id: 'cta', enabled: false, order: 0 }] } }
    expect(resolveLayout('raiz', 'landing', config)).toEqual(templateBlocks('raiz', 'landing'))
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
