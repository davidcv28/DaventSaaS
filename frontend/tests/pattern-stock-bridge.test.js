import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

import { describe, expect, it } from 'vitest'
import { JSDOM } from 'jsdom'

// Regresión del puente de documentos patrón: el host empuja el mapa
// {producto: unidades|null} del catálogo público por `davent:ds-stock` y el
// puente repinta .ds-stock de las tarjetas, inyecta la línea .dsx-stock en
// la ficha y apaga el CTA de la ficha de lo agotado. Las tarjetas son un
// solo link (contrato tarjeta=link, ola6 §1): ya no llevan [data-ds-buy] —
// el CTA de compra vive solo en la ficha. jsdom no aplica CSS: se
// verifican textos, clases y estados disabled/aria.
const here = dirname(fileURLToPath(import.meta.url))
const bridge = readFileSync(
  join(here, '../../StoreApp/domains/design/services/pattern_bridge.js'),
  'utf-8'
)

const CARD = (pid, name) => `
  <article class="ds-product" data-ds-product="${pid}">
    <a class="ds-product-link" href="#catalogo" data-ds-product="${pid}" aria-label="${name}">
      <img class="ds-product-img" alt="">
      <span class="ds-product-copy"><h3 class="ds-product-name">${name}</h3></span>
      <span class="ds-stock"><i></i>En stock</span>
      <span class="ds-product-price"><span class="ds-product-amount">$10</span></span>
    </a>
  </article>`

const HTML = `<!doctype html><html lang="es" data-ds-theme="light" data-ds-surface="catalog" data-ds-commerce="1"><head><meta charset="utf-8"></head><body>
<section data-surface="catalog"><div data-ds-products>${CARD(272, 'Aceituna')}${CARD(273, 'Oliva')}</div></section>
<section class="pdp-surface" data-surface="product">
  <div class="pdp-info">
    <h1>Ficha</h1>
    <div class="pdp-price"><b>$25.000</b></div>
    <a class="btn" href="https://wa.me/1" data-ds-buy="272" data-ds-buy-slot="pdp">Reservar</a>
    <div data-ds-products>${CARD(274, 'Relacionada')}</div>
  </div>
</section>
</body></html>`

const dom = new JSDOM(HTML, {
  url: 'http://localhost/doc/?surface=product&product=272&theme=light',
  runScripts: 'outside-only',
  pretendToBeVisual: true,
})
const { window } = dom
// Callouts que jsdom no implementa y el puente usa en init.
window.scrollTo = () => {}
window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
window.eval(bridge)

const post = (data) => window.dispatchEvent(new window.MessageEvent('message', { data, source: window }))
const $$ = (s) => [...window.document.querySelectorAll(s)]
const stockTexts = () => $$('.ds-stock').map((e) => e.textContent.trim())
const cardState = (pid) => {
  const link = window.document.querySelector(`[data-ds-product="${pid}"]`)
  const card = link?.closest('.ds-product')
  if (!card) return null
  const tag = card.querySelector('.ds-stock')
  const buy = card.querySelector('[data-ds-buy]')
  return {
    tag: tag?.textContent.trim(),
    tagOut: tag?.classList.contains('is-out'),
    buyDisabled: buy ? !!buy.disabled : null,
    buyAria: buy?.getAttribute('aria-disabled'),
  }
}

describe('pattern bridge — disponibilidad de stock', () => {
  it('sinchesis: el fallback "En stock" queda hasta recibir el mapa', () => {
    expect(stockTexts()).toEqual(['En stock', 'En stock', 'En stock'])
    expect(window.document.querySelector('.dsx-stock')).toBeNull()
  })

  it('pinta la cifra real en tarjetas y la línea de la ficha', () => {
    post({ type: 'davent:ds-stock', stock: { 272: 98, 273: 1, 274: null } })
    expect(cardState(272)?.tag).toContain('98 disponibles')
    expect(cardState(273)?.tag).toContain('1 disponible')
    expect(cardState(274)?.tag).toContain('Stock ilimitado')
    // Contrato tarjeta=link: ningún CTA dentro de .ds-product.
    expect(cardState(272)?.buyDisabled).toBeNull()
    expect($$('.ds-product [data-ds-buy]')).toHaveLength(0)
    const line = window.document.querySelector('.dsx-stock')
    expect(line?.textContent).toContain('98 unidades disponibles')
    expect(line?.classList.contains('is-out')).toBe(false)
  })

  it('agotado marca el tag y apaga el CTA de ficha sin tocar relacionados', () => {
    post({ type: 'davent:ds-stock', stock: { 272: 0, 273: 96, 274: null } })
    const z = cardState(272)
    expect(z?.tag).toContain('Agotado')
    expect(z?.tagOut).toBe(true)
    // La tarjeta no tiene CTA propio (es un solo link): no hay nada que apagar.
    expect(z?.buyDisabled).toBeNull()
    expect(z?.buyAria).toBeUndefined()
    const line = window.document.querySelector('.dsx-stock')
    expect(line?.textContent).toContain('Agotado')
    expect(line?.classList.contains('is-out')).toBe(true)
    // CTA de ficha <a>: sin .disabled — el contrato es aria-disabled + .is-out
    const pdpBuy = window.document.querySelector('[data-ds-buy-slot="pdp"]')
    expect(pdpBuy?.getAttribute('aria-disabled')).toBe('true')
    expect(pdpBuy?.classList.contains('is-out')).toBe(true)
    // La relacionada (274) conserva su propio stock
    const r = cardState(274)
    expect(r?.tag).toContain('ilimitado')
    expect(r?.buyDisabled).toBeNull()
  })

  it('el click en un CTA agotado no postea davent:ds-buy', () => {
    const posted = []
    window.addEventListener('message', (e) => { if (e.data?.type === 'davent:ds-buy') posted.push(e.data.id) })
    window.document.querySelector('[data-ds-buy-slot="pdp"]')
      .dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }))
    expect(posted).toHaveLength(0)
  })

  it('un mapa nulo no rompe el documento', () => {
    expect(() => post({ type: 'davent:ds-stock', stock: null })).not.toThrow()
    expect(stockTexts().some((t) => t.includes('Agotado'))).toBe(true)
  })
})
