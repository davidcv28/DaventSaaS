"""QA del menú móvil de la landing (tab bar + sheet) y del filtro/grilla del
catálogo. Uso: venv/Scripts/python.exe qa_tabbar_catalog.py
Levanta un runserver propio (el payload público se cachea en locmem) y maneja
el tema mobile.nav por postMessage del Studio (?studio=1), sin tocar la DB.
"""
import os, sys, time, json, subprocess, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
HOME = 'http://localhost:5173/bench-store'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
OUT = os.path.join(ROOT, 'qa_out', 'tabbar')
os.makedirs(OUT, exist_ok=True)

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

def start_server():
    global server
    free_port()
    log = open('qa_server.log', 'ab')
    server = subprocess.Popen([PY, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
                              cwd=ROOT, stdout=log, stderr=log)

def wait_api(timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(API, timeout=3)
            return True
        except Exception:
            time.sleep(0.7)
    return False

THEME = """() => window.postMessage({ type: 'studio:update',
  theme: { mobile: { nav: 'bottom', gridCols: 2 } } }, window.location.origin)"""

MEASURE = """() => {
  const bar = document.querySelector('.sp-tabbar')
  const dock = document.querySelector('.sp-dock')
  const cs = bar ? getComputedStyle(bar) : null
  const br = bar?.getBoundingClientRect()
  const dr = dock?.getBoundingClientRect()
  const grids = [...document.querySelectorAll('.sp-grid, [class*="-grid"]')]
    .filter(g => g.querySelector(':scope > .tpc'))
    .map(g => ({ cls: g.className, cols: getComputedStyle(g).gridTemplateColumns.split(' ').length }))
  return {
    scrollW: document.documentElement.scrollWidth,
    vw: window.innerWidth,
    barDisplay: cs?.display,
    barRect: br ? { top: Math.round(br.top), bottom: Math.round(br.bottom), h: Math.round(br.height) } : null,
    dockRect: dr ? { top: Math.round(dr.top), bottom: Math.round(dr.bottom) } : null,
    labels: [...document.querySelectorAll('.sp-tabbar .sp-tab')].map(b => b.textContent.trim()),
    active: document.querySelector('.sp-tabbar .sp-tab.active')?.textContent.trim() || null,
    grids
  }
}"""

report = []
def say(line):
    print(line, flush=True)
    report.append(line)

start_server()
if not wait_api():
    say('FAIL: API no respondió'); sys.exit(1)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for w in (320, 360, 390, 768, 1280):
        ctx = browser.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
        page = ctx.new_page()
        page.goto(f'{HOME}?studio=1', wait_until='networkidle', timeout=40000)
        page.evaluate(THEME)
        page.wait_for_timeout(500)
        r = page.evaluate(MEASURE)
        overflow = 'OVERFLOW' if r['scrollW'] > r['vw'] + 1 else 'ok'
        say(f"landing {w}: bar={r['barDisplay']} labels={r['labels']} active={r['active']} scroll={overflow}")
        if r['barRect'] and r['dockRect']:
            say(f"   bar top={r['barRect']['top']} h={r['barRect']['h']} | dock bottom={r['dockRect']['bottom']}")
        if w <= 768 and r['barDisplay'] != 'none':
            page.click('.sp-tabbar .sp-tab:last-child')
            page.wait_for_timeout(350)
            opened = page.evaluate("""() => ({
              open: document.querySelector('.sp-more-sheet')?.classList.contains('open'),
              focus: document.activeElement?.className,
              links: [...document.querySelectorAll('.sp-more-nav .sp-more-link')].map(a => a.textContent.trim())
            })""")
            say(f"   sheet open={opened['open']} focus={opened['focus']} links={opened['links']}")
            page.screenshot(path=os.path.join(OUT, f'sheet-{w}.png'))
            page.keyboard.press('Escape')
            page.wait_for_timeout(350)
            closed = page.evaluate("""() => ({
              open: document.querySelector('.sp-more-sheet')?.classList.contains('open'),
              focus: document.activeElement?.textContent?.trim()
            })""")
            say(f"   esc -> open={closed['open']} focus={closed['focus']}")

        page.goto(f'{HOME}/catalogo?studio=1', wait_until='networkidle', timeout=40000)
        page.evaluate(THEME)
        page.wait_for_timeout(700)
        r = page.evaluate(MEASURE)
        overflow = 'OVERFLOW' if r['scrollW'] > r['vw'] + 1 else 'ok'
        say(f"catalog {w}: scroll={overflow} grids={r['grids']}")
        btn = page.evaluate("""() => {
          const b = document.querySelector('.cf-open')
          return b ? { display: getComputedStyle(b).display, text: b.textContent.trim() } : null
        }""")
        say(f"   cf-open={btn}")
        if btn and btn['display'] != 'none':
            page.click('.cf-open')
            page.wait_for_timeout(350)
            sheet = page.evaluate("""() => {
              const s = document.querySelector('.cf-sheet')
              return {
                open: !!s,
                groups: s ? s.querySelectorAll('.cf-group').length : 0,
                price: !!s?.querySelector('.cf-price'),
                clear: !!s?.querySelector('.cf-btn.ghost'),
                view: s?.querySelector('.cf-btn:not(.ghost)')?.textContent.trim(),
                dark: document.querySelector('.store-page')?.dataset.storeTheme
              }
            }""")
            say(f"   filter sheet={sheet}")
            page.screenshot(path=os.path.join(OUT, f'filters-{w}.png'))
            page.keyboard.press('Escape')
            page.wait_for_timeout(250)
        ctx.close()
    browser.close()

with open(os.path.join(OUT, 'report.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))
try:
    server.kill()
except Exception:
    pass
print('listo')
