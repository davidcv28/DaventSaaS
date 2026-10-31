"""QA E2E — herramientas nuevas del Studio (Diseño, Estilo, Iconos, modo noche).

Login qablocks2 -> /dashboard/diseno/studio -> elige diseño, estilo y set de
iconos; verifica que la vista previa siga viva, sin errores de consola ni
404 de assets. Shots en qa/studio-design/.

Uso: venv/Scripts/python.exe qa_studio_design.py [base_url]
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:5199'
OUT = 'qa/studio-design'
os.makedirs(OUT, exist_ok=True)
errors, failed, results = [], [], []


def ok(name, cond, extra=''):
    results.append((name, bool(cond), extra))
    print(('PASS' if cond else 'FAIL'), name, extra, flush=True)


def login(page):
    page.goto(f'{BASE}/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate("() => document.querySelector('form')?.requestSubmit?.()")
    page.wait_for_selector('.sidebar, .tabbar', timeout=25000)
    page.wait_for_timeout(1200)


def open_tool(page, label):
    page.evaluate(
        """(lb) => {
            const b = [...document.querySelectorAll('.sts-rail .sts-tool')]
              .find(x => x.innerText.trim().toLowerCase().startsWith(lb.toLowerCase()))
            b?.click()
        }""", label)
    page.wait_for_timeout(900)


def active_pick(page):
    return page.evaluate("""() => {
        const el = document.querySelector('.sts-panel .stp-pick.active .stp-pick-name')
        return el ? el.innerText.trim() : ''
    }""")


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900}, locale='es-AR')
    ctx.add_init_script(
        "try{localStorage.setItem('davent:tour:done','1');"
        "localStorage.setItem('davent.studio.seen.v1','1')}catch(e){}"
    )
    page = ctx.new_page()
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('requestfailed', lambda r: failed.append(r.url))
    def on_response(r):
        if r.status < 400:
            return
        failed.append(f'{r.status} {r.url}')
        if '/customization/' in r.url:
            try: print('PATCH BODY:', r.request.post_data[:400] if r.request.post_data else '', flush=True)
            except Exception: pass
            try: print('PATCH RESP:', r.text()[:400], flush=True)
            except Exception: pass
    page.on('response', on_response)

    login(page)
    page.goto(f'{BASE}/dashboard/diseno/studio', wait_until='domcontentloaded')
    page.wait_for_selector('.sts', timeout=15000)
    page.wait_for_selector('.sts iframe', timeout=15000)
    # La vista previa puede ser la plantilla Vue (.store-page) o el
    # documento real del diseño (iframe.ds-surface anidado).
    page.frame_locator('.sts iframe').locator('.store-page, iframe.ds-surface').first.wait_for(timeout=30000)
    page.wait_for_timeout(1200)

    tools = page.evaluate("""() => [...document.querySelectorAll('.sts-rail .sts-tool')]
        .map(x => x.innerText.trim().split('\\n')[0])""")
    for label in ('Diseño', 'Estilo', 'Iconos'):
        ok(f'riel: herramienta {label}', label in tools, str(tools))

    # --- Diseño -----------------------------------------------------------
    open_tool(page, 'Diseño')
    picks = page.locator('.sts-panel .stp-pick').count()
    ok('panel Diseño lista diseños', picks >= 9, f'{picks} opciones')
    ok('panel Diseño marca el diseño actual', bool(active_pick(page)), active_pick(page))
    before = active_pick(page)
    # elige el segundo diseño habilitado distinto del actual
    page.evaluate("""() => {
        const rows = [...document.querySelectorAll('.sts-panel .stp-pick')]
        const target = rows.find(r => !r.classList.contains('active') && !r.classList.contains('locked'))
        target?.click()
    }""")
    page.wait_for_timeout(1800)
    after = active_pick(page)
    ok('cambiar de diseño actualiza la elección', after and after != before, f'{before} -> {after}')
    ok('la vista previa sigue montada', page.locator('.sts iframe').count() == 1)
    page.screenshot(path=f'{OUT}/diseno.png')

    # --- Estilo -----------------------------------------------------------
    open_tool(page, 'Estilo')
    styles = page.locator('.sts-panel .stp-pick').count()
    ok('panel Estilo lista estilos', styles >= 10, f'{styles} opciones')
    style_before = active_pick(page)
    page.evaluate("""() => {
        const rows = [...document.querySelectorAll('.sts-panel .stp-pick')]
        const target = rows.find(r => !r.classList.contains('active') && !r.classList.contains('locked'))
        target?.click()
    }""")
    page.wait_for_timeout(1500)
    style_after = active_pick(page)
    ok('elegir un estilo aplica el look', style_after and style_after != style_before, f'{style_before} -> {style_after}')
    ok('el panel Estilo trae modo noche', page.locator('.sts-panel .stp-seg .stp-opt').count() >= 2)
    page.screenshot(path=f'{OUT}/estilo.png')

    # --- Iconos -----------------------------------------------------------
    open_tool(page, 'Iconos')
    sets = page.locator('.sts-panel .stp-pick').count()
    ok('panel Iconos lista sets', sets >= 4, f'{sets} opciones')
    page.evaluate("""() => {
        const rows = [...document.querySelectorAll('.sts-panel .stp-pick')]
        const target = rows.find(r => !r.classList.contains('active'))
        target?.click()
    }""")
    page.wait_for_timeout(900)
    ok('elegir un set de iconos lo marca', bool(active_pick(page)), active_pick(page))
    page.screenshot(path=f'{OUT}/iconos.png')

    # --- Modo noche del lienzo -------------------------------------------
    page.evaluate("""() => {
        const b = [...document.querySelectorAll('.stcv-opt')]
          .find(x => /oscuro|claro/i.test(x.getAttribute('title') || ''))
        b?.click()
    }""")
    page.wait_for_timeout(1200)
    theme = page.evaluate("""() => {
        const outer = document.querySelector('.sts iframe')?.contentDocument
        const inner = outer?.querySelector('iframe.ds-surface')
        const doc = inner?.contentDocument || outer
        return doc?.querySelector('.store-page')?.getAttribute('data-store-theme')
          || doc?.documentElement?.getAttribute('data-ds-theme')
    }""")
    ok('el lienzo cambia a modo noche', theme == 'dark', str(theme))
    page.screenshot(path=f'{OUT}/noche.png')

    # --- Salud general ----------------------------------------------------
    # El botón de Google Identity se rechaza en localhost (origin no
    # autorizado en el proyecto de Firebase): ruido de dev, no del Studio.
    # El aviso genérico "Failed to load resource" no trae URL: la red ya se
    # audita abajo con la URL real de cada respuesta >= 400.
    NOISE = ('favicon', 'GSI_LOGGER', 'accounts.google.com', 'gsi/button', 'Failed to load resource')
    real_errors = [e for e in errors if not any(n in e for n in NOISE)]
    bad = [f for f in failed
           if ('/api/' in f or f.endswith('.js') or f.endswith('.css'))
           and 'accounts.google.com' not in f]
    ok('sin errores de consola', not real_errors, ' | '.join(real_errors[:3]))
    ok('sin 404 de assets/API', not bad, ' | '.join(bad[:3]))
    page.screenshot(path=f'{OUT}/final.png', full_page=False)

    browser.close()

fails = [r for r in results if not r[1]]
print('')
print(f'{len(results) - len(fails)}/{len(results)} chequeos OK')
if fails:
    sys.exit(1)
