"""
Documento HTML publicado de un DesignPattern.

El patrón (HTML/CSS/JS) se sirve como documento real en su propia URL, no
como `srcdoc`: la vista previa y la web publicada cargan exactamente el
mismo archivo. Además, el documento no usa scripts inline (el CSP de
producción solo permite `script-src 'self'`): el JS del diseño y el puente
de medición/navegación viajan como `<script src>` del mismo origen.
"""

from urllib.parse import urlencode

import re
from pathlib import Path

#El CSP de producción no permite inline: se sacan handlers `on*=` y
#`<script>` del markup (el JS del diseño viaja por `pattern.js`).
INLINE_HANDLER_RE = re.compile(r'\son[a-z]+\s*=\s*"[^"]*"', re.I)
INLINE_SCRIPT_RE = re.compile(r'<script\b[^>]*>.*?</script>', re.I | re.S)

#Reglas del host (no del diseño): una sola superficie visible y los
#controles del catálogo con la tipografía del documento.
SURFACE_CSS = """
[data-surface]{}
html[data-ds-surface="landing"] [data-surface]:not([data-surface="landing"]),
html[data-ds-surface="catalog"] [data-surface]:not([data-surface="catalog"]),
html[data-ds-surface="services"] [data-surface]:not([data-surface="services"]){display:none!important}
[hidden]{display:none!important}
img[src=""]{display:none!important}
[data-ds-filters] .ds-cat{font:inherit;cursor:pointer;background:none;border:0;color:inherit;padding:0}
[data-ds-filters] .ds-cat[aria-pressed="true"]{color:var(--ds-accent,#111);text-decoration:underline;text-underline-offset:5px}
.cat-head{display:flex;justify-content:space-between;align-items:baseline;gap:14px;border-bottom:1px solid currentColor;padding-bottom:10px}
.cat-head h1{font-size:clamp(28px,4vw,44px)}
.cat-head span{font-size:10px;letter-spacing:.2em;text-transform:uppercase;opacity:.7}
.cat-tools{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;padding:14px 0}
.cat-filters{display:flex;flex-wrap:wrap;gap:8px 14px}
.cat-sort{display:inline-flex;align-items:center;gap:8px;font-size:10px;letter-spacing:.16em;text-transform:uppercase;opacity:.8}
.cat-sort select{font:inherit;letter-spacing:0;text-transform:none;padding:6px 8px;border:1px solid currentColor;border-radius:var(--ds-radius,6px);background:transparent;color:inherit}
.cat-surface,.svc-surface{padding:34px 0 30px}
.svc-head h1{font-size:clamp(28px,4vw,44px)}
.svc-head p{margin:8px 0 0;font-size:12.5px;opacity:.75;max-width:46ch}
.svc-head p:empty{display:none}
.svc-cta{display:inline-block;margin-top:22px;padding:11px 16px;border-radius:var(--ds-radius,6px);background:var(--ds-accent,#111);color:#fff;font-size:11px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none}
"""

#El puente vive junto a este módulo y se sirve desde la misma URL del
#documento (`../bridge.js/`): el CSP de producción solo permite
#`script-src 'self'`, así que nada de scripts inline ni de assets del front.
BRIDGE_SCRIPT = Path(__file__).with_name('pattern_bridge.js').read_text(encoding = 'utf-8')
BRIDGE_URL = '../bridge.js/'


def pattern_document(html, css, theme, surface, preview = ''):
    """
    Documento completo listo para servir como `text/html`.
    `html` ya viene renderizado contra la tienda y `css` ya trae el tema del
    estilo + la hoja del patrón.
    """
    query = {'surface': surface, 'theme': theme}
    if preview:
        query['preview'] = preview
    script = f'../script.js/?{urlencode(query)}'
    html = INLINE_SCRIPT_RE.sub('', html or '')
    html = INLINE_HANDLER_RE.sub('', html)
    return (
        f'<!doctype html><html lang="es" data-ds-theme="{theme}" data-ds-surface="{surface}">'
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<style>html,body{{margin:0}}{css}{SURFACE_CSS}</style></head><body>'
        f'{html}'
        f'<script src="{script}"></script>'
        f'<script src="{BRIDGE_URL}"></script>'
        '</body></html>'
    )
