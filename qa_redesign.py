"""QA del redesign landing/servicios: overflow en 6 anchos + capturas.
Uso: venv/Scripts/python.exe qa_redesign.py [--before] [templates...]
Asume vite dev en :5173 ya corriendo; este script levanta/reinicia el
runserver de Django por plantilla (locmem cache) como qa_overflow.py.
"""
import os, sys, time, json, threading, subprocess, urllib.request
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
FRONT = 'http://localhost:5173/bench-store'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
args = [a for a in sys.argv[1:] if not a.startswith('--')]
BEFORE = '--before' in sys.argv
DARK = '--dark' in sys.argv
LONGNAME = '--longname' in sys.argv
TEMPLATES = args or ['classic', 'bloque', 'riso']
WIDTHS = [320, 360, 390, 768, 1024, 1440]
SHOTW = [360, 1440]

from StoreApp.domains.stores.models import Store

def set_state(t=None, theme=None, name=None):
    err = []
    def work():
        try:
            s = Store.objects.get(slug='bench-store')
            c = s.customization
            if t is not None:
                c.template = t
                c.save(update_fields=['template'])
            if name is not None and c.display_name != name:
                c.display_name = name
                c.save(update_fields=['display_name'])
            if theme is not None and c.theme != theme:
                c.theme = theme
                c.save(update_fields=['theme'])
        except Exception as e:
            err.append(e)
    th = threading.Thread(target=work); th.start(); th.join()
    if err: raise err[0]

def api_state():
    try:
        d = json.load(urllib.request.urlopen(API, timeout=5))
        return d.get('customization', {}).get('template'), d.get('store', d).get('name', '')
    except Exception:
        return None, ''

server = None
def start_server():
    global server
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
    time.sleep(0.4)

def wait_template(t, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        tpl, _ = api_state()
        if tpl == t: return True
        time.sleep(0.6)
    return False

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
  const fixed = []
  for (const el of document.querySelectorAll('.sv-bar, .sp-bot, .sp-dock')) {
    const r = el.getBoundingClientRect()
    if (r.height) fixed.push(`${el.className.split(' ')[0]} top=${Math.round(r.top)} bot=${Math.round(r.bottom)}`)
  }
  return { scrollW: doc.scrollWidth, vw, offenders: wide.slice(0, 14), fixed }
}"""

tag = 'before' if BEFORE else 'after'
os.makedirs(f'qa/redesign-{tag}', exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tpl in TEMPLATES:
        stop_server()
        set_state(tpl, theme='dark' if DARK else None)
        if LONGNAME:
            set_state(name=('Tienda Supercalifragilisticoespialidoso de los Andes y del Mar ' * 2)[:60])
        start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: no levantó, salto', flush=True); continue
        for route, rname in [('', 'home'), ('/servicios', 'servicios')]:
            for w in WIDTHS:
                ctx = browser.new_context(viewport={'width': w, 'height': 800})
                page = ctx.new_page()
                try:
                    page.goto(f'{FRONT}{route}', wait_until='networkidle', timeout=30000)
                    page.wait_for_timeout(900)
                    r = page.evaluate(MEASURE)
                    flag = 'OVERFLOW' if r['scrollW'] > r['vw'] + 1 else 'ok'
                    print(f'{tpl:9} {rname:10} {w:5} scrollW={r["scrollW"]} {flag}', flush=True)
                    for o in r['offenders'][:6]:
                        print(f'   └ {o}')
                    if r['fixed']:
                        print(f'   · {" | ".join(r["fixed"])}')
                    if w in SHOTW:
                        page.screenshot(path=f'qa/redesign-{tag}/{tpl}-{rname}-{w}.png', full_page=True)
                except Exception as e:
                    print(f'FAIL {tpl} {rname} {w}: {e}')
                finally:
                    ctx.close()
        print(f'done {tpl}', flush=True)
    browser.close()
if server is None:
    start_server()
print('listo')
