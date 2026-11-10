// QA de diseños de tienda: overflow horizontal, contraste AA de texto,
// errores de consola y capturas por viewport. Corre con:
//   node <skill>/browser.mjs http://localhost:5173/tienda/<slug>/ --script .tmpqa/qa-designs.mjs
const DESIGNS = [
  ['portico', 'vertice'], ['esencial', 'vivero-esencia'], ['mercado', 'bazar-artemisa'],
  ['autoservicio', 'el-trebol'], ['gimnasio', 'forja'], ['ruta', 'ruta-sur'],
  ['moderntec', 'nodo'], ['movimiento', 'demo'], ['aurum', 'casa-aurea'],
  ['brigada', 'vigia'], ['calzado', 'zancada'], ['indumentaria', 'atelier-luma'],
  ['impacto', 'mi-qa'], ['moda', 'maison-vela'], ['modista', 'atelier-serena'],
  ['topmodern', 'voga'], ['viajero', 'viajero-andino'], ['olivium', 'olivium-qa'],
  ['atelier-noir', 'atelier-bruma'], ['guardia', 'centinela'], ['expediente', 'bufete-vega'],
  ['silicio', 'nucleo'], ['neon', 'nocturna'], ['showroom', 'nomada'],
  ['sastreria', 'telar'], ['umbral', 'limen']
]
const ALL_PAGES = [['home', ''], ['auth', '/ingresar'], ['cuenta', '/cuenta'], ['catalogo', '/catalogo']]
const ALL_VIEWPORTS = [[390, 844], [768, 1024], [1280, 900]]
const PAGES = (process.env.QA_PAGES || 'home,auth,cuenta,catalogo').split(',').map((k) => ALL_PAGES.find(([n]) => n === k)).filter(Boolean)
const VIEWPORTS = (process.env.QA_WIDTHS || '390,768,1280').split(',').map((w) => [Number(w), w === '390' ? 844 : w === '768' ? 1024 : 900])
const BASE = 'http://localhost:5173/tienda'
const OUT = 'frontend/visual-qa/orch'

function ratio(c1, c2) {
  const lum = (c) => {
    const [r, g, b] = c.map((v) => {
      const s = v / 255
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
    })
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }
  const a = lum(c1), b = lum(c2)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

const AUDIT = `(() => {
  const parse = (s) => {
    let m = s.match(/rgba?\\(([^)]+)\\)/)
    if (m) {
      const p = m[1].split(',').map(Number)
      return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 }
    }
    m = s.match(/color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?\\s*\\)/)
    if (m) return { rgb: [m[1], m[2], m[3]].map((v) => Math.round(Number(v) * 255)), a: m[4] === undefined ? 1 : Number(m[4]) }
    return null
  }
  const bgOf = (el) => {
    let n = el
    while (n && n.nodeType === 1) {
      const cs2 = getComputedStyle(n)
      if (cs2.backgroundImage && cs2.backgroundImage !== 'none') return null
      const c = parse(cs2.backgroundColor)
      if (c && c.a > 0.6) return c.rgb
      n = n.parentElement
    }
    return [255, 255, 255]
  }
  const out = []
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  let n
  while ((n = walker.nextNode())) {
    const t = n.textContent.trim()
    if (t.length < 2) continue
    const el = n.parentElement
    if (!el) continue
    const cs = getComputedStyle(el)
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) < 0.15) continue
    const r = el.getBoundingClientRect()
    if (r.width < 2 || r.height < 2) continue
    if (el.closest('svg, script, style')) continue
    const fg = parse(cs.color)
    if (!fg || fg.a < 0.2) continue
    const bg = bgOf(el)
    if (!bg) continue
    const size = parseFloat(cs.fontSize)
    const bold = Number(cs.fontWeight) >= 700
    const large = size >= 24 || (size >= 18.66 && bold)
    const cr = (() => {
      const lum = (c) => { const [r2,g2,b2] = c.map((v)=>{const s=v/255;return s<=0.03928?s/12.92:Math.pow((s+0.055)/1.055,2.4)}); return 0.2126*r2+0.7152*g2+0.0722*b2 }
      const a=lum(fg.rgb), b=lum(bg); return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05)
    })()
    const min = large ? 3 : 4.5
    if (cr < min) out.push({ text: t.slice(0, 40), cls: (el.className || el.tagName).toString().slice(0, 60), fg: cs.color, bg: 'rgb(' + bg.join(',') + ')', cr: Math.round(cr * 100) / 100, need: min })
    if (out.length > 40) break
  }
  return {
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    contrast: out
  }
})()`

export default async function run(page, ui) {
  const report = []
  const filter = process.env.QA_DESIGNS ? process.env.QA_DESIGNS.split(',') : null
  const list = filter ? DESIGNS.filter(([d]) => filter.includes(d)) : DESIGNS
  for (const [design, slug] of list) {
    for (const [pageName, path] of PAGES) {
      for (const [w, h] of VIEWPORTS) {
        await page.setViewportSize({ width: w, height: h })
        try {
          await page.goto(`${BASE}/${slug}${path}`, { waitUntil: 'domcontentloaded', timeout: 45000 })
          await page.waitForFunction(() => !document.querySelector('.sp-boot'), null, { timeout: 20000 }).catch(() => {})
          await page.waitForTimeout(700)
          // recorre para disparar reveals antes de la captura
          await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
          await page.waitForTimeout(500)
          await page.evaluate(() => window.scrollTo(0, 0))
          await page.waitForTimeout(300)
          const res = await page.evaluate(AUDIT)
          const name = `${OUT}/${design}-${pageName}-${w}.png`
          await page.screenshot({ path: name, fullPage: pageName !== 'home' })
          report.push({ design, page: pageName, w, overflow: res.overflow, contrast: res.contrast.slice(0, 8), shot: name })
        } catch (e) {
          report.push({ design, page: pageName, w, error: String(e).slice(0, 160) })
        }
      }
    }
  }
  return report
}
