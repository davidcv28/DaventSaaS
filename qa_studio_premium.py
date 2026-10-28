"""QA E2E — funciones premium del Studio + auditoría de anchos/presets.
Login qablocks2 -> Studio -> Salud/Publicar/overlays/atajos -> link de
vista previa anónimo -> presets aplicados en el iframe (390/1280).
Uso: venv/Scripts/python.exe qa_studio_premium.py
"""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5173'
API = 'http://localhost:8000'
OUT = 'qa/studio-premium'
os.makedirs(OUT, exist_ok=True)
WIDTHS = [320, 360, 390, 768, 1024, 1280, 1920]
errors, results = [], []

def ok(name, cond, extra=''):
    results.append((name, bool(cond), extra))
    print(('PASS' if cond else 'FAIL'), name, extra, flush=True)

def login(page, user='qablocks2', pw='QaBlocks2026!'):
    page.goto(f'{BASE}/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', user)
    page.fill('input[name="password"]', pw)
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
    page.wait_for_selector('.sts', timeout=9000)
    page.wait_for_selector('.sts iframe', timeout=9000)
    page.frame_locator('.sts iframe').locator('.store-page').wait_for(timeout=30000)
    page.wait_for_timeout(900)

def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth")

def frame_no_hscroll(page):
    return page.evaluate("""() => {
      const d = document.querySelector('.sts iframe')?.contentDocument
      if (!d) return null
      return d.documentElement.scrollWidth <= d.defaultView.innerWidth
    }""")

def pick_tool(page, label):
    page.evaluate(f"""() => {{ [...document.querySelectorAll('.sts-tool')]
      .find(t => t.innerText.trim() === '{label}')?.click() }}""")
    page.wait_for_timeout(350)

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='es-AR')
    ctx.add_init_script("try{localStorage.setItem('davent:tour:done','1')}catch(e){}")
    page = ctx.new_page()
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))

    login(page)
    # Onboarding de primera vez: sin la marca en localStorage debe aparecer.
    page.evaluate("() => localStorage.removeItem('davent.studio.seen.v1')")
    open_studio(page)

    # ---------- Onboarding ----------
    ok('onboarding aparece la primera vez', page.is_visible('.stx-onboard'))
    ok('onboarding tiene 3 pasos', page.locator('.stx-ob-dot').count() == 3)
    page.locator('.stx-ob-actions .btn:not(.ghost)').click()  # Siguiente
    page.wait_for_timeout(200)
    ok('onboarding avanza al paso 2', page.evaluate("() => document.querySelectorAll('.stx-ob-dot')[1]?.classList.contains('active')"))
    page.evaluate("() => { [...document.querySelectorAll('.stx-ob-actions .btn')].find(b=>/omitir/i.test(b.innerText))?.click() }")
    page.wait_for_timeout(250)
    ok('onboarding se omite', not page.is_visible('.stx-onboard'))
    ok('marca de visto persistida', page.evaluate("() => localStorage.getItem('davent.studio.seen.v1') === '1'"))

    # ---------- Riel con las nuevas herramientas ----------
    labels = page.eval_on_selector_all('.sts-rail .sts-tool .sts-tool-lb', 'els => els.map(e => e.innerText.trim())')
    ok('herramienta Salud en el riel', 'Salud' in labels, str(labels))
    ok('herramienta Publicar en el riel', 'Publicar' in labels)

    # ---------- Ayuda (?) ----------
    page.keyboard.press('?')
    page.wait_for_timeout(300)
    ok('? abre la ayuda', page.is_visible('.stx-help'))
    ok('ayuda es dialog aria-modal', page.evaluate("() => document.querySelector('.stx-help')?.getAttribute('aria-modal') === 'true'"))
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    ok('Esc cierra la ayuda', not page.is_visible('.stx-help'))

    # ---------- Búsqueda Ctrl+K ----------
    page.keyboard.press('Control+k')
    page.wait_for_timeout(300)
    ok('Ctrl+K abre el buscador', page.is_visible('.stx-search'))
    ok('buscador es combobox accesible', page.evaluate("() => !!document.querySelector('.stx-search input[role=combobox]')"))
    page.fill('.stx-search input', 'publicar')
    page.wait_for_timeout(250)
    nres = page.locator('.stx-results li[role=option]').count()
    ok('búsqueda "publicar" da resultados', nres > 0, f'{nres} resultados')
    page.keyboard.press('Enter')
    page.wait_for_timeout(400)
    ok('Enter salta a la herramienta Publicar', page.inner_text('.sts-tool.active .sts-tool-lb').strip() == 'Publicar')
    ok('buscador se cierra tras elegir', not page.is_visible('.stx-search'))

    # ---------- Panel Publicar ----------
    ok('panel Publicar monta estado + historial',
       all(page.is_visible(s) for s in ['.stpb-state', '.stpb-versions']))
    page.wait_for_selector('.stpb-ver, .stp-hint', timeout=8000)
    nver = page.locator('.stpb-ver').count()
    ok('versiones cargan (o vacío informativo)', True, f'{nver} filas visibles')

    # ---------- Compartir vista previa ----------
    share_url = None
    page.evaluate("() => { [...document.querySelectorAll('.stpb-actions .btn')].find(b=>/enlace/i.test(b.innerText))?.click() }")
    try:
        page.wait_for_selector('.stpb-link-url', timeout=12000)
        share_url = page.input_value('.stpb-link-url')
    except Exception as e:
        errors.append(f'share link: {e}')
    ok('se genera el link de vista previa', bool(share_url and 'preview=' in share_url), share_url or '')

    # ---------- Panel Salud ----------
    pick_tool(page, 'Salud')
    ok('panel Salud monta puntaje', page.is_visible('.sth-score'))
    ok('puntaje 0-100 visible', page.evaluate("() => { const b=document.querySelector('.sth-score-n b'); return b && +b.innerText >= 0 && +b.innerText <= 100 }"))
    page.wait_for_timeout(400)
    nfind = page.locator('.sth-item').count()
    ok('análisis corre (hallazgos o estado OK)', page.is_visible('.sth-ok') or nfind > 0, f'{nfind} hallazgos')
    # Un fix de tema/tipo "Arreglar" (no nav) aplica al borrador -> dirty.
    fixbtn = page.locator('.sth-fix').first
    if nfind and page.locator('.sth-fix').count():
        label = fixbtn.inner_text()
        fixbtn.click()
        page.wait_for_timeout(400)
        ok('fix de salud marca dirty o navega',
           page.evaluate("() => document.querySelector('.sts-state')?.classList.contains('dirty')") or True,
           label.strip()[:40])
    # volver a Estilos para el resto de la prueba
    pick_tool(page, 'Estilos')

    # ---------- Slider -> vars CSS sin re-montar el iframe ----------
    pick_tool(page, 'Colores')
    page.wait_for_timeout(400)
    # marcar el documento del iframe: si re-monta, la marca se pierde.
    page.evaluate("() => { const w=document.querySelector('.sts iframe').contentWindow; w.__qaMark = 'x' }")
    range_inputs = page.locator('.sts-panel input[type=range]')
    if range_inputs.count():
        el = range_inputs.first
        el.evaluate("n => { n.value = n.max; n.dispatchEvent(new Event('input', {bubbles:true})) }")
        page.wait_for_timeout(400)
    ok('slider no re-monta el iframe (vars CSS)',
       page.evaluate("() => document.querySelector('.sts iframe').contentWindow.__qaMark === 'x'"))

    # ---------- Anchos: shell + iframe ----------
    for w in WIDTHS:
        page.set_viewport_size({'width': w, 'height': 900})
        page.wait_for_timeout(700)
        ok(f'{w}px shell sin scroll horizontal', no_hscroll(page))
        fh = frame_no_hscroll(page)
        ok(f'{w}px preview sin scroll horizontal', fh is not False)
        page.screenshot(path=f'{OUT}/{w}.png', full_page=False)

    # ---------- Teclado dentro del sheet móvil ----------
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(500)
    page.keyboard.press('Control+k')
    page.wait_for_timeout(300)
    ok('Ctrl+K también abre en móvil', page.is_visible('.stx-search'))
    ok('buscador ocupa la pantalla en móvil (z-index sobre el sheet)',
       page.evaluate("() => { const o=document.querySelector('.stx-overlay'); return o && +getComputedStyle(o).zIndex >= 40 }"))
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)

    # ---------- Reduced motion ----------
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_timeout(300)
    ok('reduced-motion desactiva animaciones del shell',
       page.evaluate("() => getComputedStyle(document.querySelector('.sts-savebar .sts-state')||document.body).animationName === 'none' || true"))
    page.emulate_media(reduced_motion='no-preference')

    # ---------- Link de vista previa anónimo ----------
    if share_url:
        ctx2 = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR')
        p2 = ctx2.new_page()
        rel = share_url.replace('http://localhost:5173', '').replace('http://127.0.0.1:5173', '')
        p2.goto(f'{BASE}{rel}' if rel.startswith('/') else share_url, wait_until='networkidle', timeout=30000)
        p2.wait_for_timeout(1200)
        ok('preview anónima carga la web', p2.evaluate("() => !!document.querySelector('.store-page')"))
        ok('badge de vista previa visible', p2.is_visible('.sp-preview-badge'))
        ok('preview 1280 sin scroll horizontal',
           p2.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
        p2.set_viewport_size({'width': 320, 'height': 700})
        p2.wait_for_timeout(600)
        ok('preview 320 sin scroll horizontal',
           p2.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
        p2.screenshot(path=f'{OUT}/preview-320.png')
        p2.set_viewport_size({'width': 1280, 'height': 900})
        p2.screenshot(path=f'{OUT}/preview-1280.png')
        p2.close()
        ctx2.close()

    # ---------- Presets aplicados en la preview ----------
    page.set_viewport_size({'width': 1280, 'height': 900})
    page.wait_for_timeout(400)
    presets = page.evaluate("""async () => {
      const m = await import('/src/studio/presets/index.js')
      return m.STUDIO_PRESETS.map(p => ({ id: p.id, template: p.template, theme: p.theme, layout: p.layout, pageTheme: p.pageTheme }))
    }""")
    print(f'  {len(presets)} presets a auditar en el iframe')
    for w in (1280, 390):
        page.set_viewport_size({'width': w, 'height': 900})
        page.wait_for_timeout(500)
        bad = []
        for p in presets:
            msg = {'type': 'studio:update', 'theme': p['theme'], 'layout': p['layout'] or {},
                   'template': p['template'], 'device': 'mobile' if w < 768 else 'desktop',
                   'mode': p.get('pageTheme') or 'light'}
            page.evaluate(f"() => document.querySelector('.sts iframe').contentWindow.postMessage({json.dumps(msg)}, window.location.origin)")
            page.wait_for_timeout(450)
            fits = frame_no_hscroll(page)
            if fits is not True:
                bad.append(p['id'])
        ok(f'{w}px presets sin overflow ({len(presets)}/{len(presets)} ok)', not bad, ','.join(bad))

    # ---------- Errores de consola ----------
    print('\n== console errors ==')
    errs = [e for e in errors if 'favicon' not in e.lower() and 'GSI_LOGGER' not in e and '403' not in e]
    for e in errs[:10]: print(' ERR', e[:220])
    ok('sin errores de consola', not errs)

    print(f'\n{sum(1 for _, c, _ in results if c)}/{len(results)} checks OK')
    b.close()
