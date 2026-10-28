"""Shot rápido de los heroes nuevos: home × 390/768/1440 × tpl args.
Uso: venv/Scripts/python.exe qa_hero.py <out> <tpl> [tpl...]
Mismo ciclo server que qa_shots (mata listener de :8000, levanta --noreload).
"""
import os, sys, time, json, threading, subprocess, urllib.request
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
HOME = 'http://localhost:5173/bench-store'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'hero'
TEMPLATES = sys.argv[2:] or ['duo', 'calma', 'vitrina']
WIDTHS = [360, 390, 768, 1280]

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
    th = threading.Thread(target=work)
    th.start(); th.join()
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
        if api_template() == t:
            return True
        time.sleep(0.6)
    return False

def reveal_all(page):
    page.evaluate("""async () => {
      const h = document.documentElement.scrollHeight
      for (let y = 0; y < h; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)) }
      window.scrollTo(0, 0)
      await new Promise(r => setTimeout(r, 150))
    }""")

os.makedirs(f'qa/{OUT}', exist_ok=True)
with sync_playwright() as pw:
    browser = None
    for tpl in TEMPLATES:
        stop_server()
        set_template(tpl)
        start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: server no levantó', flush=True)
            continue
        if browser:
            try: browser.close()
            except Exception: pass
        browser = pw.chromium.launch()
        for w in WIDTHS:
            ctx = browser.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
            page = ctx.new_page()
            try:
                page.goto(HOME, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(700)
                reveal_all(page)
                page.screenshot(path=f'qa/{OUT}/{tpl}-{w}-home.png', full_page=True)
            except Exception as e:
                print(f'FAIL {tpl} {w}: {str(e)[:120]}', flush=True)
            finally:
                try: ctx.close()
                except Exception: pass
        print(f'done {tpl}', flush=True)
    if browser:
        try: browser.close()
        except Exception: pass
if server is None:
    start_server()
print('listo')
