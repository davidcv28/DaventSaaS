"""Probe FASE 4: el preview recibe postMessage y reordena sin recargar."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

reqs, loads = [], []
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    page = b.new_context(viewport={'width': 1440, 'height': 1000}, locale='es-AR').new_page()
    page.on('request', lambda r: reqs.append(r.url) if '/api/stores/public' in r.url else None)
    page.goto('http://localhost:5173/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('''() => { const f = document.querySelector('form'); f?.requestSubmit?.() }''')
    page.wait_for_timeout(4500)
    page.evaluate('''() => { localStorage.setItem("davent:tour:done","1");
      document.querySelectorAll('[class*="tour"]').forEach(e => e.remove()) }''')
    page.wait_for_selector('.sidebar, .tabbar', timeout=20000)
    page.evaluate('''() => {
      const b=[...document.querySelectorAll('button')].find(x=>/mi p[aá]gina|mi web/i.test(x.innerText)&&x.closest('.sidebar,.tabbar'))
      b?.click() }''')
    page.wait_for_timeout(1200)
    page.click('button:has-text("Bloques")')
    page.wait_for_selector('.blk-frame[data-state="ready"]', timeout=20000)
    page.wait_for_timeout(1000)

    reqs.clear()
    def order():
        return page.evaluate('''() => [...document.querySelector('.blk-frame iframe')
          .contentDocument.querySelectorAll('[data-blk]')].map(e => e.dataset.blk).slice(0, 5)''')
    print('orden preview inicial:', order())

    # Reordenar con Alt+Down sobre el 2do bloque → el preview debe
    # reflejarlo por postMessage, sin load ni requests de tienda.
    page.locator('.blk-list:not(.avail) .blk-grip').nth(1).click()
    page.keyboard.press('Alt+ArrowDown')
    page.wait_for_timeout(1400)
    print('orden preview tras Alt+Down:', order())
    print('requests /public tras el edit:', len(reqs), reqs[:3])
    print('editor order:', page.evaluate('''() => [...document.querySelectorAll(
      '.blk-list:not(.avail) [data-bid]')].map(r=>r.dataset.bid).slice(0,5)'''))
    page.screenshot(path='qa_out/probe-f4.png')
    b.close()
