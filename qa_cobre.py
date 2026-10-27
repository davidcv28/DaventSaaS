"""Capturas QA de la seccion "Que ofrecemos" (sp-services) en la landing
cobre. Setea template+servicios en bench-store, espera el TTL del cache
publico (120s si hace falta) y guarda full-page + recorte de la seccion
en varios anchos.

Uso: venv/Scripts/python.exe qa_cobre.py <tag>
"""
import os, sys, time, json, threading, urllib.request
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONT = 'http://localhost:5173/bench-store'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'cobre'
WIDTHS = [1440, 1024, 768, 390]

SERVICES = [
    {'icon': 'truck',   'title': 'Envios a todo el pais',  'text': 'Despachamos en 24/48 hs por Correo Argentino con seguimiento online.'},
    {'icon': 'credit-card', 'title': 'Todos los medios de pago', 'text': 'Efectivo, transferencia, tarjetas y Mercado Pago. 3 cuotas sin interes.'},
    {'icon': 'scissors', 'title': 'Ajustes y arreglos', 'text': 'Entallado y arreglos de prendas en el local, sin cargo en compras del mes.'},
    {'icon': 'shield-check', 'title': 'Cambios sin drama', 'text': 'Tenés 30 dias para cambiar por talle o color. La prenda tiene que estar sin uso.'},
]

from StoreApp.domains.stores.models import Store

def seed():
    err = []
    def work():
        try:
            c = Store.objects.get(slug='bench-store').customization
            c.template = 'cobre'
            c.services = SERVICES
            c.show_services = True
            c.services_title = ''
            c.save(update_fields=['template', 'services', 'show_services', 'services_title'])
        except Exception as e:
            err.append(e)
    th = threading.Thread(target=work)
    th.start(); th.join()
    if err: raise err[0]

def api_state():
    try:
        d = json.load(urllib.request.urlopen(API, timeout=5))
        c = d.get('customization', {})
        return c.get('template'), len(d.get('services') or c.get('services') or [])
    except Exception:
        return None, 0

def wait_ready(timeout=190):
    deadline = time.time() + timeout
    while time.time() < deadline:
        tpl, n = api_state()
        if tpl == 'cobre' and n >= len(SERVICES):
            return True
        time.sleep(3)
    return False

def reveal_all(page):
    page.evaluate("""async () => {
      const h = document.documentElement.scrollHeight
      for (let y = 0; y < h; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)) }
      window.scrollTo(0, 0)
      await new Promise(r => setTimeout(r, 120))
    }""")

seed()
if not wait_ready():
    print('WARN: la API no refleja cobre+services a tiempo; capturo igual', flush=True)

os.makedirs(f'qa/{OUT}', exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for w in WIDTHS:
        ctx = browser.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
        page = ctx.new_page()
        try:
            page.goto(FRONT, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(700)
            reveal_all(page)
            page.screenshot(path=f'qa/{OUT}/cobre-{w}.png', full_page=True)
            el = page.locator('.sp-services')
            if el.count():
                el.screenshot(path=f'qa/{OUT}/cobre-{w}-services.png')
        except Exception as e:
            print(f'FAIL {w}: {e}')
        finally:
            ctx.close()
        print(f'done {w}', flush=True)
    browser.close()
print('listo')
