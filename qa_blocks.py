"""QA del editor de Bloques (Dashboard > Mi pagina > Bloques).
Loguea qablocks/qatienda, ejercita los flujos del editor y reporta
errores de consola, requests fallidos y estado de la vista previa.
FASE 1: carrera de guardados (PATCH demorado + edicion en vuelo),
fallo -> Reintentar conservando el draft, preview same-origin.
Uso: venv/Scripts/python.exe qa_blocks.py [--width=1440]
"""
import sys, json, time, pathlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'qa_out' / 'blocks'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://localhost:5173'
WIDTH = 1440
SLOW_PATCH = '--slow-patch' in sys.argv
FAIL_PATCH = '--fail-patch' in sys.argv
for a in sys.argv[1:]:
    if a.startswith('--width='):
        WIDTH = int(a.split('=')[1])

console_msgs, failed_reqs, patches = [], [], []

def router(route, request):
    if request.method == 'PATCH' and 'customization' in request.url:
        patches.append(time.time())
        if FAIL_PATCH:
            return route.fulfill(status=400, content_type='application/json',
                                 body=json.dumps({'layout_config': ['Error QA simulado']}))
        if SLOW_PATCH:
            time.sleep(2.0)
    return route.continue_()

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': WIDTH, 'height': 1000}, locale='es-AR')
    if SLOW_PATCH or FAIL_PATCH:
        ctx.route('**/api/**', router)
    page = ctx.new_page()
    page.on('console', lambda m: console_msgs.append(f'{m.type}: {m.text[:300]}'))
    page.on('pageerror', lambda e: console_msgs.append(f'PAGEERROR: {e}'))
    page.on('requestfailed', lambda r: failed_reqs.append(f'FAILED {r.url[:160]} {r.failure}'))
    page.on('response', lambda r: failed_reqs.append(f'{r.status} {r.url[:160]}') if r.status >= 400 else None)

    resp = ctx.request.post(f'{BASE}/api/token/', data={'username': 'qablocks', 'password': 'QaBlocks2026!', 'remember': True})
    print('login:', resp.status)
    if resp.status != 200:
        print(resp.text()[:400]); sys.exit(1)

    page.goto(f'{BASE}/dashboard', wait_until='domcontentloaded')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.setItem("davent:tour:done", "1")')
    page.reload(wait_until='domcontentloaded')
    try:
        page.wait_for_selector('.page-head, .tabbar, main.main', timeout=20000)
    except Exception:
        page.screenshot(path=str(OUT / f'{WIDTH}-fail.png'))
        print('URL:', page.url)
        print('body[:400]:', page.evaluate('document.body.innerText.slice(0,400)'))
        print('classes:', page.evaluate('[...document.querySelectorAll("body *")].slice(0,60).map(e=>e.className).filter(Boolean).slice(0,30)'))
        raise
    page.wait_for_timeout(2500)

    # Navegar a la seccion de la web: sidebar "Mi pagina" en desktop,
    # tabbar "Mi web" en movil.
    if page.locator('.tabbar').count():
        page.evaluate('''() => {
          const b = [...document.querySelectorAll('.tabbar button')].find(x => /web|página|pagina/i.test(x.innerText))
          if (b) b.click()
        }''')
    else:
        page.click('button[data-tour="nav-store"], .sidebar button:has-text("Mi página"), .side-panel button:has-text("Mi página")')
    page.wait_for_timeout(1200)
    page.click('button:has-text("Bloques")')
    page.wait_for_timeout(1800)

    def save_txt():
        return page.locator('.blk-save').inner_text().strip().replace('\n', ' ')

    # --- Flujo 1: toggle ---
    toggles = page.locator('.blk-row:not(.locked) .blk-toggle input')
    if toggles.count() > 2:
        toggles.nth(2).click()
        page.wait_for_timeout(1400)
        print('save tras toggle:', save_txt())

    # --- Flujo 2: mover ---
    page.locator('.blk-row:not(.locked) .blk-mv').nth(1).click()
    page.wait_for_timeout(1400)
    print('save tras mover:', save_txt())

    # --- Flujo 3: variante / titulo ---
    sel = page.locator('.blk-select').first
    if sel.count() and sel.locator('option').count() > 1:
        sel.select_option(index=1)
        page.wait_for_timeout(1400)
        print('save tras variante:', save_txt())
    tin = page.locator('.blk-input').first
    if tin.count():
        tin.fill('Titulo QA')
        page.wait_for_timeout(1400)
        print('save tras titulo:', save_txt())

    # --- Flujo 4: undo/redo + reset ---
    page.locator('button[aria-label="Deshacer"]').click()
    page.wait_for_timeout(300)
    page.locator('button[aria-label="Rehacer"]').click()
    page.wait_for_timeout(1400)
    print('save tras undo/redo:', save_txt())
    page.locator('button:has-text("Restablecer")').click()
    page.wait_for_timeout(1400)
    print('save tras reset:', save_txt())

    # --- Flujo 5: carrera — edicion durante un PATCH en vuelo ---
    if SLOW_PATCH:
        t0 = len(patches)
        toggles.nth(3).click()          # dispara PATCH lento
        page.wait_for_timeout(1300)     # el PATCH ya salio y sigue en vuelo
        print('estado en vuelo:', save_txt())
        toggles.nth(4).click()          # edicion durante el vuelo
        page.wait_for_timeout(4500)     # PATCH1 aterriza -> re-save del draft nuevo
        print('PATCHes disparados:', len(patches) - t0, '| estado final:', save_txt())

    # --- Flujo 6: fallo -> Reintentar conserva el draft ---
    if FAIL_PATCH:
        toggles.nth(3).click()
        page.wait_for_timeout(1600)
        print('estado tras fallo:', save_txt())
        has_retry = page.locator('.blk-save .blk-link', has_text='Reintentar').count()
        print('boton Reintentar visible:', bool(has_retry))
        # el draft no se pisio: el toggle quedo como quedo el usuario
        off_rows = page.locator('.blk-row.off').count()
        print('rows apagadas conservadas:', off_rows)
    else:
        off_rows = page.locator('.blk-row.off').count()

    # --- Vista previa: same-origin + estados ---
    page.screenshot(path=str(OUT / f'{WIDTH}-editor.png'), full_page=True)
    tabs = page.locator('.dsg-tab')
    tabs.first.click()
    page.wait_for_timeout(1200)
    iframe_state = page.evaluate('''async () => {
      const f = document.querySelector('.blk-frame iframe')
      if (!f) return { iframe: false }
      let inner = null
      try { inner = { title: f.contentDocument?.title, ready: f.contentDocument?.readyState, bodyLen: f.contentDocument?.body?.innerHTML?.length } }
      catch (e) { inner = 'cross-origin: ' + e.message }
      return { iframe: true, src: f.src, state: f.closest('.blk-frame')?.dataset.state, inner }
    }''')
    print('IFRAME:', json.dumps(iframe_state, ensure_ascii=False))
    page.wait_for_timeout(2500)
    frame_el = page.locator('.blk-frame')
    print('frame data-state tras wait:', frame_el.get_attribute('data-state'))
    print('fail visible:', page.locator('.blk-frame-fail').count())

    page.screenshot(path=str(OUT / f'{WIDTH}-preview.png'))
    print('\nPATCHes customization:', len(patches))
    print('--- CONSOLE ---')
    for m in console_msgs[:40]:
        print(m)
    print('--- NETWORK ISSUES ---')
    for m in failed_reqs[:40]:
        print(m)
    browser.close()
print('listo ->', OUT)
