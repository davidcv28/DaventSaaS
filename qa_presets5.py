"""QA probe: estado del preview en el tiempo + respuesta del GET customization."""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR')
    page = ctx.new_page()
    cust = []
    def on_resp(r):
        if '/api/stores/customization' in r.url and r.status == 200:
            try:
                d = r.json()
                cust.append({'template': d.get('template'),
                             'site_theme': bool(d.get('site_theme')),
                             'layout': list((d.get('layout_config') or {}).keys())})
            except Exception as e:
                cust.append({'err': str(e)[:80]})
    page.on('response', on_resp)

    page.goto('http://localhost:5173/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('() => { document.querySelector("form")?.requestSubmit?.() }')
    page.wait_for_timeout(4500)
    page.evaluate('''() => { localStorage.setItem("davent:tour:done","1");
      document.querySelectorAll('[class*="tour"]').forEach(e => e.remove()) }''')
    page.wait_for_selector('.sidebar, .tabbar', timeout=20000)
    print('GETs de customization (login):', json.dumps(cust))
    cust.clear()

    page.evaluate('''() => {
      const b=[...document.querySelectorAll('.sidebar button,.sidebar a,.tabbar button,.tabbar a')]
        .find(x=>/mi p[aá]gina|mi web/i.test(x.innerText))
      b?.click() }''')
    page.wait_for_timeout(1000)
    page.locator('.sec-tab', has_text='Cómo se ve').first.click()
    page.wait_for_timeout(800)
    page.locator('.dsg-tab', has_text='Studio').first.click()
    page.wait_for_selector('.sts', timeout=20000)
    print('GETs de customization (al montar studio):', json.dumps(cust))

    def st():
        return page.evaluate('''() => {
          const f = document.querySelector('.sts-canvas iframe')
          if (!f || !f.contentDocument) return 'no-frame'
          const p = f.contentDocument.querySelector('.store-page')
          return p ? (p.getAttribute('data-store-template') + '/' +
                      (p.getAttribute('data-store-theme')||'')) : 'no-page'
        }''')
    for t in (0, 2000, 4000, 6000):
        if t: page.wait_for_timeout(t)
        print(f't={t}: preview={st()} dirty={page.locator(".sts-state.dirty").count()}')

    b.close()
