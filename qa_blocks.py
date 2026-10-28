"""QA del editor de Bloques (Dashboard > Mi pagina > Bloques).
Loguea qablocks/qatienda y ejercita los flujos del editor reportando
errores de consola, requests fallidos y estado de la vista previa.
FASE 1: carrera de guardados, fallo->Reintentar, preview same-origin.
FASE 2: drag&drop, Alt+flechas, Agregar/Quitar, sync con preview, Ctrl+Z.
Uso: venv/Scripts/python.exe qa_blocks.py [--width=375] [--slow-patch] [--fail-patch]
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

    # Login por el formulario real: devuelve el access en el body (el
    # endpoint de refresh está throtteado por IP y lo agotaría el QA).
    page.goto(f'{BASE}/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('''() => {
      const f = document.querySelector('form')
      f?.dispatchEvent(new Event('submit', {cancelable: true}))
      f?.requestSubmit?.()
    }''')
    page.wait_for_timeout(4000)
    print('post-login url:', page.url)

    # Sin reload: el access vive en memoria y el refresh está throtteado.
    # El tour se quita del DOM directo (localStorage sirve solo a futuros loads).
    page.evaluate('''() => {
      localStorage.setItem("davent:tour:done", "1")
      document.querySelectorAll('.tour, .tour-overlay, [class*="tour"], [data-tour-overlay]').forEach(e => {
        if (e.className && /tour/i.test(e.className)) e.remove()
      })
    }''')
    page.wait_for_timeout(2000)
    try:
        page.wait_for_selector('.page-head, .tabbar, main.main', timeout=20000)
    except Exception:
        page.screenshot(path=str(OUT / f'{WIDTH}-fail.png'))
        print('URL:', page.url)
        print('body[:400]:', page.evaluate('document.body.innerText.slice(0,400)'))
        raise
    page.wait_for_timeout(2500)

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

    def names(sel='.blk-list:not(.avail) .blk-row strong'):
        return page.evaluate(f'''() => [...document.querySelectorAll("{sel}")].map(e => e.textContent.trim())''')

    print('activos:', names()[:8])
    print('disponibles:', names('.blk-list.avail .blk-row strong')[:6])
    print('aria-live:', page.locator('.sr-only[role=status]').count())

    # --- F2.1 Alt+flechas: bajar el 2do bloque ---
    before = names()
    page.locator('.blk-list:not(.avail) .blk-grip').nth(1).click()
    page.keyboard.press('Alt+ArrowDown')
    page.wait_for_timeout(400)
    after = names()
    print('Alt+Down reordena:', before[1:4], '->', after[1:4], '|', 'OK' if before[1] != after[1] and before[1] == after[2] else 'FAIL')
    print('announce:', page.locator('.sr-only[role=status]').inner_text())
    page.wait_for_timeout(1200)
    print('save tras Alt+Down:', save_txt())

    # --- F2.2 drag & drop real con el asa ---
    before = names()
    grip = page.locator('.blk-list:not(.avail) .blk-grip').nth(0)
    box = grip.bounding_box()
    row_h = page.locator('.blk-list:not(.avail) .blk-row').nth(0).bounding_box()['height']
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    page.mouse.down()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2 + row_h * 2.5, steps=12)
    page.mouse.up()
    page.wait_for_timeout(400)
    after = names()
    print('drag 1er->3ro:', before[:4], '->', after[:4], '|', 'OK' if before[0] in after[1:4] else 'FAIL')
    page.wait_for_timeout(1200)
    print('save tras drag:', save_txt())

    # --- F2.3 Quitar -> disponibles, Agregar -> activos ---
    n_act0, n_av0 = len(names()), len(names('.blk-list.avail .blk-row strong'))
    page.locator('.blk-list:not(.avail) .blk-quit').first.click()
    page.wait_for_timeout(400)
    n_act1, n_av1 = len(names()), len(names('.blk-list.avail .blk-row strong'))
    print('quitar:', n_act0, '->', n_act1, 'activos /', n_av0, '->', n_av1, 'disponibles')
    page.locator('.blk-list.avail .blk-add').last.click()
    page.wait_for_timeout(400)
    print('agregar:', len(names()), 'activos | ultimo:', names()[-1])
    page.wait_for_timeout(1200)
    print('save tras quitar/agregar:', save_txt())

    # --- F2.4 toggle + variante + titulo ---
    toggles = page.locator('.blk-list:not(.avail) .blk-row:not(.locked) .blk-toggle input')
    if toggles.count() > 2:
        toggles.nth(2).click()
        page.wait_for_timeout(1300)
        print('save tras toggle->disponibles:', save_txt())
        page.locator('.blk-list.avail .blk-add').last.click()
        page.wait_for_timeout(1300)
        print('save tras re-agregar:', save_txt())
    sel = page.locator('.blk-select').first
    if sel.count() and sel.locator('option').count() > 1:
        sel.select_option(index=1)
        page.wait_for_timeout(1300)
        print('save tras variante:', save_txt())
    tin = page.locator('.blk-input').first
    if tin.count():
        tin.fill('Titulo QA')
        page.wait_for_timeout(1300)
        print('save tras titulo:', save_txt())

    # --- F2.5 click en fila -> scroll+highlight en preview ---
    page.wait_for_selector('.blk-frame[data-state="ready"]', timeout=15000)
    page.wait_for_timeout(800)
    page.evaluate('document.querySelector(".blk-frame iframe")?.contentWindow?.scrollTo(0,0)')
    # Clic a un bloque que siempre se renderiza (sin badge "Sin contenido"):
    # los auto-ocultos por falta de datos no tienen sección a la que scrollear.
    target = page.evaluate('''() => {
      const rows = [...document.querySelectorAll('.blk-list:not(.avail) .blk-row')]
      const c = rows.findIndex(r => r.dataset.bid === 'contact')
      if (c !== -1) return c
      let i = -1
      rows.forEach((r, k) => { if (!r.querySelector('.blk-tag.empty')) i = k })
      return i
    }''')
    page.locator('.blk-list:not(.avail) .blk-row').nth(target).click()
    page.wait_for_timeout(1200)
    scroll = page.evaluate('document.querySelector(".blk-frame iframe")?.contentWindow?.scrollY ?? -1')
    selid = page.evaluate('document.querySelector(".blk-row.sel")?.dataset.bid || null')
    print('click fila idx', target, '-> scrollY:', scroll, '| sel:', selid, '|', 'OK' if selid and scroll > 0 else 'PARCIAL')

    # --- F2.6 Ctrl+Z / Ctrl+Shift+Z ---
    page.keyboard.press('Control+z')
    page.wait_for_timeout(400)
    print('save tras Ctrl+Z:', save_txt())
    page.keyboard.press('Control+Shift+z')
    page.wait_for_timeout(1400)
    print('save tras Ctrl+Shift+Z:', save_txt())

    # --- restablecer + superficies ---
    page.locator('button:has-text("Restablecer")').click()
    page.wait_for_timeout(1400)
    print('save tras reset:', save_txt())

    # --- F1: carrera ---
    if SLOW_PATCH:
        t0 = len(patches)
        tg = page.locator('.blk-list.avail .blk-toggle input')
        if not tg.count():
            tg = page.locator('.blk-list:not(.avail) .blk-row:not(.locked) .blk-toggle input')
        tg.first.click()
        page.wait_for_timeout(1300)
        print('estado en vuelo:', save_txt())
        page.locator('.blk-list:not(.avail) .blk-grip').nth(0).click()
        page.keyboard.press('Alt+ArrowDown')
        page.wait_for_timeout(4500)
        print('PATCHes disparados:', len(patches) - t0, '| estado final:', save_txt())

    if FAIL_PATCH:
        page.locator('.blk-list.avail .blk-add').first.click()
        page.wait_for_timeout(1600)
        print('estado tras fallo:', save_txt())
        print('boton Reintentar visible:', bool(page.locator('.blk-save .blk-link', has_text='Reintentar').count()))
        print('rows en activos conservadas:', len(names()))

    page.screenshot(path=str(OUT / f'{WIDTH}-editor.png'), full_page=True)
    iframe_state = page.evaluate('''async () => {
      const f = document.querySelector('.blk-frame iframe')
      if (!f) return { iframe: false }
      let inner = null
      try { inner = { title: f.contentDocument?.title, ready: f.contentDocument?.readyState, blks: f.contentDocument?.querySelectorAll('[data-blk]')?.length } }
      catch (e) { inner = 'cross-origin: ' + e.message }
      return { iframe: true, src: f.src, state: f.closest('.blk-frame')?.dataset.state, inner }
    }''')
    print('IFRAME:', json.dumps(iframe_state, ensure_ascii=False))
    page.wait_for_timeout(2000)
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
