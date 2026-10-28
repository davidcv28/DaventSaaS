"""Auditoría móvil de landings: capturas 360/390/430 claro+oscuro por plantilla.
Uso: venv/Scripts/python.exe qa_mob_audit.py <tag> [templates...]
Guarda qa/<tag>/<tpl>-<w>-light.png y <tpl>-<w>-dark.png (viewport 900px) +
<tpl>-390-full.png (página completa) + reporte de overflow en stdout y
qa/<tag>/overflow.txt.

El modo oscuro se fuerza con ?studio=1 + postMessage studio:update {mode:'dark'}
(el visor Studio pisa data-store-theme sin tocar la DB). Misma danza de server
que qa_shots.py: un runserver propio por plantilla (locmem cachea el payload).
"""
import os, sys, time, json, threading, subprocess, urllib.request
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
HOME = 'http://localhost:5173/bench-store'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'mob-before'
ONLY = sys.argv[2:] or None
WIDTHS = [360, 390, 430]
TEMPLATES = ['classic', 'perspective', 'duo', 'bloque', 'riso', 'terra', 'street', 'atelier',
             'circuit', 'lab', 'mercado', 'carta', 'studio', 'proceso', 'promo', 'shop', 'arena',
             'terminal', 'calma', 'signature', 'vitrina', 'lookbook', 'cobre', 'minimal',
             'boutique', 'aurora']

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
            try: os.kill(int(line.split()[-1]), 9)
            except Exception: pass
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

def reveal_all(page):
    page.evaluate("""async () => {
      const h = document.documentElement.scrollHeight
      for (let y = 0; y < h; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)) }
      window.scrollTo(0, 0)
      await new Promise(r => setTimeout(r, 150))
    }""")

MEASURE = """() => {
  const doc = document.documentElement
  const wide = []
  const vw = window.innerWidth
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect()
    if (r.width > vw + 1 || r.right > vw + 1 || r.left < -1) {
      let clipped = false, p = el.parentElement
      while (p) {
        const cs = getComputedStyle(p)
        if (cs.overflowX === 'hidden' || cs.overflowX === 'clip') { clipped = true; break }
        p = p.parentElement
      }
      if (!clipped) {
        const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 60)
        wide.push(`${el.tagName.toLowerCase()}.${cls} w=${Math.round(r.width)} l=${Math.round(r.left)}`)
      }
    }
    if (wide.length > 14) break
  }
  return { scrollW: doc.scrollWidth, vw, offenders: wide.slice(0, 14) }
}"""

# qa/ está gitignored (el agente no puede leer las capturas); qa_out/ no.
os.makedirs(f'qa_out/{OUT}', exist_ok=True)
report = open(f'qa_out/{OUT}/overflow.txt', 'w', encoding='utf-8')
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tpl in (ONLY or TEMPLATES):
        stop_server(); set_template(tpl); start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: no levantó, salto', flush=True); continue
        for w in WIDTHS:
            for mode in ('light', 'dark'):
                ctx = browser.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
                page = ctx.new_page()
                try:
                    url = HOME if mode == 'light' else f'{HOME}?studio=1'
                    page.goto(url, wait_until='networkidle', timeout=30000)
                    if mode == 'dark':
                        page.evaluate("""() => window.postMessage(
                          { type: 'studio:update', mode: 'dark' }, window.location.origin)""")
                        page.wait_for_timeout(300)
                    page.wait_for_timeout(700)
                    reveal_all(page)
                    page.screenshot(path=f'qa_out/{OUT}/{tpl}-{w}-{mode}.png')
                    if mode == 'light':
                        r = page.evaluate(MEASURE)
                        flag = 'OVERFLOW' if r['scrollW'] > r['vw'] + 1 else 'ok'
                        line = f'{tpl:12} {w} scrollW={r["scrollW"]} vw={r["vw"]} {flag}'
                        print(line); report.write(line + '\n')
                        for o in r['offenders'][:8]:
                            report.write(f'   {o}\n')
                        if w == 390:
                            page.screenshot(path=f'qa_out/{OUT}/{tpl}-{w}-full.png', full_page=True)
                except Exception as e:
                    print(f'FAIL {tpl} {w} {mode}: {str(e)[:120]}')
                finally:
                    ctx.close()
        report.flush()
        print(f'done {tpl}', flush=True)
    browser.close()
report.close()
if server is None:
    start_server()
print('listo')
