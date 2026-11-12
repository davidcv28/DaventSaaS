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
#El handler se elimina con comillas dobles, simples, sin comillas o pegado
#a `/`/comilla (HTML5 tokeniza `/` antes de atributo y acepta atributos
#nuevos tras una comilla de cierre sin whitespace): `onerror='…'`,
#`onbegin=alert(1)`, `<svg/onload=…>` y `<img src="x"onerror=…>`.
#El lookbehind excluye `-`/`:` para no tocar `data-onclick` ni `json=`.
INLINE_HANDLER_RE = re.compile(r"""(?<![\w:-])on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", re.I)
#El documento no lleva `<script>` propio (el JS viaja por `pattern.js`): se
#eliminan bloques completos, etiquetas sueltas, self-closing y cierres
#espaciados (`</script >`). Un `<script>` huérfano sin cerrar devoraría los
#`<script>` con nonce del documento y dejaría la página sin puente.
SCRIPT_RE = re.compile(r'<script\b[^>]*>.*?</script\s*>|</?script\b[^>]*>', re.I | re.S)


def _obf_scheme(word):
    """
    Fragmento de regex para un scheme peligroso tolerando ofuscación que el
    navegador decodifica dentro de URLs: entidades (`&#106;`, `&Tab;`,
    `&colon;`…) y whitespace entre caracteres. Sobre-bloquear es seguro:
    el peor caso es reescribir un href raro a `#`.
    """
    junk   =   r'(?:&[#\w]+;|\s)*'
    parts  =   [f'(?:{re.escape(ch)}|&[#\w]+;)' for ch in word]
    return  junk.join(parts)


_DANGER_SCHEME   =   (rf'(?:{_obf_scheme("javascript")}|{_obf_scheme("vbscript")}'
                     rf'|{_obf_scheme("data:text/html")})')
#URL ejecutable en un atributo de navegación: `javascript:`/`vbscript:`/
#`data:text/html` en href/src/action/etc. corre código (o phishing) dentro
#del documento. El boundary `(?<![\w:-])` cubre `/` y comillas adyacentes.
SCRIPT_URL_RE = re.compile(
    rf"""((?<![\w:-])(?:href|src|action|formaction|xlink:href|poster|background|srcset|ping)\s*=\s*)"""
    rf"""(?:"\s*{_DANGER_SCHEME}[^"]*"|'\s*{_DANGER_SCHEME}[^']*'|{_DANGER_SCHEME}[^\s>]*)""",
    re.I,
)
#`<base>` reescribe TODAS las URLs relativas del documento (incluido el
#`<script src>` del puente): un `<base href="//evil">` desvía el JS del
#diseño a un host ajeno. Los embeds externos tampoco tienen lugar.
DANGEROUS_TAG_RE = re.compile(r'<(?:base|object|embed|iframe|frame|frameset)\b[^>]*>', re.I)
#Todo `<meta>` sale del markup del patrón: el documento ya declara charset y
#viewport en su `<head>` propio, y cualquier meta restante solo sirve para
#refresh/navegación encubierta (el regex de refresh se bypaseaba con
#entidades `&#114;efresh` o espacios dentro de las comillas — el CSP no
#cubre meta refresh).
META_TAG_RE = re.compile(r'<meta\b[^>]*>', re.I)
#La hoja viaja dentro de `<style>…</style>`: un `</style` en el CSS
#(`pattern.css` es texto admin sin filtrar) cerraría el elemento y lo que
#sigue se parsearía como HTML — meta refresh, trackers, handlers.
STYLE_CLOSE_RE = re.compile(r'</\s*style', re.I)

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

/* Superficie "chrome": el documento se monta fijo sobre las páginas que NO
   son del diseño (cuenta, auth, carrito, checkout, seguimiento) solo para
   darles el navbar/cromo del patrón. El contenido (superficies, pie en
   flujo, chatbot del puente) se apaga y los wrappers dejan de pedir 100vh:
   el alto que reporta el puente queda en el cromo superior + las barras
   fijas de abajo. */
html[data-ds-surface="chrome"],
html[data-ds-surface="chrome"] body{overflow:hidden}
html[data-ds-surface="chrome"] [data-surface],
html[data-ds-surface="chrome"] footer,
html[data-ds-surface="chrome"] .foot,
html[data-ds-surface="chrome"] .footer,
html[data-ds-surface="chrome"] .ds-chat{display:none!important}
html[data-ds-surface="chrome"] body,
html[data-ds-surface="chrome"] body>*:not([data-ds-pin]){min-height:0!important}
/* Contenedores de CTA de la ficha que quedaron sin hijos visibles: sin
   WhatsApp ni venta online el diseño deja `.pdp-buy`/`.pdp-ctas` vacío o
   con solo el anchor `href=""` (oculto por la regla propia del diseño) y
   el tema lo pinta igual como botón. Una cáscara vacía no se muestra. */
.pdp-buy:not(:has(> :not(a[href=""]))),
.pdp-ctas:not(:has(> :not(a[href=""]))),
.pdp-actions:not(:has(> :not(a[href=""]))){display:none!important}
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

/* Línea de envío de la ficha ({{product_shipping}}): los diseños la
   montan junto al precio/CTA; vacía (tienda sin venta online) el <p>
   queda :empty y desaparece. El aire superior la separa del precio. */
.ds-ship{font-size:12px;font-weight:600;line-height:1.45;opacity:.8;margin:12px 0 0}
.ds-ship:empty{display:none!important}
/* El valor de la tarifa viaja marcado (.ds-ship-price, fragmento raw) y va
   siempre en verde de estado: el precio y el "sin cargo" se leen como dato
   positivo. */
.ds-ship .ds-ship-price{color:var(--ds-success,#0f9d58)}

/* Medios de pago de la ficha ({{product_payments}}): chips sobrios con
   los métodos habilitados (transferencia/WhatsApp/efectivo/Mercado
   Pago). Solo tokens --ds-* — funciona en claro y oscuro sin reglas
   extra. Vacío (tienda sin venta online) queda :empty y desaparece. */
.ds-pay{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin:12px 0 0}
.ds-pay:empty{display:none!important}
/* El texto genérico que el diseño traía bajo el precio ("Medios de pago y
   cuotas se coordinan…") duplicaba el mensaje cuando los chips ya están:
   se retira solo en los documentos donde el fragmento va justo antes. */
.ds-pay + .pdp-pay{display:none!important}
/* El CTA de la ficha no debe quedar pegado a los chips: los contenedores
   de compra de los diseños (mismo fragmento compartido) suman aire. */
.ds-pay + .pdp-buy,
.ds-pay + .pdp-ctas,
.ds-pay + .pdp-actions{margin-top:16px}
.ds-pay-label{font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;opacity:.65}
.ds-pay-chip{display:inline-flex;align-items:center;gap:5px;padding:4px 9px;
  border:1px solid var(--ds-border,var(--line,#ddd));border-radius:999px;
  font-size:11px;font-weight:600;line-height:1.2;letter-spacing:.02em;
  color:var(--ds-text,var(--ink,currentColor));
  background:color-mix(in srgb,var(--ds-accent,#888) 5%,transparent)}
.ds-pay-chip svg{flex:none;opacity:.75}

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

/* Tag de disponibilidad de la tarjeta: fallback "En stock" del fragmento —
   con venta online el puente repinta la cifra real (davent:ds-stock). */
.ds-stock{
  display:inline-flex;align-items:center;gap:5px;
  font-size:11px;font-weight:600;letter-spacing:.04em;
  color:var(--ds-success-text,var(--ds-success,#0f9d58));
}
.ds-stock i{width:6px;height:6px;border-radius:50%;background:currentColor;flex:none}
/* Sin token del estilo el verde de stock no llega a AA en oscuro: se
   aclara hacia blanco un 45% — las superficies de noche son fijas y no
   las conoce la paleta, así que el ajuste fino por paleta
   (--ds-success-text) se refuerza con esta mezcla en el modo noche. */
html[data-ds-theme="dark"] .ds-stock{color:color-mix(in srgb,var(--ds-success-text,var(--ds-success,#5ecf8f)) 55%,#fff)}

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
    Markup del diseño sin nada ejecutable: scripts (bloques y etiquetas
    sueltas), handlers `on*=` (con cualquier comilla o separador `/`),
    URLs `javascript:`/`vbscript:`/`data:text/html` (incl. ofuscadas por
    entidades), `<base>`, embeds y TODO `<meta>` (el refresh se bypaseaba
    por entidades/espacios y el CSP no lo cubre). El documento corre en
    origen opaco, así que el saneo + el CSP son la barrera del iframe.
    """
    html = SCRIPT_RE.sub('', html or '')
    html = INLINE_HANDLER_RE.sub('', html)
    html = SCRIPT_URL_RE.sub(r'\1"#"', html)
    html = DANGEROUS_TAG_RE.sub('', html)
    return META_TAG_RE.sub('', html)


def sanitize_css(css):
    """
    La hoja viaja dentro de `<style>…</style>` en el documento y en el
    srcdoc de la vista previa: un `</style` en el CSS (`pattern.css` es
    texto admin sin filtrar, junto a theme/studio css ya validados)
    cerraría el elemento y lo que sigue se parsearía como HTML — meta
    refresh, trackers o handlers. Se elimina la secuencia de cierre; el
    resto del CSS no puede salir del contexto raw-text.
    """
    return STYLE_CLOSE_RE.sub('', css or '')


def pattern_document(html, css, theme, surface, preview = '', style = '', nonce = '', preload = None, template = '', commerce = False, events = 0):
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
    al host por postMessage. `events` es el conteo global de productos con
    descuento programado vigente: viaja como `data-ds-events` y el puente
    muestra el filtro "Eventos" del catálogo solo cuando hay eventos.
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
    #Conteo de eventos del catálogo: entero acotado, saneado igual que el
    #resto de los flags del <html>.
    try:
        events_n = max(0, min(9999, int(events or 0)))
    except (TypeError, ValueError):
        events_n = 0
    events_attr = f' data-ds-events="{events_n}"' if events_n else ''
    #Los dos `<script>` son los únicos ejecutables del documento: el nonce
    #(CSP `script-src 'nonce-…'`) los autoriza sin depender del origen.
    nonce   =   str(nonce or '')
    nonce_attr = f' nonce="{nonce}"' if re.fullmatch(r'[A-Za-z0-9_\-]{8,64}', nonce) else ''
    preload_links = ''.join(
        f'<link rel="preload" as="image" href="{escape(str(url))}" fetchpriority="high">'
        for url in (preload or [])[:2] if url
    )
    return (
        f'<!doctype html><html lang="es" data-ds-theme="{theme}" data-ds-surface="{surface}"{style_attr}{commerce_attr}{events_attr}>'
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'{preload_links}'
        #La hoja base del host va ANTES de la del diseño: si va después,
        #sus reglas genéricas (.ds-cat, .cat-sort) pisan la piel del patrón
        #por empate de especificidad (los chips del catálogo quedaban sin
        #estilo). El !important de las superficies sigue ganando igual.
        f'<style>html,body{{margin:0}}{SURFACE_CSS}{sanitize_css(css)}</style></head><body>'
        f'{html}'
        f'<script src="{script}"{nonce_attr}></script>'
        f'<script src="{bridge_url()}"{nonce_attr}></script>'
        '</body></html>'
    )
