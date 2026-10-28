"""QA de la migración landing=sistema Cobre: para cada plantilla verifica en
/bench-store (home) que data-store-template=<tpl> (piel propia), que la
landing monta el sistema de bloques compartido (.sp-* + hero propio) y que
no hay overflow horizontal a los anchos de Regla 0.
Uso: venv/Scripts/python.exe qa_landing_cobre.py [templates...]
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
ONLY = sys.argv[1:] or ['cobre', 'classic', 'terra', 'circuit', 'promo', 'shop', 'aurora', 'atelier']

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

CHECK = """(tpl) => {
  const root = document.querySelector('.store-page')
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
      if (!clipped) wide.push((el.tagName + '.' + String(el.className?.baseVal ?? el.className ?? '')).slice(0, 70))
    }
    if (wide.length > 8) break
  }
  return {
    design: root?.getAttribute('data-store-template'),
    ident: root?.getAttribute('data-store-tpl'),
    hero: !!document.querySelector('.sp-hero, .sp-cb-hero, .sp-hero-band'),
    blocks: document.querySelectorAll('.sp-page-root > *').length,
    scrollW: document.documentElement.scrollWidth, vw,
    wide: wide.slice(0, 8)
  }
}"""

bad = 0
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tpl in ONLY:
        stop_server(); set_template(tpl); start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: no levantó, salto', flush=True); continue
        ctx = browser.new_context(viewport={'width': 390, 'height': 800}, reduced_motion='reduce')
        page = ctx.new_page()
        page.goto(FRONT, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(900)
        r0 = page.evaluate(CHECK)
        ok0 = r0['design'] == tpl and r0['hero'] and r0['blocks'] > 0
        print(f"{tpl:12} attr={r0['design']}/{r0['ident']} hero={'si' if r0['hero'] else 'NO'} blocks={r0['blocks']} {'OK' if ok0 else 'FAIL'}", flush=True)
        if not ok0: bad += 1
        for w, name in [(320, '320'), (360, '360'), (390, '390'), (430, '430'), (768, '768')]:
            page.set_viewport_size({'width': w, 'height': 800})
            page.wait_for_timeout(400)
            r = page.evaluate(CHECK)
            flag = 'OVERFLOW' if r['scrollW'] > r['vw'] + 1 else 'ok'
            if flag != 'ok':
                bad += 1
                print(f"  {name:5} scrollW={r['scrollW']} vw={r['vw']} {flag} {r['wide'][:3]}", flush=True)
            else:
                print(f"  {name:5} scrollW={r['scrollW']} vw={r['vw']} {flag}", flush=True)
        ctx.close()
        print('done', tpl, flush=True)
    browser.close()
stop_server()
print('FALLOS:', bad, flush=True)
