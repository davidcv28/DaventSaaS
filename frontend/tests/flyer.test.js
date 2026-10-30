import { describe, expect, it } from 'vitest'

import {
  FLYER_LAYOUTS,
  isDigitalSize,
  layoutById,
  layoutsForSize,
  layoutsOfKind,
  sizeById,
} from '../src/utils/flyer.js'

describe('flyer catalog', () => {
  it('layoutById falls back to the first layout', () => {
    expect(layoutById('no-existe')).toBe(FLYER_LAYOUTS[0])
  })

  it('layoutsOfKind filters by kind', () => {
    const kind = FLYER_LAYOUTS[0].kind
    expect(layoutsOfKind(kind).every((layout) => layout.kind === kind)).toBe(true)
  })

  it('layoutsForSize respects the sizes whitelist', () => {
    const size = sizeById('a5')
    expect(layoutsForSize(size.id).every((layout) => !layout.sizes || layout.sizes.includes(size.id))).toBe(true)
  })

  it('sizeById defaults to a5 and knows digital sizes', () => {
    expect(sizeById('no-existe').id).toBe('a5')
    expect(typeof isDigitalSize('a5')).toBe('boolean')
  })
})
