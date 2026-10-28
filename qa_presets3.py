"""QA FASE presets #3: anchos 320/360/390/768/1024/1280/1920 + locked try +
combinar por partes + undo/redo completo."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

WIDTHS = [1280, 1920, 1024, 768, 390, 360, 320]

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR')
    page = ctx.new_page()
    page.on('pageerror', lambda e: print('  [PAGEERROR]', str(e)[:300]))

    page.goto('http://localhost:5173/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('() => { const f = document.querySelector("form"); f?.requestSubmit?.() }')
    page.wait_for_timeout(4500)
    page.evaluate('''() => { localStorage.setItem("davent:tour:done","1");
      document.querySelectorAll('[class*="tour"]').forEach(e => e.remove()) }''')
    page.wait_for_selector('.sidebar, .tabbar', timeout=20000)

    # Navegar una sola vez: sidebar "Mi página" -> sec-tab "Cómo se ve" -> dsg-tab "Studio"
    page.evaluate('''() => {
      const b=[...document.querySelectorAll('.sidebar button,.sidebar a,.tabbar button,.tabbar a')]
        .find(x=>/mi p[aá]gina|mi web/i.test(x.innerText))
      b?.click() }''')
    page.wait_for_timeout(1200)
    page.locator('.sec-tab', has_text='Cómo se ve').first.click()
    page.wait_for_timeout(1200)
    page.locator('.dsg-tab', has_text='Studio').first.click()
    page.wait_for_selector('.sts', timeout=20000)
    page.wait_for_timeout(3500)
    print('sts montado, cards:', page.locator('.psg-card').count())

    def preview_state():
        return page.evaluate('''() => {
          const f = document.querySelector('.sts-canvas iframe')
          if (!f || !f.contentDocument) return 'no-frame'
          const p = f.contentDocument.querySelector('.store-page')
          return p ? (p.getAttribute('data-store-template') + '/' +
                      (p.getAttribute('data-store-theme')||'')) : 'no-page'
        }''')

    # --- 1. Probar preset BLOQUEADO (bento -> template plus, plan sin has_design_plus)
    page.evaluate('''() => {
      const card=[...document.querySelectorAll('.psg-card')]
        .find(c=>c.querySelector('h4')?.textContent.includes('Bento'))
      card?.querySelector('.psg-btn.is-try')?.click() }''')
    page.wait_for_timeout(1800)
    st = preview_state()
    print('locked Probar Bento -> preview:', st)
    print('  trial chip:', page.locator('.psg-trial').is_visible(),
          '| dirty:', page.locator('.sts-state.dirty').count(),
          '| Aplicar presente en card Bento:',
          page.evaluate('''() => {
            const c=[...document.querySelectorAll('.psg-card')]
              .find(x=>x.querySelector('h4')?.textContent.includes('Bento'))
            return c ? !!c.querySelector('.psg-btn.is-apply') : '?' }'''),
          '| Ver planes en card Bento:',
          page.evaluate('''() => {
            const c=[...document.querySelectorAll('.psg-card')]
              .find(x=>x.querySelector('h4')?.textContent.includes('Bento'))
            return c ? !!([...c.querySelectorAll('button,a')]
              .find(x=>/ver planes/i.test(x.innerText))) : '?' }'''))

    # undo -> restaura tema+template+viewer
    page.locator('.psg-mini').first.click()
    page.wait_for_timeout(1500)
    print('  tras Deshacer:', preview_state())

    # --- 2. Combinar por partes (preset no bloqueado, p.ej. 'Neón tech' es plus?
    # usar uno advanced permitido: 'Papel riso' = riso base). Partes:
    for parte, preset in [('tipografía', 'Editorial mínima'), ('distribución', 'Papel riso')]:
        page.evaluate(f'''() => {{
          const card=[...document.querySelectorAll('.psg-card')]
            .find(c=>c.querySelector('h4')?.textContent.includes('{preset}'))
          card?.querySelector('.psg-btn.is-comb')?.click() }}''')
        page.wait_for_timeout(400)
        page.evaluate(f'''() => {{
          [...document.querySelectorAll('.psg-comb button')]
            .find(b=>b.textContent.toLowerCase().includes('{parte}'))?.click() }}''')
        page.wait_for_timeout(1500)
        print(f'combinar {parte} ({preset}) -> preview:', preview_state(),
              '| dirty:', page.locator('.sts-state.dirty').count())
        page.locator('button[aria-label="Deshacer"]').first.click()  # undo del shell
        page.wait_for_timeout(1200)
        print(f'  tras Deshacer {parte}:', preview_state())

    # --- 3. Matriz de anchos
    for w in WIDTHS:
        page.set_viewport_size({'width': w, 'height': 900})
        page.wait_for_timeout(900)
        if w <= 768:
            # el panel es bottom-sheet: llevarlo a media posicion
            stops = page.locator('.sts-stop')
            if stops.count() > 1:
                stops.nth(1).click()
                page.wait_for_timeout(700)
        ok = page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth')
        vis = page.locator('.psg').is_visible()
        cards = page.locator('.psg-card').count()
        clip = {'x': 0, 'y': 0, 'width': w, 'height': 900}
        page.screenshot(path=f'qa_out/presets-{w}.png', clip=clip)
        print(f'{w}px: scroll_ok={ok} psg_visible={vis} cards={cards}')

    b.close()
