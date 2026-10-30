"""QA headless de las superficies catálogo/servicios de cada patrón."""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from pathlib import Path
from StoreApp.domains.design.models import DesignPattern
from StoreApp.domains.design.services.pattern_render import build_store_context, theme_css
from StoreApp.domains.stores.models import Store

OUT = Path('.tmp/qa-surfaces')
OUT.mkdir(parents=True, exist_ok=True)
SLUGS = sys.argv[1:] or ['raiz', 'alimentos', 'trama', 'indumentaria', 'boutique',
                         'atelier', 'clasico', 'circuito', 'seguridad']

HIDE = ('html[data-ds-surface="catalog"] [data-surface]:not([data-surface="catalog"]),'
        'html[data-ds-surface="services"] [data-surface]:not([data-surface="services"]){display:none!important}'
        '[hidden]{display:none!important}')

store = Store.objects.get(slug='demo')
custom = store.customization
context, raw = build_store_context(store)


def document(pattern, theme, surface):
    css = theme_css(custom, pattern) + '\n' + (pattern.css or '') + '\n' + HIDE
    html = pattern.render(context, raw=raw)
    return (
        '<!doctype html><html lang="es" data-ds-theme="%s" data-ds-surface="%s">'
        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>html,body{margin:0}%s</style></head><body>%s<script>%s</script></body></html>'
    ) % (theme, surface, css, html, pattern.js or '')


DOCS = {}
for slug in SLUGS:
    pattern = DesignPattern.objects.get(slug=slug)
    for surface in ('catalog', 'services'):
        for theme in ('light', 'dark'):
            file = OUT / f'{slug}-{surface}-{theme}.html'
            file.write_text(document(pattern, theme, surface), encoding='utf-8')
            DOCS[(slug, surface, theme)] = file

from playwright.sync_api import sync_playwright
problems = []
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for (slug, surface, theme), file in DOCS.items():
        for width in (1360, 390):
            page = browser.new_page(viewport={'width': width, 'height': 900})
            errors = []
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.goto(file.resolve().as_uri())
            page.wait_for_timeout(250)
            info = page.evaluate("""() => {
                const d = document.documentElement;
                const visible = [...document.querySelectorAll('[data-surface]')]
                  .filter(el => getComputedStyle(el).display !== 'none')
                  .map(el => el.getAttribute('data-surface'));
                return { overflow: d.scrollWidth - d.clientWidth, visible,
                         products: document.querySelectorAll('.ds-product').length,
                         services: document.querySelectorAll('.ds-service').length,
                         height: d.scrollHeight };
            }""")
            page.screenshot(path=str(OUT / f'{slug}-{surface}-{theme}-{width}.png'), full_page=True)
            if info['overflow'] > 1 or info['visible'] != [surface] or errors:
                problems.append((slug, surface, theme, width, info, errors[:2]))
            page.close()
    browser.close()

print(json.dumps({'ok': not problems, 'problems': problems}, ensure_ascii=False, indent=1)[:4000])
