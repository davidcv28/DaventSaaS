"""Capturas QA del rediseño generativo (6 diseños).

Uso: venv/Scripts/python.exe qa_generative.py [tag] [templates...]
Requiere Vite dev en :5173 (proxya /api a :8000). El script maneja el runserver
propio de :8000 y lo reinicia por diseño para evitar el cache locmem del
payload público. Guarda qa/<tag>/<tpl>-<w>-{home,cat,svc,pdp}.png y aplica el
acento por defecto de cada diseño para juzgar la identidad visual.
"""
import os, sys, time, json, threading, subprocess, urllib.request

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright
from StoreApp.domains.stores.models import Store

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
BASE = 'http://localhost:5173/bench-store'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
CAT = API + 'catalog/'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'generative'
ONLY = sys.argv[2:] or None
TEMPLATES = ['raiz', 'alimentos', 'trama', 'boutique', 'circuito', 'seguridad']
# El acento del dueño es un slug del catálogo cerrado STORE_ACCENTS.
ACCENTS = {
    'raiz': 'emerald', 'alimentos': 'rose', 'trama': 'orange',
    'boutique': 'violet', 'circuito': 'sky', 'seguridad': 'rose',
}

server = None


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


def start_server():
    global server
    free_port()
    log = open('qa_server.log', 'ab')
    server = subprocess.Popen([PY, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
                              cwd=ROOT, stdout=log, stderr=log)


def stop_server():
    global server
    if server:
        try:
            server.kill()
        except Exception:
            pass
        try:
            server.wait(timeout=10)
        except Exception:
            pass
        server = None
    free_port()


def set_template(t, accent):
    err = []

    def work():
        try:
            st = Store.objects.get(slug='bench-store')
            c = st.customization
            c.template = t
            c.template_draft = t
            c.accent = accent
            c.save(update_fields=['template', 'template_draft', 'accent'])
        except Exception as e:  # pragma: no cover
            err.append(e)

    th = threading.Thread(target=work)
    th.start()
    th.join()
    if err:
        raise err[0]


def get_json(url):
    return json.load(urllib.request.urlopen(url, timeout=8))


def api_template():
    try:
        return get_json(API).get('customization', {}).get('template')
    except Exception:
        return None


def wait_template(t, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_template() == t:
            return True
        time.sleep(0.5)
    return False


def reveal_all(page):
    page.evaluate("""async () => {
      const h = document.documentElement.scrollHeight
      for (let y = 0; y < h; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)) }
      window.scrollTo(0, 0)
      await new Promise(r => setTimeout(r, 120))
    }""")


def shot(page, path):
    reveal_all(page)
    page.screenshot(path=path, full_page=True)


os.makedirs(f'qa/{OUT}', exist_ok=True)
stop_server()
with sync_playwright() as pw:
    browser = None

    def fresh_browser():
        global browser
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        browser = pw.chromium.launch()

    for tpl in (ONLY or TEMPLATES):
        stop_server()
        set_template(tpl, ACCENTS[tpl])
        start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: server no sirve el diseño', flush=True)
            continue
        try:
            product_id = (get_json(CAT).get('products') or [{}])[0].get('id')
        except Exception:
            product_id = None
        fresh_browser()
        for w, height in [(1440, 1000), (390, 900)]:
            ctx = browser.new_context(viewport={'width': w, 'height': height}, reduced_motion='reduce')
            page = ctx.new_page()
            try:
                page.goto(BASE, wait_until='networkidle', timeout=40000)
                page.wait_for_timeout(900)
                shot(page, f'qa/{OUT}/{tpl}-{w}-home.png')
            except Exception as e:
                print(f'FAIL {tpl} {w} home: {str(e)[:140]}', flush=True)
                fresh_browser()
            finally:
                try:
                    ctx.close()
                except Exception:
                    pass
        for path, tag in [('/catalogo', 'cat'), ('/servicios', 'svc')] + (
                [(f'/producto/{product_id}', 'pdp')] if product_id else []):
            ctx = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
            page = ctx.new_page()
            try:
                page.goto(BASE + path, wait_until='networkidle', timeout=40000)
                page.wait_for_timeout(900)
                shot(page, f'qa/{OUT}/{tpl}-1440-{tag}.png')
            except Exception as e:
                print(f'FAIL {tpl} {tag}: {str(e)[:140]}', flush=True)
                fresh_browser()
            finally:
                try:
                    ctx.close()
                except Exception:
                    pass
        print(f'done {tpl}', flush=True)
    if browser:
        try:
            browser.close()
        except Exception:
            pass
if server is None:
    start_server()
print('listo')
