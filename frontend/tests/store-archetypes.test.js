import { describe, expect, it } from 'vitest'
import {
  NAV_ARCHETYPES,
  ACCOUNT_ARCHETYPES,
  TRACKING_ARCHETYPES,
  DESIGN_ARCHETYPES,
  DEFAULT_ARCHETYPES,
  archetypeForDesign
} from '../src/composables/storeArchetypes.js'

const MATRIX_SLUGS = [
  'portico', 'esencial', 'mercado', 'autoservicio', 'gimnasio', 'movimiento',
  'sastreria', 'moderntec', 'indumentaria', 'impacto', 'showroom', 'ruta',
  'aurum', 'brigada', 'neon', 'calzado', 'moda', 'modista', 'topmodern',
  'viajero', 'olivium', 'atelier-noir', 'guardia', 'expediente', 'silicio',
  'umbral'
]

const NAV_SET = new Set(NAV_ARCHETYPES)
const ACCOUNT_SET = new Set(ACCOUNT_ARCHETYPES)
const TRACKING_SET = new Set(TRACKING_ARCHETYPES)

describe('matriz diseño → arquetipos', () => {
  it('cubre los 26 diseños del catálogo', () => {
    expect(Object.keys(DESIGN_ARCHETYPES).sort()).toEqual([...MATRIX_SLUGS].sort())
  })

  it('todos los valores existen en sus catálogos', () => {
    for (const [design, arch] of Object.entries(DESIGN_ARCHETYPES)) {
      expect(NAV_SET.has(arch.nav), `${design}.nav`).toBe(true)
      expect(ACCOUNT_SET.has(arch.account), `${design}.account`).toBe(true)
      expect(TRACKING_SET.has(arch.tracking), `${design}.tracking`).toBe(true)
    }
  })

  it('los 26 nav son todos distintos y están en el catálogo', () => {
    const navs = Object.values(DESIGN_ARCHETYPES).map((a) => a.nav)
    expect(new Set(navs).size).toBe(26)
    for (const nav of navs) expect(NAV_SET.has(nav)).toBe(true)
  })

  it('los pares cuenta+seguimiento: 24 únicos (colisiones documentadas)', () => {
    // La matriz del catálogo produce 24 pares distintos sobre 26 diseños:
    // sastreria/expediente comparten account-card|tracking-stepcard y
    // brigada/olivium comparten account-bento|tracking-minimal (el doc lo
    // verifica: "24 pares distintos"). La unicidad estructural la completa
    // el CSS propio de cada diseño.
    const pairs = Object.values(DESIGN_ARCHETYPES).map((a) => `${a.account}|${a.tracking}`)
    expect(new Set(pairs).size).toBe(24)
  })
})

describe('archetypeForDesign', () => {
  it('devuelve los arquetipos de la matriz', () => {
    expect(archetypeForDesign('calzado')).toMatchObject({
      nav: 'hide-on-scroll', account: 'account-split', tracking: 'tracking-bento', design: 'calzado'
    })
    expect(archetypeForDesign('portico').nav).toBe('editorial-index')
  })

  it('normaliza mayúsculas y espacios', () => {
    expect(archetypeForDesign('  Calzado ').nav).toBe('hide-on-scroll')
  })

  it('cae en defaults para diseño desconocido o vacío', () => {
    for (const id of ['', null, undefined, 'no-existe']) {
      expect(archetypeForDesign(id)).toEqual({
        ...DEFAULT_ARCHETYPES,
        design: id ? String(id).trim().toLowerCase() : 'esencial'
      })
    }
  })
})
