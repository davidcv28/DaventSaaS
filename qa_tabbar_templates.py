"""QA por plantilla del menú móvil + grilla del catálogo (360/390).
Uso: venv/Scripts/python.exe qa_tabbar_templates.py [templates...]
Cambia customization.template en bench-store (restaura el original al final)
y reinicia el runserver por plantilla para saltar el cache público.
"""
import os, sys, time, json, threading, subprocess, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()
from StoreApp.domains.stores.models import Store
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
HOME = 'http://localhost:5173/bench-store'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
TEMPLATES = sys.argv[1:] or ['terra', 'boutique', 'arena', 'lookbook', 'classic', 'cobre', 'calma', 'atelier']
server = None

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

def start():
    global server
    free_port()
    server = subprocess.Popen([PY, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
                              cwd=ROOT, stdout=open('qa_server.log', 'ab'), stderr=subprocess.STDOUT)

def stop():
    global server
    if server:
        try: server.kill(); server.wait(timeout=10)
        except Exception: pass
        server = None
    free_port()

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

def current_template():
    return Store.objects.get(slug='bench-store').customization.template

def wait_api(t, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            d = json.load(urllib.request.urlopen(API, timeout=3))
            if d.get('customization', {}).get('template') == t: return True
        except Exception:
            pass
        time.sleep(0.7)
    return False

THEME = """() => window.postMessage({ type: 'studio:update',
  theme: { mobile: { nav: 'bottom', gridCols: 2 } } }, window.location.origin)"""
DARK = """() => window.postMessage({ type: 'studio:update', mode: 'dark',
  theme: { mobile: { nav: 'bottom', gridCols: 2 } } }, window.location.origin)"""

MEASURE = """() => {
  const bar = document.querySelector('.sp-tabbar')
  const grids = [...document.querySelectorAll('.sp-grid, [class*="-grid"]')]
    .filter(g => g.querySelector(':scope > .tpc'))
    .map(g => getComputedStyle(g).gridTemplateColumns.split(' ').length)
  return {
    scrollW: document.documentElement.scrollWidth, vw: window.innerWidth,
    bar: bar ? getComputedStyle(bar).display : 'none',
    tabs: [...document.querySelectorAll('.sp-tabbar .sp-tab')].map(b => b.textContent.trim()),
    grids,
    sheetOpen: !!document.querySelector('.cf-sheet'),
    filterBtn: document.querySelector('.cf-open') ? getComputedStyle(document.querySelector('.cf-open')).display : 'none'
  }
}"""

orig = current_template()
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tpl in TEMPLATES:
        stop(); set_template(tpl); start()
        if not wait_api(tpl):
            print(f'WARN {tpl}: no levantó'); continue
        for w in (360, 390):
            ctx = browser.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
            page = ctx.new_page()
            page.goto(f'{HOME}?studio=1', wait_until='networkidle', timeout=40000)
            page.evaluate(THEME); page.wait_for_timeout(400)
            r = page.evaluate(MEASURE)
            print(f"{tpl:10} {w} landing bar={r['bar']} tabs={len(r['tabs'])} scrollW={r['scrollW']}/{r['vw']}")
            page.goto(f'{HOME}/catalogo?studio=1', wait_until='networkidle', timeout=40000)
            page.evaluate(THEME); page.wait_for_timeout(700)
            r = page.evaluate(MEASURE)
            print(f"{tpl:10} {w} catalog grids={r['grids']} cf-open={r['filterBtn']} scrollW={r['scrollW']}/{r['vw']}")
            if r['filterBtn'] != 'none':
                page.click('.cf-open'); page.wait_for_timeout(300)
                d = page.evaluate("""() => {
                  const s = document.querySelector('.cf-sheet')
                  return s ? { groups: s.querySelectorAll('.cf-group').length,
                               price: !!s.querySelector('.cf-price'),
                               facets: !!s.querySelector('.cf-opt'),
                               view: s.querySelector('.cf-btn:not(.ghost)')?.textContent.trim() } : null
                }""")
                print(f"           sheet={d}")
                page.keyboard.press('Escape')
            ctx.close()
        # Oscuro: el sheet y la tab bar usan la paleta oscura
        ctx = browser.new_context(viewport={'width': 390, 'height': 900}, reduced_motion='reduce')
        page = ctx.new_page()
        page.goto(f'{HOME}?studio=1', wait_until='networkidle', timeout=40000)
        page.evaluate(DARK); page.wait_for_timeout(400)
        page.click('.sp-tabbar .sp-tab:last-child'); page.wait_for_timeout(300)
        d = page.evaluate("""() => {
          const s = document.querySelector('.sp-more-sheet')
          return { theme: document.querySelector('.store-page')?.dataset.storeTheme,
                   bg: s ? getComputedStyle(s).backgroundColor : null,
                   fg: s ? getComputedStyle(s).color : null }
        }""")
        print(f"{tpl:10} dark sheet={d}")
        ctx.close()
    browser.close()
stop()
set_template(orig)
print('listo (template restaurado:', orig, ')')
