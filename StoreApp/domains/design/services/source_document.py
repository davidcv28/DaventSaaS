"""
Documento fuente de un patrón de diseño (HTML de archivo único).

`StoreApp/domains/design/sources/<slug>.html` es la fuente editable de un
`DesignPattern`: se parte en las tres capas del modelo (`html`, `css`, `js`)
y sus `variables` se derivan de los placeholders `{{nombre}}` que el markup
usa de verdad (solo los que están en el contrato `PATTERN_VARIABLES`).

Así el seed no puede declarar una variable que el diseño no pinta ni pintar
una variable que la tienda no puede resolver.
"""

import re
from pathlib import Path

from StoreApp.domains.design.services.pattern_render import PATTERN_VARIABLES

SOURCES_DIR = Path(__file__).resolve().parents[1] / 'sources'

STYLE_RE    =   re.compile(r'<style[^>]*>(.*?)</style>', re.S | re.I)
SCRIPT_RE   =   re.compile(r'<script[^>]*>(.*?)</script>', re.S | re.I)
BODY_RE     =   re.compile(r'<body[^>]*>(.*?)</body>', re.S | re.I)
HEAD_RE     =   re.compile(r'<(title|meta)\b[^>]*>.*?</\1>|<(title|meta)\b[^>]*/?>', re.S | re.I)
#Assets externos (CDN de Tailwind, Google Fonts): no tienen contenido inline,
#así que se conservan tal cual al inicio del html para que el preview cargue.
ASSET_RE    =   re.compile(r'<script\b[^>]*\bsrc=[^>]*>\s*</script>|<link\b[^>]*>', re.S | re.I)
VAR_RE      =   re.compile(r'\{\{\s*([a-z][a-z0-9_]{0,39})\s*\}\}')

#=========================================
# SPLIT DEL DOCUMENTO
#=========================================
def split_document(document):
    """Devuelve `(html, css, js)` de un documento HTML de archivo único."""
    css = '\n'.join(m.group(1).strip() for m in STYLE_RE.finditer(document)).strip()
    js  = '\n'.join(m.group(1).strip() for m in SCRIPT_RE.finditer(document)).strip()
    body = BODY_RE.search(document)
    html = body.group(1) if body else document
    html = STYLE_RE.sub('', html)
    html = SCRIPT_RE.sub('', html)
    html = HEAD_RE.sub('', html)
    assets = '\n'.join(m.group(0) for m in ASSET_RE.finditer(document))
    html = ASSET_RE.sub('', html)
    if assets:
        html = f'{assets}\n{html}'
    return html.strip(), css, js

#=========================================
# VARIABLES DECLARADAS POR EL MARKUP
#=========================================
def variables_from_markup(*chunks):
    """
    Variables del contrato que el markup (html/css/js) usa, en el orden
    canónico de `PATTERN_VARIABLES`.
    """
    used = set()
    for chunk in chunks:
        used.update(VAR_RE.findall(chunk or ''))
    return {
        name: dict(spec)
        for name, spec in PATTERN_VARIABLES.items()
        if name in used
    }

#=========================================
# FUENTE EDITABLE DE UN PATRÓN
#=========================================
def source_path(slug):
    return SOURCES_DIR / f'{slug}.html'

def load_source(slug):
    """
    `(html, css, js, variables)` desde `sources/<slug>.html`, o `None` si el
    patrón todavía no tiene fuente editable.
    """
    path = source_path(slug)
    if not path.exists():
        return None
    html, css, js = split_document(path.read_text(encoding = 'utf-8'))
    return html, css, js, variables_from_markup(html, css, js)
