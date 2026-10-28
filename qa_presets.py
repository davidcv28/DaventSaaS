"""QA FASE presets: galeria en el Studio + Probar/Aplicar en vivo."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    page = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR').new_page()
    page.on('console', lambda m: print('  [con]', m.type, m.text[:160]) if m.type in ('error', 'warning') else None)
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

    # Mi página -> "Cómo se ve" -> tab "Studio"
    page.evaluate('''() => {
      const b=[...document.querySelectorAll('button,a')].find(x=>/mi p[aá]gina/i.test(x.innerText)&&x.closest('.sidebar,.tabbar,nav'))
      b?.click() }''')
    page.wait_for_timeout(1200)
    page.evaluate('''() => {
      const b=[...document.querySelectorAll('button,a')].find(x=>/c[oó]mo se ve/i.test(x.innerText))
      b?.click() }''')
    page.wait_for_timeout(1500)
    page.click('button:has-text("Studio")')
    page.wait_for_selector('.sts', timeout=20000)
    page.wait_for_timeout(3500)

    # Galeria presente?
    n_cards = page.locator('.psg-card').count()
    print('preset cards:', n_cards)
    print('psg visible:', page.locator('.psg').is_visible())
    print('thumbs:', page.locator('.psth').count())

    # Estado del iframe preview antes
    def preview_state():
        return page.evaluate('''() => {
          const f = document.querySelector('.sts-canvas iframe')
          if (!f || !f.contentDocument) return 'no-frame'
          const p = f.contentDocument.querySelector('.store-page')
          return p ? p.getAttribute('data-store-template') + '/' + (p.getAttribute('data-store-theme')||'') : 'no-page'
        }''')
    print('preview antes:', preview_state())

    # Probar el preset "Vidrio nocturno" (aurora, dark, locked o no segun plan)
    page.evaluate('''() => {
      const card = [...document.querySelectorAll('.psg-card')]
        .find(c => c.querySelector('h4')?.textContent.includes('Vidrio'))
      card?.querySelector('.psg-btn.is-try')?.click()
    }''')
    page.wait_for_timeout(1500)
    print('preview tras Probar Vidrio:', preview_state())
    print('trial chip:', page.locator('.psg-trial').is_visible())
    print('savebar dirty:', page.locator('.sts-state.dirty').count())

    # Deshacer
    page.locator('.psg-mini').first.click()
    page.wait_for_timeout(1200)
    print('preview tras Deshacer:', preview_state())

    # Combinar: solo la paleta de otro preset
    page.evaluate('''() => {
      const card = [...document.querySelectorAll('.psg-card')]
        .find(c => c.querySelector('h4')?.textContent.includes('Papel riso'))
      card?.querySelector('.psg-btn.is-comb')?.click()
    }''')
    page.wait_for_timeout(300)
    page.evaluate('''() => {
      [...document.querySelectorAll('.psg-comb button')]
        .find(b => b.textContent.includes('paleta'))?.click()
    }''')
    page.wait_for_timeout(1200)
    print('preview tras Combinar paleta riso:', preview_state())

    # Filtros
    page.select_option('.psg-filters select >> nth=2', 'base')
    page.wait_for_timeout(400)
    print('cards con tier=base:', page.locator('.psg-card').count())
    page.select_option('.psg-filters select >> nth=2', '')
    page.fill('.psg-search input', 'riso')
    page.wait_for_timeout(400)
    print('cards buscando riso:', page.locator('.psg-card').count())

    # Favoritos
    page.fill('.psg-search input', '')
    page.locator('.psg-fav').first.click()
    page.locator('.psg-toggles .stp-opt >> nth=1').click()
    page.wait_for_timeout(300)
    print('cards en favoritos:', page.locator('.psg-card').count())
    page.locator('.psg-toggles .stp-opt >> nth=1').click()

    page.screenshot(path='qa_out/presets-1280.png', full_page=False)
    # scroll horizontal check
    print('scrollWidth<=innerWidth:', page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth'))
    b.close()
