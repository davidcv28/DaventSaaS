"""QA headless de los patrones de diseño (documento real, claro/oscuro, 1360/390)."""
import os, sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from pathlib import Path
from StoreApp.domains.design.models import DesignPattern
from StoreApp.domains.design.services.pattern_render import build_store_context, theme_css
from StoreApp.domains.stores.models import Store

OUT = Path('.tmp/qa-patterns')
OUT.mkdir(parents=True, exist_ok=True)
SLUGS = sys.argv[1:] or ['raiz', 'alimentos', 'trama', 'indumentaria', 'boutique',
                         'atelier', 'clasico', 'circuito', 'seguridad']
WIDTHS = [360, 390, 768, 1024, 1360, 1920]

store = Store.objects.get(slug='demo')
custom = store.customization
context, raw = build_store_context(store)

def document(pattern, theme):
    css = theme_css(custom, pattern) + '\n' + (pattern.css or '')
    html = pattern.render(context, raw=raw)
    js = pattern.js or ''
    return (
        '<!doctype html><html lang="es" data-ds-theme="%s"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>html,body{margin:0}%s</style></head><body>%s<script>%s</script></body></html>'
    ) % (theme, css, html, js)

DOCS = {}
for slug in SLUGS:
    pattern = DesignPattern.objects.get(slug=slug)
    for theme in ('light', 'dark'):
        file = OUT / f'{slug}-{theme}.html'
        file.write_text(document(pattern, theme), encoding='utf-8')
        DOCS[(slug, theme)] = file

from playwright.sync_api import sync_playwright
problems = []
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for slug in SLUGS:
        for theme in ('light', 'dark'):
            file = DOCS[(slug, theme)]
            for width in WIDTHS:
                page = browser.new_page(viewport={'width': width, 'height': 900})
                errors = []
                page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                page.goto(file.resolve().as_uri())
                page.wait_for_timeout(350)
                page.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('on'))")
                page.wait_for_timeout(700)
                info = page.evaluate("""() => {
                    const d = document.documentElement;
                    const wide = [...document.querySelectorAll('body *')]
                      .filter(el => el.getBoundingClientRect().right > d.clientWidth + 1)
                      .slice(0, 4).map(el => el.tagName + '.' + (el.className || '').toString().slice(0, 40));
                    return { overflow: d.scrollWidth - d.clientWidth, wide,
                             products: document.querySelectorAll('.ds-product').length,
                             cats: document.querySelectorAll('.ds-cat').length,
                             services: document.querySelectorAll('.ds-service').length,
                             shots: document.querySelectorAll('.ds-shot').length,
                             height: d.scrollHeight };
                }""")
                page.screenshot(path=str(OUT / f'{slug}-{theme}-{width}.png'), full_page=True)
                if info['overflow'] > 1 or errors:
                    problems.append((slug, theme, width, info, errors[:3]))
                page.close()
    browser.close()

print(json.dumps({'ok': not problems, 'problems': problems}, ensure_ascii=False, indent=1)[:4000])
