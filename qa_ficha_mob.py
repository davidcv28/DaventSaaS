"""QA móvil de la ficha de producto: verifica que .spd-top quede en una
columna y la imagen apilada sobre el panel de compra en 390px.
Uso: venv/Scripts/python.exe qa_ficha_mob.py [templates...]
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
CAT = API + 'catalog'
ONLY = sys.argv[1:] or ['duo', 'bloque', 'shop', 'classic']

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

def api_get(url):
    try:
        return json.load(urllib.request.urlopen(url, timeout=5))
    except Exception:
        return None

def api_template():
    data = api_get(API)
    return (data or {}).get('customization', {}).get('template')

def product_id():
    data = api_get(CAT) or {}
    prods = data.get('products') or []
    return prods[0]['id'] if prods else None

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

def wait_template(t, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_template() == t: return True
        time.sleep(0.6)
    return False

MEASURE = """() => {
  const top = document.querySelector('.spd-top')
  const gal = document.querySelector('.spd-gallery')
  const img = document.querySelector('.spd-gallery img')
  const buy = document.querySelector('.spd-buy')
  const promo = document.querySelector('.sp-shop-promo.has-img')
  const pmedia = document.querySelector('.sp-shop-promo.has-img .sp-shop-promo-media')
  const r = {}
  const box = (el) => el ? (() => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) } })() : null
  if (top) r.top_cols = getComputedStyle(top).gridTemplateColumns
  r.gallery = box(gal); r.img = box(img); r.buy = box(buy)
  if (promo) { r.promo_cols = getComputedStyle(promo).gridTemplateColumns; r.promo_media = box(pmedia) }
  r.vw = window.innerWidth
  return r
}"""

os.makedirs('qa_out/ficha-mob', exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tpl in ONLY:
        if server is None or tpl != ONLY[0]:
            if server: server.kill(); server = None
            free_port(); set_template(tpl); start_server()
        if not wait_template(tpl):
            print(f'WARN {tpl}: no levantó, salto', flush=True); continue
        pid = product_id()
        for w in (390,):
            ctx = browser.new_context(viewport={'width': w, 'height': 900}, reduced_motion='reduce')
            page = ctx.new_page()
            try:
                if pid:
                    page.goto(f'{HOME}/producto/{pid}', wait_until='networkidle', timeout=30000)
                    page.wait_for_timeout(700)
                    r = page.evaluate(MEASURE)
                    gal, img, buy = r.get('gallery'), r.get('img'), r.get('buy')
                    gy = (gal or {}).get('y'); by = (buy or {}).get('y')
                    order = 'col-ok' if (gy is not None and by is not None and gy < by) else 'ROW?'
                    bleed = ''
                    if gal and img and gal.get('h') is not None:
                        bot_g, bot_i = gal['y'] + gal['h'], img['y'] + img['h']
                        if img['y'] < gal['y'] - 2 or bot_i > bot_g + 2:
                            bleed = f'BLEED img={img["y"]}..{bot_i} gal={gal["y"]}..{bot_g}'
                    print(f'{tpl:10} {w} cols={r.get("top_cols")!r} gal={gal} img={img} buy_y={by} {order} {bleed}', flush=True)
                    page.screenshot(path=f'qa_out/ficha-mob/{tpl}-{w}-ficha.png')
                else:
                    print(f'{tpl}: sin productos', flush=True)
                # shop landing promo
                if tpl == 'shop':
                    page.goto(HOME, wait_until='networkidle', timeout=30000)
                    page.wait_for_timeout(700)
                    r = page.evaluate(MEASURE)
                    print(f'{tpl:10} {w} promo_cols={r.get("promo_cols")!r} media={r.get("promo_media")}', flush=True)
                    page.screenshot(path=f'qa_out/ficha-mob/shop-{w}-promo.png')
            except Exception as e:
                print(f'FAIL {tpl} {w}: {str(e)[:140]}')
            finally:
                ctx.close()
        print(f'done {tpl}', flush=True)
    browser.close()
print('listo')
