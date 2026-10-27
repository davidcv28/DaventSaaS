"""Capturas QA del catálogo público por plantilla y ancho.
Uso: venv/Scripts/python.exe qa_shots.py <tag> [templates...]
  tag: carpeta destino (qa/before, qa/after)
  templates: opcional, subset. Default: todas.
Guarda qa/<tag>/<tpl>-<w>-cat.png (catálogo con ?category=8 → facetas visibles),
qa/<tag>/<tpl>-<w>-cat-open.png (panel de filtros abierto, si hay trigger)
y qa/<tag>/<tpl>-<w>.png (sin filtros).

El payload público se cachea server-side en locmem (sin REDIS_URL en dev), así
que el bump del post_save no alcanza: por cada plantilla se reinicia el
runserver propio en :8000 para arrancar con el cache vacío. El script asume
que el puerto 8000 quedó libre (matar el runserver previo antes de correrlo).
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
OUT = sys.argv[1] if len(sys.argv) > 1 else 'before'
ONLY = sys.argv[2:] or None
WIDTHS = [320, 360, 390, 768, 1024, 1440]
MOBILE = {320, 360, 390, 768}
TEMPLATES = ['classic', 'perspective', 'duo', 'bloque', 'riso', 'terra', 'street', 'atelier',
             'circuit', 'lab', 'mercado', 'carta', 'studio', 'proceso', 'promo', 'shop', 'arena',
             'terminal', 'calma', 'signature', 'vitrina', 'lookbook', 'cobre', 'minimal',
             'boutique', 'aurora']

from StoreApp.domains.stores.models import Store

def set_template(t):
    # ORM dentro de un thread: sync_playwright deja un event loop en el main
    # thread y Django rechaza ORM síncrono ahí (SynchronousOnlyOperation).
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

server = None
def start_server():
    # runserver propio en :8000 (--noreload = proceso único, kill limpio).
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
        if api_template() == t:
            return True
        time.sleep(0.6)
    return False

def reveal_all(page):
    # v-reveal oculta los bloques hasta que el IO los ve; en una captura
    # full-page quedan invisibles. Scroll en pasos para dispararlos.
    page.evaluate("""async () => {
      const h = document.documentElement.scrollHeight
      for (let y = 0; y < h; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)) }
      window.scrollTo(0, 0)
      await new Promise(r => setTimeout(r, 150))
    }""")

def shot(page, path):
    reveal_all(page)
    page.screenshot(path=path, full_page=True)

os.makedirs(f'qa/{OUT}', exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tpl in (ONLY or TEMPLATES):
        # Orden: cortar el server viejo → update en DB → server fresco (cache
        # vacío) → esperar a que la API sirva la plantilla nueva.
        stop_server()
        set_template(tpl)
        start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: el server no levantó con la plantilla, salto', flush=True)
            continue
        for w in WIDTHS:
            # Contexto aislado por captura: la API manda max_age=30 y un
            # contexto compartido serviría el payload del diseño anterior.
            # reduced_motion='reduce': la directiva v-reveal marca .is-in al
            # instante — sin esto las tarjetas bajo el fold quedan invisibles
            # en la captura (IntersectionObserver nunca las ve).
            ctx = browser.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
            page = ctx.new_page()
            try:
                # Estado con categoría (facetas visibles)
                page.goto(f'{FRONT}?category=8', wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(700)
                shot(page, f'qa/{OUT}/{tpl}-{w}-cat.png')
                # Abrir el panel/drawer de filtros si hay trigger en móvil
                if w in MOBILE:
                    # El sheet de filtros lo abre el trigger de la toolbar;
                    # el burger quedó solo para navegación del sitio.
                    for sel in ['.cf-open', '.cv-sh-filter-btn', '.sp-burger']:
                        try:
                            btn = page.locator(sel).first
                            if btn.count() and btn.is_visible():
                                btn.click()
                                page.wait_for_timeout(500)
                                shot(page, f'qa/{OUT}/{tpl}-{w}-cat-open.png')
                                break
                        except Exception:
                            pass
                page.goto(FRONT, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(700)
                shot(page, f'qa/{OUT}/{tpl}-{w}.png')
            except Exception as e:
                print(f'FAIL {tpl} {w}: {e}')
            finally:
                ctx.close()
        print(f'done {tpl}', flush=True)
    browser.close()
# El último server queda vivo para seguir trabajando (el hijo no muere con el
# script en Windows). Si se cortó por WARN, levantar uno limpio igual.
if server is None:
    start_server()
print('listo')
