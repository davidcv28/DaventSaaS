"""Verifica el scroll-sync: scrollIntoView sobre el hijo real del
marcador data-blk en la pagina publica (sin login)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
BASE = 'http://localhost:5173'
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    page = b.new_page(viewport={'width': 1440, 'height': 900})
    fails = []
    page.on('response', lambda r: fails.append(f'{r.status} {r.url[:120]}') if r.status >= 400 else None)
    page.goto(f'{BASE}/qatienda2', wait_until='domcontentloaded')
    page.wait_for_timeout(4500)
    print('blks:', page.evaluate('document.querySelectorAll("[data-blk]").length'))
    print('body[:300]:', page.evaluate('document.body.innerText.slice(0,300)'))
    print('fails:', fails[:10])
    print('scrollY inicial:', page.evaluate('scrollY'))
    # Lo que hace selectBlock() en el editor: hijo real del marcador
    res = page.evaluate('''() => {
      const mark = document.querySelector('[data-blk="contact"]')
      const el = mark?.firstElementChild || mark
      if (!el?.scrollIntoView) return 'no el'
      el.scrollIntoView({behavior:'instant', block:'start'})
      el.animate?.([{boxShadow:'0 0 0 4px rgba(99,91,255,.8)'},{boxShadow:'0 0 0 4px rgba(99,91,255,0)'}],{duration:600})
      return {tag: el.tagName, cls: el.className?.toString().slice(0,60), rect: !!mark.getBoundingClientRect}
    }''')
    print('target:', res)
    page.wait_for_timeout(600)
    print('scrollY tras scrollIntoView:', page.evaluate('scrollY'))
    # Y a la inversa: desde un elemento interno, closest -> marcador
    print('closest desde contenido:', page.evaluate('''() => {
      const inner = document.querySelector('[data-blk="contact"] input, [data-blk="contact"] button, [data-blk="contact"] h2, [data-blk="contact"] *')
      const m = inner?.closest?.('[data-blk]')
      return m?.getAttribute('data-blk')
    }'''))
    b.close()
