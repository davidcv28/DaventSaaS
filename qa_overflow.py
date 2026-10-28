"""Chequeo de overflow horizontal a 320px por plantilla.
Misma danza que qa_shots.py: reinicia el runserver por plantilla (locmem cache).
Uso: venv/Scripts/python.exe qa_overflow.py [templates...]
"""
import os, sys, time, json, threading, subprocess, urllib.request
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
FRONT = 'http://localhost:5173/bench-store/catalogo'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
ONLY = sys.argv[1:] or None
TEMPLATES = ['classic', 'duo', 'calma', 'vitrina', 'cobre', 'minimal']

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
    #En Windows SO_REUSEADDR permite doble bind sobre :8000 — un runserver
    #zombie (warm locmem) responde con el template/cache viejos. Matamos todo
    #listener por PID antes de levantar el propio.
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

MEASURE = """() => {
  const doc = document.documentElement
  const wide = []
  const vw = window.innerWidth
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect()
    if (r.width > vw + 1 || r.right > vw + 1 || r.left < -1) {
      // Ignora elementos dentro de contenedores con overflow oculto (clip)
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

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tpl in (ONLY or TEMPLATES):
        stop_server(); set_template(tpl); start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: no levantó, salto', flush=True); continue
        for w, h, name in [(320, 700, '320'), (360, 340, 'landscape'), (430, 700, '430'), (390, 700, '390')]:
            ctx = browser.new_context(viewport={'width': w, 'height': h}, reduced_motion='reduce')
            page = ctx.new_page()
            try:
                page.goto(f'{FRONT}?category=8', wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(700)
                r = page.evaluate(MEASURE)
                flag = 'OVERFLOW' if r['scrollW'] > r['vw'] + 1 else 'ok'
                print(f'{tpl:12} {name:9} scrollW={r["scrollW"]} vw={r["vw"]} {flag}')
                for o in r['offenders'][:8]:
                    print(f'   └ {o}')
            except Exception as e:
                print(f'FAIL {tpl} {name}: {e}')
            finally:
                ctx.close()
        print(f'done {tpl}', flush=True)
    browser.close()
if server is None:
    start_server()
print('listo')
