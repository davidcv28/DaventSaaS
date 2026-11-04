import { describe, expect, it } from 'vitest'

import {
  FLYER_LAYOUTS,
  FLYER_SHEETS,
  imposition,
  isDigitalSize,
  layoutById,
  layoutsForSize,
  layoutsOfKind,
  sheetById,
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

const fitsPage = (imp) => (
  imp.cols * imp.fw + (imp.cols - 1) * imp.gap <= imp.pageW + 0.2 &&
  imp.rows * imp.fh + (imp.rows - 1) * imp.gap <= imp.pageH + 0.2
)

describe('imposition', () => {
  it('llena la A4 con copias A6 y no se sale de la hoja', () => {
    const imp = imposition('a6', 'a4')
    expect(imp.count).toBe(4)
    expect(imp.cols).toBe(2)
    expect(imp.rows).toBe(2)
    expect(imp.landscape).toBe(false)
    expect(fitsPage(imp)).toBe(true)
  })

  it('aprovecha el formato apaisado cuando entran más copias (A5)', () => {
    const imp = imposition('a5', 'a4')
    expect(imp.count).toBe(2)
    expect(imp.landscape).toBe(true)
    expect(fitsPage(imp)).toBe(true)
  })

  it('escala las copias para llenar la hoja sin recortarlas (A7)', () => {
    const imp = imposition('a7', 'a4')
    expect(imp.count).toBe(8)
    expect(fitsPage(imp)).toBe(true)
    expect(imp.scale).toBeGreaterThan(0)
  })

  it('respeta el tamaño real cuando se pide', () => {
    const imp = imposition('a6', 'a4', { fill: false })
    expect(imp.fw).toBe(105)
    expect(imp.fh).toBe(148)
    expect(fitsPage(imp)).toBe(true)
  })

  it('fuerza la orientación vertical', () => {
    const imp = imposition('a5', 'a4', { orientation: 'portrait' })
    expect(imp.count).toBe(1)
    expect(imp.landscape).toBe(false)
    expect(imp.fw).toBeGreaterThan(148)
    expect(fitsPage(imp)).toBe(true)
  })

  it('la separación entra en la cuenta y no desborda', () => {
    const imp = imposition('a6', 'a4', { gap: 10 })
    expect(imp.gap).toBeGreaterThan(0)
    expect(fitsPage(imp)).toBe(true)
  })

  it('una copia del tamaño del folleto va en su propia hoja', () => {
    const imp = imposition('a5', 'own')
    expect(imp.own).toBe(true)
    expect(imp.count).toBe(1)
    expect(imp.pageW).toBe(148)
    expect(imp.pageH).toBe(210)
    expect(imp.fw).toBe(148)
    expect(imp.fh).toBe(210)
  })

  it('achica una pieza más grande que la hoja en lugar de recortarla', () => {
    const imp = imposition('a4', 'a5')
    expect(imp.count).toBe(1)
    expect(imp.fw).toBeLessThan(210)
    expect(fitsPage(imp)).toBe(true)
  })

  it('admite otras hojas y piezas digitales', () => {
    expect(FLYER_SHEETS.map((s) => s.id)).toContain('oficio')
    expect(sheetById('oficio').h).toBe(356)
    const oficio = imposition('a6', 'oficio')
    expect(fitsPage(oficio)).toBe(true)
    const story = imposition('story', 'a4')
    expect(story.digital).toBe(true)
    expect(story.count).toBe(1)
    expect(fitsPage(story)).toBe(true)
  })

  it('una hoja desconocida cae en A4', () => {
    expect(imposition('a6', 'no-existe').sheetId).toBe('a4')
  })
})
