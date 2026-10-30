"""Contraste AA real (navegador) de las 32 pieles en modo noche sobre bench-store."""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

URL = 'http://localhost:5173/bench-store'
FAMILIES = ['glass', 'editorial', 'brutal', 'soft', 'tech', 'warm', 'luxury', 'kinetic',
            'paper', 'neon', 'minimal', 'organic', 'retro', 'corporate', 'playful',
            'mono', 'gradient', 'cinematic', 'swiss', 'magazine', 'pop', 'aurora',
            'craft', 'nostalgia', 'prestige', 'showcase', 'atelier', 'terminal',
            'riso', 'vitrina', 'cobre', 'lumen']
WIDTH = int(os.environ.get('QA_W', '1360'))
ONLY = sys.argv[1:] or FAMILIES

SETUP = """(family) => {
  const page = document.querySelector('.store-page')
  if (!page) return false
  page.setAttribute('data-store-theme', 'dark')
  page.setAttribute('data-theme', 'dark')
  page.setAttribute('data-st-skin', family)
  page.setAttribute('data-st-style', 'dark')
  page.setAttribute('data-st-themed', '')
  const id = 'qa-skin-' + family
  if (!document.getElementById(id)) {
    const l = document.createElement('link')
    l.id = id; l.rel = 'stylesheet'; l.href = '/src/assets/skin-' + family + '.css?direct'
    document.head.appendChild(l)
  }
  return getComputedStyle(page).getPropertyValue('--sp-radius')
}"""

SAMPLE = r"""() => {
  const lum = (c) => {
    if (!/^rgba?\(/.test(c)) return null
    const m = c.match(/[\d.]+/g); if (!m || m.length < 3) return null
    const [r, g, b] = m.slice(0, 3).map(v => +v / 255)
    const f = (x) => x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
  }
  const parse = (c) => {
    if (!c) return null
    const m = c.match(/[\d.]+/g)
    if (!m || m.length < 3) return null
    if (/^color\(srgb/.test(c)) {
      const a = m.length > 3 ? +m[3] : 1
      return { rgb: m.slice(0, 3).map(v => Math.round(+v * 255)), a }
    }
    return { rgb: m.slice(0, 3).map(Number), a: m.length > 3 ? +m[3] : 1 }
  }
  const blend = (top, base) => top.rgb.map((v, i) => v * top.a + base.rgb[i] * (1 - top.a))
  // Fondo efectivo: compone translúcidos y degradados (primer color del degradado).
  const bgOf = (el) => {
    const stack = []
    let p = el
    while (p) {
      const cs = getComputedStyle(p)
      if (cs.backgroundImage && cs.backgroundImage !== 'none') {
        const m = cs.backgroundImage.match(/rgba?\([^)]*\)/)
        if (m) { const c = parse(m[0]); if (c && c.a > 0) stack.push(c) }
        else stack.push({ rgb: [13, 18, 32], a: 1 })
      }
      const c = parse(cs.backgroundColor)
      if (c && c.a > 0) stack.push(c)
      if (stack.length && stack[stack.length - 1].a >= 0.99) break
      p = p.parentElement
    }
    let base = { rgb: [255, 255, 255], a: 1 }
    for (let i = stack.length - 1; i >= 0; i--) {
      base = { rgb: blend(stack[i], base), a: 1 }
    }
    return base
  }
  const inView = (el) => {
    const r = el.getBoundingClientRect()
    if (r.width < 1 || r.height < 1) return false
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) return false
    if (el.closest('[aria-hidden="true"], [inert]')) return false
    let p = el
    while (p) {
      const cs = getComputedStyle(p)
      if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return false
      p = p.parentElement
    }
    return true
  }
  const out = []
  const seen = new Set()
  for (const el of document.querySelectorAll('p, h1, h2, h3, h4, li, span, a, button, label, small, strong')) {
    if (!inView(el) || !el.innerText?.trim() || el.innerText.length > 200) continue
    const cs = getComputedStyle(el)
    // Texto pintado con degradado (background-clip:text): no hay color plano.
    if (cs.backgroundClip === 'text' || cs.webkitBackgroundClip === 'text') continue
    const fg = parse(cs.color)
    if (!fg || fg.a < 0.5) continue
    const bg = bgOf(el)
    const fgc = fg.a < 1 ? blend(fg, bg) : fg.rgb
    const lf = lum('rgb(' + fgc.map(Math.round).join(',') + ')')
    const lb = lum('rgb(' + bg.rgb.map(Math.round).join(',') + ')')
    if (lf == null || lb == null) continue
    const ratio = (Math.max(lf, lb) + 0.05) / (Math.min(lf, lb) + 0.05)
    const size = parseFloat(cs.fontSize)
    const weight = parseInt(cs.fontWeight) || 400
    const large = size >= 24 || (size >= 18.66 && weight >= 700)
    const need = large ? 3 : 4.5
    if (ratio < need) {
      const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 45)
      const key = el.tagName + '.' + cls + el.innerText.trim().slice(0, 12)
      if (seen.has(key)) continue
      seen.add(key)
      out.push({ ratio: +ratio.toFixed(2), need, sel: el.tagName.toLowerCase() + '.' + cls,
                 text: el.innerText.trim().slice(0, 30), color: cs.color,
                 bg: 'rgb(' + bg.rgb.map(Math.round).join(',') + ')' })
    }
  }
  return out
}"""

results = {}
PAYLOAD = json.load(open('.tmp/bench.json', encoding='utf-8'))
CATALOG = json.load(open('.tmp/bench_catalog.json', encoding='utf-8'))
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={'width': WIDTH, 'height': 900}, reduced_motion='reduce')
    # El endpoint público va throttleado (store_visit 120/h): se responde con
    # el payload serializado en vez de golpear la API en cada piel.
    def _fulfill(route):
        body = CATALOG if '/catalog/' in route.request.url else PAYLOAD
        route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
    ctx.route('**/api/stores/public/bench-store/**', _fulfill)
    page = ctx.new_page()
    page.goto(URL, wait_until='networkidle', timeout=40000)
    page.wait_for_timeout(1200)
    if not page.evaluate("document.querySelectorAll('.store-page').length"):
        raise SystemExit('sin .store-page')
    for fam in ONLY:
        page.evaluate("window.scrollTo(0,0)")
        page.evaluate(SETUP, fam)
        page.wait_for_timeout(700)
        found = []
        h = page.evaluate("document.body.scrollHeight")
        step = 700
        y = 0
        while y < h and len(found) < 12:
            page.evaluate(f"window.scrollTo(0,{y})")
            page.wait_for_timeout(160)
            for item in page.evaluate(SAMPLE):
                if item not in found:
                    found.append(item)
            y += step
            h = page.evaluate("document.body.scrollHeight")
        results[fam] = found
        print(f'{fam:11s} {len(found):2d} fallas', flush=True)
    browser.close()

with open('qa_skin_dark.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=1)

print('\n--- detalle ---')
for fam, items in results.items():
    for i in items[:6]:
        print(f"{fam:11s} {i['ratio']:>5} / {i['need']}  {i['sel'][:55]}  \"{i['text']}\"  fg={i['color']} bg={i['bg']}")
print('\nfallas totales:', sum(len(v) for v in results.values()))
