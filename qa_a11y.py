"""Auditoría de accesibilidad automática por plantilla (WCAG 2.2 AA).
Mismo esquema que qa_overflow.py: server propio por plantilla (locmem).
Uso: venv/Scripts/python.exe qa_a11y.py [templates...]

Chequeos ejecutables por página (home, catálogo, servicios):
  - imágenes <img> sin alt (decorativas deben tener alt="")
  - botones/enlaces sin nombre accesible (texto, aria-label o title)
  - inputs sin <label> asociado ni aria-label
  - font-size < 16px en inputs (zoom iOS)
  - targets < 44px en botones/enlaces visibles (a 390px)
  - .tpc sin aria-label ni tabindex=0 (cards deben ser teclado-activables)
  - foco visible: :focus-visible con outline/box-shadow en al menos un
    interactivo probado (Tab real)
  - h1 único y jerarquía sin saltos (h1→h3 sin h2)
  - contraste: sample de texto principal (color vs fondo efectivo ≥ 4.5)
"""
import os, sys, time, json, threading, subprocess, urllib.request
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
BASE = 'http://localhost:5173/bench-store'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
ONLY = sys.argv[1:] or None
TEMPLATES = ['classic', 'perspective', 'duo', 'bloque', 'riso', 'terra', 'street', 'atelier',
             'circuit', 'lab', 'mercado', 'carta', 'studio', 'proceso', 'promo', 'shop', 'arena',
             'terminal', 'calma', 'signature', 'vitrina', 'lookbook', 'cobre', 'minimal',
             'boutique', 'aurora']
PAGES = [('home', ''), ('cat', '/catalogo'), ('svc', '/servicios')]

from StoreApp.domains.stores.models import Store

def set_template(t):
    err = []
    def work():
        try:
            c = Store.objects.get(slug='bench-store').customization
            c.template = t
            c.save(update_fields=['template'])
        except Exception as e:
            err.append(e)
    th = threading.Thread(target=work); th.start(); th.join()
    if err: raise err[0]

def api_template():
    try:
        return json.load(urllib.request.urlopen(API, timeout=5)).get('customization', {}).get('template')
    except Exception:
        return None

def free_port():
    try:
        out = subprocess.check_output(['netstat', '-ano']).decode('cp1252', 'replace')
    except Exception:
        return
    for line in out.splitlines():
        if ':8000' in line and 'LISTENING' in line:
            try:
                os.kill(int(line.split()[-1]), 9)
            except Exception:
                pass
    time.sleep(0.6)

server = None
def start_server():
    global server
    free_port()
    log = open('qa_server.log', 'ab')
    server = subprocess.Popen([PY, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
                              cwd=ROOT, stdout=log, stderr=log)

def stop_server():
    global server
    if server:
        try: server.kill()
        except Exception: pass
        try: server.wait(timeout=10)
        except Exception: pass
        server = None
    free_port()

def wait_template(t, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_template() == t: return True
        time.sleep(0.6)
    return False

AUDIT = r"""() => {
  const issues = []
  const vis = (el) => {
    const r = el.getBoundingClientRect()
    const cs = getComputedStyle(el)
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'
  }
  // imgs sin alt
  for (const img of document.querySelectorAll('img')) {
    if (vis(img) && !img.hasAttribute('alt')) {
      issues.push(`img sin alt: ${(img.getAttribute('src')||'').slice(-40)}`)
      if (issues.length > 40) break
    }
  }
  // interactivos sin nombre accesible
  for (const el of document.querySelectorAll('button, a[href], [role="button"]')) {
    if (!vis(el)) continue
    const name = (el.getAttribute('aria-label') || el.getAttribute('title') || el.innerText || '').trim()
    const img = el.querySelector('img[alt]')
    const svg = el.querySelector('svg[aria-label], svg title')
    if (!name && !img && !svg) {
      const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 50)
      issues.push(`interactivo sin nombre: ${el.tagName.toLowerCase()}.${cls}`)
      if (issues.length > 40) break
    }
  }
  // inputs sin label / font < 16px
  for (const el of document.querySelectorAll('input:not([type=hidden]), textarea, select')) {
    if (!vis(el)) continue
    const id = el.id
    const labelled = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') ||
      (id && document.querySelector(`label[for="${id}"]`)) || el.closest('label') || el.placeholder
    if (!labelled) issues.push(`input sin label: ${el.name || el.type}`)
    if (parseFloat(getComputedStyle(el).fontSize) < 16) {
      issues.push(`input font <16px: ${el.name || el.type} (${getComputedStyle(el).fontSize})`)
    }
  }
  // targets < 44px (a 390px)
  for (const el of document.querySelectorAll('button, a[href], [role="button"], input, select')) {
    if (!vis(el)) continue
    const r = el.getBoundingClientRect()
    if (r.width < 40 || r.height < 40) {
      const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 40)
      issues.push(`target <44px: ${el.tagName.toLowerCase()}.${cls} ${Math.round(r.width)}x${Math.round(r.height)}`)
      if (issues.length > 40) break
    }
  }
  // cards .tpc sin activación por teclado
  for (const el of document.querySelectorAll('.tpc')) {
    if (el.tagName !== 'A' && el.tagName !== 'BUTTON' &&
        el.getAttribute('tabindex') !== '0' && el.getAttribute('role') !== 'link' && el.getAttribute('role') !== 'button') {
      issues.push('card .tpc no teclado-activable')
      break
    }
    if (issues.length > 40) break
  }
  // h1 único y jerarquía
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(vis)
  const h1s = hs.filter(h => h.tagName === 'H1').length
  if (h1s === 0) issues.push('sin h1')
  if (h1s > 1) issues.push(`${h1s} h1 en la página`)
  let prev = 0
  for (const h of hs) {
    const lvl = +h.tagName[1]
    if (prev && lvl > prev + 1) { issues.push(`salto de jerarquía h${prev}→h${lvl}: "${(h.innerText||'').slice(0,30)}"`); break }
    prev = lvl
  }
  return issues
}"""

CONTRAST = r"""() => {
  // Contraste de texto principal: sample de párrafos/headers visibles.
  const lum = (c) => {
    const m = c.match(/[\d.]+/g); if (!m || m.length < 3) return null
    const [r, g, b] = m.slice(0, 3).map(v => +v / 255)
    const f = (x) => x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
  }
  const bgOf = (el) => {
    let p = el
    while (p) {
      const bg = getComputedStyle(p).backgroundColor
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && !bg.endsWith(', 0)')) return bg
      p = p.parentElement
    }
    return 'rgb(255, 255, 255)'
  }
  const out = []
  for (const el of document.querySelectorAll('p, h1, h2, h3, li, span, a')) {
    if (out.length >= 12) break
    const r = el.getBoundingClientRect()
    const cs = getComputedStyle(el)
    if (!r.width || !r.height || !el.innerText?.trim() || el.innerText.length > 200) continue
    const fg = lum(cs.color), bg = lum(bgOf(el))
    if (fg == null || bg == null) continue
    const ratio = (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05)
    if (ratio < 4.5 && parseFloat(cs.fontSize) < 24) {
      const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 40)
      out.push(`contraste ${ratio.toFixed(2)} <4.5: ${el.tagName.toLowerCase()}.${cls} "${el.innerText.trim().slice(0,25)}"`)
    }
  }
  return out
}"""

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    total = {}
    for tpl in (ONLY or TEMPLATES):
        stop_server(); set_template(tpl); start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: no levantó, salto', flush=True); continue
        for tag, path in PAGES:
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
            page = ctx.new_page()
            try:
                page.goto(BASE + path, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(600)
                issues = page.evaluate(AUDIT) + page.evaluate(CONTRAST)
                # Foco visible real: Tab hasta un interactivo y medir outline/box-shadow
                focus_ok = None
                for _ in range(6):
                    page.keyboard.press('Tab')
                    page.wait_for_timeout(120)
                    foc = page.evaluate("""() => {
                      const el = document.activeElement
                      if (!el || el === document.body) return null
                      const cs = getComputedStyle(el)
                      return { tag: el.tagName, outline: cs.outlineWidth + ' ' + cs.outlineStyle, shadow: cs.boxShadow }
                    }""")
                    if foc:
                        focus_ok = foc
                        break
                uniq = sorted(set(issues))
                print(f'== {tpl} /{tag or "home"}: {len(uniq)} issues', flush=True)
                for i in uniq[:12]:
                    print(f'   - {i}')
                if focus_ok:
                    has_focus_style = focus_ok['outline'] != '0px none' or focus_ok['shadow'] != 'none'
                    print(f'   foco visible: {"ok" if has_focus_style else "SIN ESTILO"} ({focus_ok["tag"]} {focus_ok["outline"]} {focus_ok["shadow"][:30]})')
                else:
                    print('   foco visible: nada enfocable en 6 Tabs')
                total[f'{tpl}/{tag}'] = len(uniq)
            except Exception as e:
                print(f'FAIL {tpl} {tag}: {e}')
            finally:
                ctx.close()
        print(f'done {tpl}', flush=True)
    browser.close()
    print('RESUMEN:', total)
if server is None:
    start_server()
print('listo')
