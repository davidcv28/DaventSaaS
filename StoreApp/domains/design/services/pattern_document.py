"""
Documento HTML publicado de un DesignPattern.

El patrón (HTML/CSS/JS) se sirve como documento real en su propia URL, no
como `srcdoc`: la vista previa y la web publicada cargan exactamente el
mismo archivo. Además, el documento no usa scripts inline (el CSP de
producción solo permite `script-src 'self'`): el JS del diseño y el puente
de medición/navegación viajan como `<script src>` del mismo origen.
"""

import re
from pathlib import Path
from urllib.parse import urlencode

from django.utils.html import escape

#El CSP de producción no permite inline: se sacan handlers `on*=` y
#`<script>` del markup (el JS del diseño viaja por `pattern.js`).
#El handler se elimina con comillas dobles, simples o sin comillas: la
#variante `onerror='…'` y `onbegin=alert(1)` sobrevivían al filtro y el
#documento corre en el MISMO origen de la app (iframe `allow-same-origin`).
INLINE_HANDLER_RE = re.compile(r"""\son[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", re.I)
INLINE_SCRIPT_RE = re.compile(r'<script\b[^>]*>.*?</script>', re.I | re.S)
#URL ejecutable en un atributo de navegación: `javascript:` en un href/src
#corre código dentro del documento (y del origen de la app).
SCRIPT_URL_RE = re.compile(
    r"""(\s(?:href|src|action|formaction|xlink:href)\s*=\s*)"""
    r"""(?:"\s*(?:javascript|vbscript|data:text/html)[^"]*"|'\s*(?:javascript|vbscript|data:text/html)[^']*'|(?:javascript|vbscript|data:text/html)[^\s>]*)""",
    re.I,
)
#`<base>` reescribe TODAS las URLs relativas del documento (incluido el
#`<script src>` del puente): un `<base href="//evil">` desvía el JS del
#diseño a un host ajeno. Los embeds externos y el refresh por meta tampoco
#tienen lugar en un diseño.
DANGEROUS_TAG_RE = re.compile(r'<(?:base|object|embed|iframe|frame|frameset)\b[^>]*>', re.I)
META_REFRESH_RE = re.compile(r'<meta\b[^>]*http-equiv\s*=\s*["\']?refresh[^>]*>', re.I)

#CSP del documento del diseño. El iframe va SANDBOXEADO sin
#`allow-same-origin`: el documento tiene origen opaco y no puede tocar el DOM
#ni las cookies de la app. En un origen opaco `'self'` no matchea nada, así
#que el JS del diseño y del puente se autoriza por NONCE (por request) y el
#resto de la política no depende del host: el mismo documento funciona
#detrás de un proxy que reescribe el `Host` (dev con vite, nginx, Render).
#
#`frame-ancestors` queda fuera a propósito: lo cubre `X-Frame-Options:
#SAMEORIGIN` de la respuesta, que compara contra el origen real del
#navegador y no contra el `Host` interno que ve Django.
DOCUMENT_CSP = (
    "default-src 'none'; "
    "script-src {scripts}; "
    "style-src 'unsafe-inline'; "
    "img-src https: data:; "
    "font-src https: data:; "
    "media-src https:; "
    "connect-src 'none'; "
    "frame-src 'none'; child-src 'none'; worker-src 'none'; "
    "object-src 'none'; base-uri 'none'; form-action 'none'"
)


def document_csp(nonce):
    """
    Política del documento para el nonce de ESTA respuesta. Sin nonce cae a
    `script-src 'none'`: mejor una web sin JS que una política abierta.
    """
    nonce   =   str(nonce or '')
    if not nonce or not re.fullmatch(r'[A-Za-z0-9_\-]{8,64}', nonce):
        return DOCUMENT_CSP.format(scripts = "'none'")
    return DOCUMENT_CSP.format(scripts = f"'nonce-{nonce}'")

#Reglas del host (no del diseño): una sola superficie visible y los
#controles del catálogo con la tipografía del documento.
SURFACE_CSS = """
[data-surface]{}
html[data-ds-surface="landing"] [data-surface]:not([data-surface="landing"]),
html[data-ds-surface="catalog"] [data-surface]:not([data-surface="catalog"]),
html[data-ds-surface="services"] [data-surface]:not([data-surface="services"]),
html[data-ds-surface="product"] [data-surface]:not([data-surface="product"]){display:none!important}
[hidden]{display:none!important}
img[src=""]{display:none!important}

/* Cáscaras sin dato: una fila de resumen/contacto cuyo valor salió vacío, un
   título bajada sin texto o una sección cuya grilla quedó sin ítems no se
   muestran — la vista previa y la web no pintan residuos. */
.stat:has(.txt>span:last-child:empty),
.contact-row:has(>span:last-child:empty){display:none!important}
.eyebrow:empty,.lead:empty,p:empty{display:none!important}
li:empty,dd:empty,dt:has(+dd:empty){display:none!important}
section:has(.catalog-grid:empty),
section:has(.ds-plans:empty){display:none!important}
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
.svc-cta{display:inline-block;margin-top:22px;padding:11px 16px;border-radius:var(--ds-radius,6px);background:var(--ds-accent,#111);color:var(--ds-accent-ink,#fff);font-size:11px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none}

/* Personalidad de subtítulos (común a todos los diseños): el texto que
   acompaña a un título de sección se lee como etiqueta editorial, con una
   regla corta y el acento del estilo. */
.head > span,.head > small,.cat-head > span{
  display:inline-flex;align-items:center;gap:8px;
  color:var(--ds-accent,currentColor);
  font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
}
.head > span:not(:empty)::before,
.head > small:not(:empty)::before,
.cat-head > span:not(:empty)::before{
  content:"";flex:none;width:18px;height:1px;background:currentColor;opacity:.6;
}

/* Relleno visual de bandas planas: una retícula tenue evita el bloque
   vacío sin competir con el contenido. */
.band.white,.band.gray,.cat-surface,.svc-surface{
  background-image:radial-gradient(color-mix(in srgb,var(--ink,currentColor) 4%,transparent) 1px,transparent 1px);
  background-size:22px 22px;
}

/* Media sin imagen: degradado de marca + marca de agua en vez de un
   rectángulo gris. */
.ds-product-img.is-empty,.hero-media{
  background-image:
    radial-gradient(120% 100% at 18% 0%,color-mix(in srgb,var(--ds-accent,#888) 13%,transparent),transparent 62%),
    linear-gradient(150deg,color-mix(in srgb,var(--ink,#111) 5%,transparent),transparent 58%);
  background-color:var(--soft,var(--surface,#f5f5f5));
}
.ds-product-img.is-empty::after{opacity:.55}

/* Etiqueta de campaña que firma la oferta (Hot Sale, Navidad…): sticker
   anclado a la esquina superior de la tarjeta. Vive en la hoja del host —
   no en cada patrón — porque pattern_render la emite en todos los
   documentos y sin regla la <img> fluye a tamaño completo. */
.ds-product{position:relative}
.ds-campaign-label{
  position:absolute;top:10px;left:10px;z-index:4;height:22px;width:auto;
  max-width:60%;object-fit:contain;border-radius:3px;
  box-shadow:0 8px 16px -10px rgba(0,0,0,.55);
}

/* Tag de disponibilidad de la tarjeta: el catálogo solo publica productos
   en stock (no hay inventario en el sistema). */
.ds-stock{
  display:inline-flex;align-items:center;gap:5px;
  font-size:11px;font-weight:600;letter-spacing:.04em;
  color:var(--ds-success,#0f9d58);
}
.ds-stock i{width:6px;height:6px;border-radius:50%;background:currentColor;flex:none}
/* Sin token del estilo el verde de stock no llega a AA en oscuro. */
html[data-ds-theme="dark"] .ds-stock{color:var(--ds-success,#5ecf8f)}

/* Opiniones de producto: honeypot fuera de pantalla y pulgar inline. */
.ds-rev-hp{position:absolute!important;left:-9999px;width:1px;height:1px;overflow:hidden}
.ds-rev-vote{display:inline-block;vertical-align:-1px}
.ds-rev-vote svg{display:block}
/* Respuesta del dueño bajo la opinión: filete de acento + etiqueta en
   versalitas; las variables caen a neutros en diseños sin tokens. */
.ds-rev-reply{margin-top:8px;padding:8px 10px;border-left:2px solid var(--ds-accent,var(--line,#bbb));background:color-mix(in srgb,var(--ds-accent,#888) 7%,transparent);border-radius:0 var(--ds-radius,4px) var(--ds-radius,4px) 0;font-size:12px;line-height:1.55;color:var(--ink-2,var(--ink,currentColor))}
.ds-rev-reply strong{display:block;margin-bottom:2px;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--ds-accent,var(--ink,currentColor))}
.ds-rev-reply span{display:block;white-space:pre-wrap;overflow-wrap:anywhere}
"""

#El puente vive junto a este módulo y se sirve desde la misma URL del
#documento (`../bridge.js/`): el CSP de producción solo permite
#`script-src 'self'`, así que nada de scripts inline ni de assets del front.
BRIDGE_SCRIPT = Path(__file__).with_name('pattern_bridge.js').read_text(encoding = 'utf-8')
BRIDGE_FILE = Path(__file__).with_name('pattern_bridge.js')
BRIDGE_URL = '../bridge.js/'

def bridge_url():
    """
    URL del puente con la versión del archivo. El puente se sirve con cache
    larga; al cambiar el archivo (deploy o edición) cambia la query y el
    navegador pide la versión nueva sin esperar al TTL.
    """
    try:
        version = int(BRIDGE_FILE.stat().st_mtime)
    except OSError:
        version = 0
    return f'{BRIDGE_URL}?v={version}'


def sanitize_markup(html):
    """
    Markup del diseño sin nada ejecutable: scripts, handlers `on*=` (con
    cualquier comilla), URLs `javascript:`/`data:text/html`, `<base>`,
    embeds y refresh por meta. El documento corre en el mismo origen de la
    app, así que el saneo + el CSP son la barrera del iframe.
    """
    html = INLINE_SCRIPT_RE.sub('', html or '')
    html = INLINE_HANDLER_RE.sub('', html)
    html = SCRIPT_URL_RE.sub(r'\1="#"', html)
    html = DANGEROUS_TAG_RE.sub('', html)
    return META_REFRESH_RE.sub('', html)


def pattern_document(html, css, theme, surface, preview = '', style = '', nonce = '', preload = None, template = '', commerce = False):
    """
    Documento completo listo para servir como `text/html`.
    `html` ya viene renderizado contra la tienda y `css` ya trae el tema del
    estilo + la hoja del patrón. `preload` son las imágenes críticas
    (portada del hero) que conviene descubrir antes de parsear el body.
    `template` es el diseño en ensayo: se propaga a `script.js` para que el
    JS corresponda al patrón del documento (antes servía el del borrador).
    `commerce` marca `data-ds-commerce` en <html>: la tienda vende online
    (orders_enabled) y el puente inyecta los CTA "Agregar al carrito" —
    el documento nunca toca la API de carrito (origen opaco), solo avisa
    al host por postMessage.
    """
    query = {'surface': surface, 'theme': theme}
    if preview:
        query['preview'] = preview
        if template:
            query['template'] = template
    script = f'../script.js/?{urlencode(query)}'
    html = sanitize_markup(html)
    #Tema/superficie van a atributos del `<html>`: se normalizan acá y no
    #solo en la vista. `surfaces` sale del HTML del diseño (regex), así que
    #un valor raro podía viajar de vuelta al documento y romper el atributo.
    theme   = 'dark' if str(theme or '').lower() == 'dark' else 'light'
    surface = re.sub(r'[^a-z0-9-]', '', str(surface or '').lower())[:40] or 'landing'
    #Solo slug ASCII: el atributo lo escriben selectores CSS, nunca HTML.
    style = re.sub(r'[^a-z0-9-]', '', str(style or '').lower())[:80]
    style_attr = f' data-ds-style="{style}"' if style else ''
    commerce_attr = ' data-ds-commerce="1"' if commerce else ''
    #Los dos `<script>` son los únicos ejecutables del documento: el nonce
    #(CSP `script-src 'nonce-…'`) los autoriza sin depender del origen.
    nonce   =   str(nonce or '')
    nonce_attr = f' nonce="{nonce}"' if re.fullmatch(r'[A-Za-z0-9_\-]{8,64}', nonce) else ''
    preload_links = ''.join(
        f'<link rel="preload" as="image" href="{escape(str(url))}" fetchpriority="high">'
        for url in (preload or [])[:2] if url
    )
    return (
        f'<!doctype html><html lang="es" data-ds-theme="{theme}" data-ds-surface="{surface}"{style_attr}{commerce_attr}>'
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'{preload_links}'
        #La hoja base del host va ANTES de la del diseño: si va después,
        #sus reglas genéricas (.ds-cat, .cat-sort) pisan la piel del patrón
        #por empate de especificidad (los chips del catálogo quedaban sin
        #estilo). El !important de las superficies sigue ganando igual.
        f'<style>html,body{{margin:0}}{SURFACE_CSS}{css}</style></head><body>'
        f'{html}'
        f'<script src="{script}"{nonce_attr}></script>'
        f'<script src="{bridge_url()}"{nonce_attr}></script>'
        '</body></html>'
    )
