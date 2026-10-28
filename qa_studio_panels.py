"""QA de los paneles nuevos del Studio (Diseño > Studio).
Loguea qablocks/qatienda (premium) y ejercita Colores, Tipografía,
Contenedores, Fondo, Móvil y Movimiento: overflow horizontal en los 7
anchos, errores de consola, bloqueo por plan (beneficios simulados vía
route, sin tocar la DB), forzado de dispositivo móvil y presencia de los
controles/hints/tooltips.

Uso: venv/Scripts/python.exe qa_studio_panels.py [--locked] [--width=390]
"""
import sys, json, pathlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'qa_out' / 'studio_panels'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://localhost:5173'
WIDTHS = [320, 360, 390, 768, 1024, 1280, 1920]
ONLY_WIDTH = next((int(a.split('=')[1]) for a in sys.argv[1:] if a.startswith('--width=')), None)
LOCKED = '--locked' in sys.argv
TOOLS = ['Colores', 'Tipografía', 'Contenedores', 'Fondo', 'Móvil', 'Movimiento']
console_msgs, failed_reqs = [], []

# Beneficios simulados: el plan actual queda sin diseño (sin mutar la DB —
# solo se filtra la respuesta de /api/plans/ para este contexto).
def lock_router(route, request):
    if '/api/plans/' in request.url:
        try:
            data = route.fetch().json()
            for p in data if isinstance(data, list) else data.get('results', []):
                b = p.get('benefits') or {}
                # has_customization queda: la sección Diseño existe pero las
                # opciones plus/advanced se bloquean (estado Plan básico).
                for k in ('has_design_plus', 'has_design_advanced'):
                    if k in b and isinstance(b[k], bool):
                        b[k] = False
            return route.fulfill(json=data)
        except Exception:
            pass
    return route.continue_()

def check_overflow(page, w):
    return page.evaluate('''() => ({
      inner: window.innerWidth,
      scroll: document.documentElement.scrollWidth,
      bodyScroll: document.body ? document.body.scrollWidth : 0
    })''')

def open_studio(page):
    page.goto(f'{BASE}/dashboard', wait_until='domcontentloaded')
    page.wait_for_timeout(1800)
    # La guía del primer ingreso tapa la pantalla: se salta si aparece.
    skip = page.locator('.tour-skip')
    if skip.count() and skip.first.is_visible():
        skip.first.click()
        page.wait_for_timeout(400)
    nav = page.locator('[data-tour="nav-store"], [data-tour="tab-store"]')
    if nav.first.is_visible():
        nav.first.click()
    else:
        # El FAB de soporte se superpone al botón "Más" en 320-390 (z 90 vs
        # tabbar): el dispatch evita la intercepción de pointer events.
        page.locator('.tabbar button[aria-controls="more-sheet"]').dispatch_event('click')
        page.wait_for_timeout(400)
        page.locator('.sheet-nav button', has_text='Mi página').first.click()
    page.wait_for_timeout(800)
    page.get_by_role('tab', name='Cómo se ve').first.click()
    page.wait_for_timeout(500)
    page.get_by_role('tab', name='Studio').first.click()
    page.wait_for_selector('.sts', timeout=15000)
    page.wait_for_timeout(2500)  # la preview carga en iframe

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    for w in ([ONLY_WIDTH] if ONLY_WIDTH else WIDTHS):
        ctx = browser.new_context(viewport={'width': w, 'height': 900}, locale='es-AR')
        if LOCKED:
            ctx.route('**/api/**', lock_router)
        page = ctx.new_page()
        tag = f'{w}px'
        page.on('console', lambda m: console_msgs.append(f'{tag} {m.type}: {m.text[:200]}') if m.type in ('error', 'warning') else None)
        page.on('pageerror', lambda e: console_msgs.append(f'{tag} PAGEERROR: {e}'))
        page.on('requestfailed', lambda r: failed_reqs.append(f'{tag} FAILED {r.url[:140]}'))
        page.on('response', lambda r: failed_reqs.append(f'{tag} {r.status} {r.url[:140]}') if r.status >= 400 else None)

        # Login real (el access vive en memoria; el refresh está throtteado).
        page.goto(f'{BASE}/login', wait_until='domcontentloaded')
        page.wait_for_timeout(700)
        page.fill('input[name="username"]', 'qablocks')
        page.fill('input[name="password"]', 'QaBlocks2026!')
        page.evaluate('''() => {
          const f = document.querySelector('form')
          f?.requestSubmit?.()
        }''')
        page.wait_for_timeout(3500)
        if '/dashboard' not in page.url:
            print(f'{tag} !! login no llegó al panel: {page.url}')
            ctx.close()
            continue

        try:
            open_studio(page)
        except Exception as e:
            print(f'{tag} !! no abrió el Studio: {e}')
            page.screenshot(path=str(OUT / f'{w}-fail.png'))
            ctx.close()
            continue

        ov = check_overflow(page, w)
        flag = 'OK ' if ov['scroll'] <= ov['inner'] else 'OVERFLOW'
        print(f'{tag} {flag} scrollWidth={ov["scroll"]} inner={ov["inner"]}')
        page.screenshot(path=str(OUT / f'{w}-studio.png'), full_page=(w < 768))

        # Recorrer las herramientas nuevas del riel.
        for tool in TOOLS:
            btn = page.locator('.sts-tool', has_text=tool).first
            try:
                if w < 768:
                    btn.scroll_into_view_if_needed()
                btn.click(timeout=4000)
                page.wait_for_timeout(600)
                body = page.locator('.sts-panel-body')
                n_fields = body.locator('.stp-field').count()
                n_tips = body.locator('.tip').count()
                n_locks = body.locator('.lock-badge').count() + body.locator('.dl-lock').count()
                print(f'   {tool:<13} campos={n_fields} tips={n_tips} locks={n_locks}')
                safe = tool.lower().replace('í', 'i').replace('ó', 'o').replace('é', 'e')
                page.screenshot(path=str(OUT / f'{w}-{safe}.png'))
                if tool == 'Móvil' and w > 768:
                    active_dev = page.locator('.stcv-seg .stcv-opt[aria-pressed="true"]').first
                    lbl = active_dev.get_attribute('title') or active_dev.inner_text()
                    print(f'      -> dispositivo del lienzo: {lbl}')
            except Exception as e:
                print(f'   {tool:<13} !! {e}')

        # Interacción mínima: un cambio en Tipografía marca el borrador.
        if not LOCKED:
            try:
                page.locator('.sts-tool', has_text='Contenedores').first.click()
                page.wait_for_timeout(400)
                page.locator('.stp-opt', has_text='Recto').first.click()
                page.wait_for_timeout(400)
                dirty = page.locator('.sts-state.dirty').count()
                print(f'   borrador dirty tras cambio: {dirty > 0}')
            except Exception as e:
                print(f'   !! interacción: {e}')

        ctx.close()
    browser.close()

errs = [m for m in console_msgs if 'PAGEERROR' in m or m.split(' ', 2)[1] == 'error:']
print('\n--- errores de consola ---')
print('\n'.join(errs[:30]) if errs else '(ninguno)')
print('--- requests fallidos ---')
print('\n'.join(failed_reqs[:30]) if failed_reqs else '(ninguno)')
