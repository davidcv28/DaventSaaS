"""QA E2E del StudioShell (dashboard > Mi página > Diseño > Studio).
Login qablocks2 -> abre el Studio -> ejercita preview en vivo, historial,
dispositivos, hoja móvil y los 7 anchos. Guarda shots en qa/studio-shell/.
OJO: la app tiene que abrirse en localhost (env.appUrl = localhost) para que
el iframe de la preview sea same-origin.
Uso: venv/Scripts/python.exe qa_studio_shell.py
"""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5173'
OUT = 'qa/studio-shell'
os.makedirs(OUT, exist_ok=True)
WIDTHS = [320, 360, 390, 768, 1024, 1280, 1920]
errors, results = [], []

def ok(name, cond, extra=''):
    results.append((name, bool(cond), extra))
    print(('PASS' if cond else 'FAIL'), name, extra, flush=True)

def login(page):
    page.goto(f'{BASE}/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate("() => { const f = document.querySelector('form'); f?.requestSubmit?.() }")
    page.wait_for_selector('.sidebar, .tabbar', timeout=25000)
    page.wait_for_timeout(1200)

def open_studio(page):
    page.evaluate("""() => {
      const b=[...document.querySelectorAll('button')].find(x=>/mi p[aá]gina|mi web/i.test(x.innerText)&&x.closest('.sidebar,.tabbar'))
      b?.click() }""")
    page.wait_for_timeout(1500)
    page.evaluate("""() => { [...document.querySelectorAll('button')].find(x=>/c[oó]mo se ve/i.test(x.innerText))?.click() }""")
    page.wait_for_timeout(1500)
    page.evaluate("""() => { [...document.querySelectorAll('.dsg-tab')].find(t=>/Studio/i.test(t.innerText))?.click() }""")
    page.wait_for_selector('.sts', timeout=8000)
    page.wait_for_selector('.sts iframe', timeout=8000)
    # el store-page dentro del iframe (SPA fría en dev tarda unos segundos)
    page.frame_locator('.sts iframe').locator('.store-page').wait_for(timeout=30000)
    page.wait_for_timeout(800)  # studio:ready + bridge

def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth")

def accent(page):
    return page.evaluate("""() => document.querySelector('.sts iframe')?.contentDocument
        ?.querySelector('.store-page')?.style.getPropertyValue('--store-accent')""")

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='es-AR')
    ctx.add_init_script("try{localStorage.setItem('davent:tour:done','1')}catch(e){}")
    page = ctx.new_page()
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))

    login(page)
    open_studio(page)
    ok('shell monta (riel+panel+lienzo+savebar)',
       all(page.is_visible(s) for s in ['.sts-rail', '.sts-panel', '.sts-canvas', '.sts-savebar']))
    ok('8 herramientas en el riel', page.locator('.sts-rail .sts-tool:not(.sts-collapse)').count() >= 8)
    ok('iframe ?studio=1 cargó', page.evaluate("() => document.querySelector('.sts iframe')?.src.includes('studio=1')"))
    ok('iframe same-origin accesible',
       page.evaluate("() => !!document.querySelector('.sts iframe')?.contentDocument?.querySelector('.store-page')"))
    ok('página pública dentro del iframe',
       page.evaluate("() => !!document.querySelector('.sts iframe')?.contentDocument?.querySelector('.store-page .sp-btn, .store-page h1')"))

    # --- preview en vivo: cambiar el acento desde Colores -> var en iframe ---
    page.evaluate("() => { [...document.querySelectorAll('.sts-tool')].find(t=>/Colores/.test(t.innerText))?.click() }")
    page.wait_for_timeout(300)
    page.evaluate("""() => {
      const c = document.querySelector('.sts-panel input[aria-label^="Acento"]')
      if (c) { c.value = '#dd1144'; c.dispatchEvent(new Event('input', { bubbles: true })) } }""")
    page.wait_for_timeout(300)  # debounce 60ms + render
    a1 = accent(page)
    ok('accent -> --store-accent en vivo', a1 == '#dd1144', f'accent={a1}')
    ok('savebar marca cambios',
       page.evaluate("() => document.querySelector('.sts-state')?.classList.contains('dirty')"))

    # --- undo/redo ---
    page.keyboard.press('Control+z')
    page.wait_for_timeout(300)
    a2 = accent(page)
    ok('Ctrl+Z revierte el acento', a2 != '#dd1144', f'accent={a2}')
    page.keyboard.press('Control+Shift+z')
    page.wait_for_timeout(300)
    a3 = accent(page)
    ok('Ctrl+Shift+Z rehace', a3 == '#dd1144', f'accent={a3}')

    # --- click en un bloque de la preview -> herramienta Distribución ---
    tool0 = page.inner_text('.sts-tool.active .sts-tool-lb').strip()
    page.evaluate("""() => {
      const d = document.querySelector('.sts iframe')?.contentDocument
      d?.querySelector('[data-blk]')?.dispatchEvent(new MouseEvent('click', { bubbles: true })) }""")
    page.wait_for_timeout(500)
    tool1 = page.inner_text('.sts-tool.active .sts-tool-lb').strip()
    ok('pick en preview enfoca su herramienta', tool1 == 'Distribución' and tool1 != tool0, f'{tool0}->{tool1}')

    # --- dispositivos: marco móvil + rotación ---
    page.evaluate("() => { [...document.querySelectorAll('.stcv-opt')].find(t=>t.title==='Móvil')?.click() }")
    page.wait_for_timeout(300)
    fw = page.evaluate("() => parseInt(document.querySelector('.stcv-frame')?.style.width)")
    ok('marco móvil 390px', fw == 390, f'w={fw}')
    page.evaluate("() => { [...document.querySelectorAll('.stcv-opt')].find(t=>t.title==='Rotar')?.click() }")
    page.wait_for_timeout(300)
    fw = page.evaluate("() => parseInt(document.querySelector('.stcv-frame')?.style.width)")
    ok('rotación aplica (844px)', fw == 844, f'w={fw}')
    page.evaluate("() => { [...document.querySelectorAll('.stcv-opt')].find(t=>t.title==='Rotar')?.click() }")
    page.evaluate("() => { [...document.querySelectorAll('.stcv-opt')].find(t=>t.title==='Escritorio')?.click() }")
    page.wait_for_timeout(300)

    # --- fullscreen + Esc ---
    page.evaluate("() => { [...document.querySelectorAll('.stcv-opt')].find(t=>/pantalla completa/i.test(t.title))?.click() }")
    page.wait_for_timeout(300)
    ok('fullscreen entra', page.evaluate("() => document.querySelector('.sts')?.classList.contains('is-full')"))
    page.keyboard.press('Escape')
    page.wait_for_timeout(300)
    ok('Esc sale de fullscreen', page.evaluate("() => !document.querySelector('.sts')?.classList.contains('is-full')"))
    page.screenshot(path=f'{OUT}/desktop-1440.png', full_page=False)

    # --- comparar (press-hold) ---
    page.locator('.sts-cmp').dispatch_event('pointerdown')
    page.wait_for_timeout(300)
    ok('comparar muestra chip "versión guardada"',
       page.is_visible('.stcv-compare'))
    a4 = accent(page)
    ok('comparar muestra tema guardado', a4 != '#dd1144', f'accent={a4}')
    page.locator('.sts-cmp').dispatch_event('pointerup')
    page.wait_for_timeout(300)

    # --- QA por anchos ---
    for w in WIDTHS:
        page.set_viewport_size({'width': w, 'height': 900})
        page.wait_for_timeout(700)
        ok(f'{w}px sin scroll horizontal', no_hscroll(page))
        if w <= 768:
            ok(f'{w}px studio a pantalla completa', page.evaluate("() => getComputedStyle(document.querySelector('.sts')).position === 'fixed'"))
            ok(f'{w}px riel fijo abajo', page.evaluate("() => { const r=document.querySelector('.sts-rail'); const b=r.getBoundingClientRect(); return getComputedStyle(r).position==='absolute' && Math.abs(b.bottom - window.innerHeight) < 4 }"))
            ok(f'{w}px hoja móvil visible', page.evaluate("() => { const r=document.querySelector('.sts-panel').getBoundingClientRect(); return r.height > 40 && r.bottom <= window.innerHeight + 2 && r.top < window.innerHeight }"))
            ok(f'{w}px botón Volver', page.evaluate("() => getComputedStyle(document.querySelector('.sts-back')).display !== 'none'"))
        page.screenshot(path=f'{OUT}/{w}.png', full_page=False)

    # --- salir del Studio vuelve a la sección Diseño ---
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(500)
    page.evaluate("() => { document.querySelector('.sts-back')?.click() }")
    page.wait_for_timeout(500)
    ok('Volver sale del Studio (móvil)', page.evaluate("() => !document.querySelector('.sts')"))

    print('\n== console errors ==')
    errs = [e for e in errors if 'favicon' not in e.lower() and 'GSI_LOGGER' not in e and '403' not in e]
    for e in errs[:10]: print(' ERR', e[:200])
    ok('sin errores de consola', not errs)
    print(f'\n{sum(1 for _,c,_ in results if c)}/{len(results)} checks OK')
    b.close()
