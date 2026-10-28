"""QA FASE presets #4: persistencia de favoritos tras reload + Descartar."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR')
    page = ctx.new_page()
    page.on('pageerror', lambda e: print('  [PAGEERROR]', str(e)[:300]))

    def login():
        page.goto('http://localhost:5173/login', wait_until='domcontentloaded')
        page.wait_for_timeout(800)
        if page.locator('input[name="username"]').count():
            page.fill('input[name="username"]', 'qablocks2')
            page.fill('input[name="password"]', 'QaBlocks2026!')
            page.evaluate('() => { document.querySelector("form")?.requestSubmit?.() }')
            page.wait_for_timeout(4500)
        page.evaluate('''() => { localStorage.setItem("davent:tour:done","1");
          document.querySelectorAll('[class*="tour"]').forEach(e => e.remove()) }''')
        page.wait_for_selector('.sidebar, .tabbar', timeout=20000)

    def to_studio():
        page.evaluate('''() => {
          const b=[...document.querySelectorAll('.sidebar button,.sidebar a,.tabbar button,.tabbar a')]
            .find(x=>/mi p[aá]gina|mi web/i.test(x.innerText))
          b?.click() }''')
        page.wait_for_timeout(1000)
        page.locator('.sec-tab', has_text='Cómo se ve').first.click()
        page.wait_for_timeout(1000)
        page.locator('.dsg-tab', has_text='Studio').first.click()
        page.wait_for_selector('.sts', timeout=20000)
        page.wait_for_timeout(3000)

    def preview_state():
        return page.evaluate('''() => {
          const f = document.querySelector('.sts-canvas iframe')
          if (!f || !f.contentDocument) return 'no-frame'
          const p = f.contentDocument.querySelector('.store-page')
          return p ? (p.getAttribute('data-store-template') + '/' +
                      (p.getAttribute('data-store-theme')||'')) : 'no-page'
        }''')

    login()
    to_studio()

    # Favorito en dos cards
    favs = page.locator('.psg-fav')
    favs.nth(0).click(); page.wait_for_timeout(250)
    favs = page.locator('.psg-fav')
    favs.nth(2).click(); page.wait_for_timeout(400)
    print('fav keys en localStorage:', page.evaluate(
        '''() => Object.keys(localStorage).filter(k=>/fav|preset/i.test(k))
             .map(k=>k+'='+localStorage.getItem(k))'''))
    # filtro Favoritos muestra 2
    page.locator('.psg-toggles .stp-opt', has_text='Favoritos').first.click()
    page.wait_for_timeout(400)
    print('cards filtro Favoritos:', page.locator('.psg-card').count())

    # reload -> persisten?
    page.reload(wait_until='domcontentloaded')
    page.wait_for_timeout(3000)
    page.evaluate('''() => { localStorage.setItem("davent:tour:done","1");
      document.querySelectorAll('[class*="tour"]').forEach(e => e.remove()) }''')
    page.wait_for_selector('.sidebar, .tabbar', timeout=20000)
    to_studio()
    page.locator('.psg-toggles .stp-opt', has_text='Favoritos').first.click()
    page.wait_for_timeout(400)
    print('cards Favoritos tras reload:', page.locator('.psg-card').count())
    page.locator('.psg-toggles .stp-opt', has_text='Favoritos').first.click()  # salir del filtro

    # Descartar: probar un preset -> Descartar -> baseline
    page.wait_for_timeout(3000)  # dejar asentar el SWR antes de medir baseline
    before = preview_state()
    print('baseline:', before, '| dirty:', page.locator('.sts-state.dirty').count())
    page.evaluate('''() => {
      const card=[...document.querySelectorAll('.psg-card')]
        .find(c=>c.querySelector('h4')?.textContent.includes('Vidrio'))
      card?.querySelector('.psg-btn.is-try')?.click() }''')
    page.wait_for_timeout(1800)
    print('tras Probar Vidrio:', preview_state(), '| dirty:',
          page.locator('.sts-state.dirty').count())
    page.locator('.sts button', has_text='Descartar').first.click()
    page.wait_for_timeout(1800)
    print('tras Descartar:', preview_state(), '| dirty:',
          page.locator('.sts-state.dirty').count())

    b.close()
