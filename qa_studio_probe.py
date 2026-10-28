"""Probe: does studio:update postMessage actually switch the template live?

Loads /bench-store?studio=1, posts the same message StudioShell sends on
"Probar", and reports data-store-template before/after on .store-page.
"""
import json, urllib.request
from playwright.sync_api import sync_playwright

HOME = 'http://localhost:5173/bench-store?studio=1'
API = 'http://127.0.0.1:8000/api/stores/public/bench-store/'

tpl = json.load(urllib.request.urlopen(API)).get('customization', {}).get('template')
print('saved template:', tpl)

MSG = {
    'type': 'studio:update',
    'theme': {},
    'layout': {},
    'template': 'aurora',
    'device': 'desktop',
    'mode': 'dark',
}

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={'width': 1280, 'height': 900})
    msgs = []
    page.on('console', lambda m: msgs.append(f'{m.type}: {m.text[:150]}'))
    page.on('pageerror', lambda e: msgs.append(f'PAGEERROR: {e}'))
    page.goto(HOME, wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(1000)

    before = page.evaluate("() => document.querySelector('.store-page')?.getAttribute('data-store-template')")
    print('data-store-template BEFORE:', before)

    # Post the message from inside the page (same-origin -> passes e.origin check)
    page.evaluate(f"""() => window.postMessage({json.dumps(MSG)}, window.location.origin)""")
    page.wait_for_timeout(2500)

    after = page.evaluate("() => document.querySelector('.store-page')?.getAttribute('data-store-template')")
    theme = page.evaluate("() => document.querySelector('.store-page')?.getAttribute('data-store-theme')")
    print('data-store-template AFTER :', after)
    print('data-store-theme    AFTER :', theme)
    errs = [m for m in msgs if 'error' in m.lower()]
    print('console errors:', errs[:5] if errs else 'none')
    print('RESULT:', 'PASS' if after == 'aurora' and theme == 'dark' else 'FAIL')
    b.close()
