"""QA: Studio preview en vivo tras el fix.

1. Login -> abre Studio -> el select #psg-style lista los presets.
2. Elegir un preset cambia data-store-template del iframe SIN recargar.
3. Navegar dentro del preview conserva ?studio=1 y los updates siguen.
4. El mismo ejercicio por http://127.0.0.1:5173 (antes: iframe cross-origin
   -> postMessage mudo -> había que recargar para ver el estilo).
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

PASS = True
def ok(name, cond, extra=''):
    global PASS
    PASS = PASS and bool(cond)
    print(('PASS' if cond else 'FAIL'), name, extra, flush=True)

def login(page, base):
    for attempt in range(2):
        page.goto(f'{base}/login', wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        page.fill('input[name="username"]', 'qablocks2')
        page.fill('input[name="password"]', 'QaBlocks2026!')
        page.evaluate("() => { const f = document.querySelector('form'); f?.requestSubmit?.() }")
        try:
            page.wait_for_selector('.sidebar, .tabbar', timeout=25000)
            page.wait_for_timeout(1200)
            return
        except Exception:
            if attempt: raise
            page.wait_for_timeout(2000)

def open_studio(page):
    page.evaluate("""() => {
      const b=[...document.querySelectorAll('button')].find(x=>/mi p[aá]gina|mi web/i.test(x.innerText)&&x.closest('.sidebar,.tabbar'))
      b?.click() }""")
    page.wait_for_timeout(1500)
    page.evaluate("""() => { [...document.querySelectorAll('button')].find(x=>/c[oó]mo se ve/i.test(x.innerText))?.click() }""")
    page.wait_for_timeout(1500)
    page.evaluate("""() => { [...document.querySelectorAll('.dsg-tab')].find(t=>/Studio/i.test(t.innerText))?.click() }""")
    page.wait_for_selector('.sts', timeout=10000)
    page.wait_for_selector('.sts iframe', timeout=10000)
    page.frame_locator('.sts iframe').locator('.store-page').wait_for(timeout=45000)
    page.wait_for_timeout(1500)

def tpl_in_frame(page):
    return page.evaluate("""() => document.querySelector('.sts iframe')?.contentDocument
        ?.querySelector('.store-page')?.getAttribute('data-store-template')""")

def run(base):
    print(f'\n===== {base} =====')
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='es-AR')
        ctx.add_init_script("try{localStorage.setItem('davent:tour:done','1')}catch(e){}")
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))

        login(page, base)
        open_studio(page)

        src = page.evaluate("() => document.querySelector('.sts iframe')?.src || ''")
        same_origin = page.evaluate("""() => {
          const f = document.querySelector('.sts iframe')
          try { return !!f.contentDocument && !!f.contentDocument.querySelector('.store-page') }
          catch { return false }
        }""")
        ok('iframe same-origin accesible', same_origin, src)

        # select_list en vez de la columna de tarjetas
        has_select = page.is_visible('select#psg-style')
        n_opts = page.locator('select#psg-style option').count()
        ok('select de estilos visible', has_select, f'{n_opts} opciones')
        ok('sin columna de tarjetas', page.locator('.psg-card').count() == 0)

        before = tpl_in_frame(page)
        # Elegir un preset distinto al actual directo en el select
        picked = page.evaluate(f"""() => {{
          const s = document.querySelector('select#psg-style')
          const TPLS = ['minimal','aurora','circuit','bloque','signature','calma','classic','street','riso','terra','promo','mercado','lookbook','cobre','boutique']
          const cur = {json.dumps(before or '')}
          const opt = [...s.options].find(o => o.value && !o.disabled)
          // probar con la 2da opción para asegurar cambio de plantilla
          const cand = [...s.options].filter(o => o.value && !o.disabled)[1] || opt
          s.value = cand.value
          s.dispatchEvent(new Event('change', {{ bubbles: true }}))
          return {{ id: cand.value, label: cand.textContent }}
        }}""")
        page.wait_for_timeout(3000)
        after = tpl_in_frame(page)
        print('  picked:', picked, '| template', before, '->', after)
        ok('estilo aplica en vivo (sin recargar)', bool(after) and after != before)
        ok('cinta "Probando" visible', page.is_visible('.psg-trial'))

        # navegación interna: click en un enlace del preview conserva ?studio=1
        page.evaluate("""() => {
          const d = document.querySelector('.sts iframe')?.contentDocument
          d?.querySelector('.sp-top a[href*="/catalogo"], .store-page a[href*="/catalogo"]')?.click()
        }""")
        page.wait_for_timeout(2500)
        iframe_url = page.evaluate("() => document.querySelector('.sts iframe')?.contentWindow?.location?.href || ''")
        ok('navegación interna conserva ?studio=1', 'studio=1' in iframe_url, iframe_url[:80])

        # y los updates siguen aplicando después de navegar (el click dentro
        # del preview cambia la herramienta activa: volver a Estilos)
        page.evaluate("""() => { [...document.querySelectorAll('.sts-tool')].find(t=>/Estilos/.test(t.innerText))?.click() }""")
        page.wait_for_timeout(600)
        page.evaluate("""() => {
          const s = document.querySelector('select#psg-style')
          if (!s) return
          const cand = [...s.options].filter(o => o.value && !o.disabled)[3]
          if (cand) { s.value = cand.value; s.dispatchEvent(new Event('change', { bubbles: true })) }
        }""")
        page.wait_for_timeout(2500)
        after2 = tpl_in_frame(page)
        ok('updates siguen tras navegar', bool(after2) and after2 != after, f'{after} -> {after2}')

        errs = [e for e in errors if 'favicon' not in e.lower()]
        ok('sin errores JS', not errs, '; '.join(errs[:3]))
        page.screenshot(path='qa_out/studio-select.png')
        b.close()

for base in ['http://localhost:5173', 'http://127.0.0.1:5173']:
    try:
        run(base)
    except Exception as e:
        PASS = False
        print('FAIL run', base, repr(e)[:200])
print('\nRESULT:', 'PASS' if PASS else 'FAIL')
