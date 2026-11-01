"""
Render de un DesignPattern contra los datos reales de una tienda.

El patrón trae HTML + CSS + JS con placeholders `{{variable}}`. Este módulo
arma el contexto con lo que la tienda cargó (identidad, contacto, catálogo,
servicios, galería) y devuelve el documento listo para publicar.

Contrato:

* Las variables de texto/imagen/color las interpola `DesignPattern.render`
  y salen escapadas (fail-closed: una variable no declarada no se interpola).
* Las variables de tipo `list` se arman acá como fragmentos HTML y viajan en
  `raw`: cada dato de la tienda se escapa dentro del fragmento, así el único
  HTML que entra al documento es el que genera este módulo.
* El CSS del patrón se antepone con un bloque `:root` de custom properties
  (`--ds-*`) armado con los `effects`/`tokens` del estilo y el acento de la
  tienda: el estilo solo puede tocar bordes, colores y básicos.
"""

import re

from django.utils.html import escape, strip_tags

from StoreApp.domains.design.models import DesignPattern

#=========================================
# VARIABLES QUE DECLARA UN PATRON
#=========================================
#Nombres canónicos: el seed y el catálogo usan los mismos. Un patrón puede
#declarar un subconjunto; el resto se descarta en el render.
PATTERN_VARIABLES = {
    'store_name':        {'type': 'text',  'label': 'Nombre del negocio'},
    'store_initial':     {'type': 'text',  'label': 'Inicial del negocio'},
    'store_tagline':     {'type': 'text',  'label': 'Titular'},
    'store_description': {'type': 'text',  'label': 'Descripción'},
    'store_about':       {'type': 'text',  'label': 'Sobre nosotros'},
    'store_location':    {'type': 'text',  'label': 'Ciudad y provincia'},
    'store_address':     {'type': 'text',  'label': 'Dirección'},
    'store_phone':       {'type': 'text',  'label': 'Teléfono / WhatsApp'},
    'store_whatsapp_url': {'type': 'text', 'label': 'Link de WhatsApp'},
    'store_email':       {'type': 'text',  'label': 'Email de contacto'},
    'store_hours':       {'type': 'text',  'label': 'Horarios'},
    'store_instagram_url': {'type': 'text', 'label': 'Instagram'},
    'store_facebook_url': {'type': 'text', 'label': 'Facebook'},
    'store_tiktok_url':  {'type': 'text',  'label': 'TikTok'},
    'store_logo':        {'type': 'image', 'label': 'Logo'},
    'store_cover':       {'type': 'image', 'label': 'Portada'},
    'store_accent':      {'type': 'color', 'label': 'Color de acento'},
    'year':              {'type': 'number', 'label': 'Año'},
    'product_name':      {'type': 'text',  'label': 'Producto: nombre'},
    'product_description': {'type': 'text', 'label': 'Producto: descripción'},
    'product_price':     {'type': 'text',  'label': 'Producto: precio'},
    'product_old_price': {'type': 'text',  'label': 'Producto: precio antes de la oferta'},
    'product_offer_pct': {'type': 'text',  'label': 'Producto: % de ahorro'},
    'product_image':     {'type': 'image', 'label': 'Producto: imagen'},
    'product_category':  {'type': 'text',  'label': 'Producto: categoría'},
    'product_brand':     {'type': 'text',  'label': 'Producto: marca'},
    'product_ref':       {'type': 'text',  'label': 'Producto: referencia'},
    'product_whatsapp_url': {'type': 'text', 'label': 'Producto: consulta por WhatsApp'},
    'product_features':  {'type': 'list',  'label': 'Producto: características'},
    'product_related':   {'type': 'list',  'label': 'Producto: relacionados'},
    'products':          {'type': 'list',  'label': 'Productos'},
    'categories':        {'type': 'list',  'label': 'Categorías'},
    'services':          {'type': 'list',  'label': 'Servicios'},
    'gallery':           {'type': 'list',  'label': 'Galería'},
}
SURFACE_RE = re.compile(r'data-surface="([a-z]+)"')
LIST_VARIABLES = frozenset(name for name, spec in PATTERN_VARIABLES.items() if spec['type'] == 'list')

#Cantidad máxima de items por fragmento: el patrón nunca recibe más de lo
#que puede mostrar sin paginar.
FRAGMENT_LIMIT = 24

DAYS_ES = {
    'mon': 'Lun', 'tue': 'Mar', 'wed': 'Mié', 'thu': 'Jue',
    'fri': 'Vie', 'sat': 'Sáb', 'sun': 'Dom',
}

#=========================================
# HELPERS
#=========================================
def _text(value, limit = 0):
    text = strip_tags(str(value or '')).strip()
    return text[:limit] if limit else text

def _attr(value):
    return escape(str(value or ''))

def _amount(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

def _money(value):
    amount = int(round(_amount(value)))
    return '$' + f'{amount:,}'.replace(',', '.')

def _hours_text(customization):
    """
    "Lun a Vie 9 a 18 h · Sáb 9 a 13 h" a partir de `hours`
    ([{day, open, close, closed}]).
    """
    if customization is None or not customization.show_hours:
        return ''
    rows = customization.hours or []
    parts = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = DAYS_ES.get(str(row.get('day') or '').lower(), '')
        if not day:
            continue
        if row.get('closed'):
            parts.append(f'{day} cerrado')
            continue
        open_at = _text(row.get('open'), 5)
        close_at = _text(row.get('close'), 5)
        if open_at and close_at:
            parts.append(f'{day} {open_at} a {close_at}')
    return ' · '.join(parts[:7])

def _social_url(network, handle):
    handle = _text(handle, 60).lstrip('@')
    if not handle:
        return ''
    if network == 'instagram':
        return f'https://instagram.com/{handle}'
    if network == 'facebook':
        return f'https://facebook.com/{handle}'
    if network == 'tiktok':
        return f'https://tiktok.com/@{handle}'
    return ''

def _whatsapp_url(phone):
    digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
    return f'https://wa.me/{digits}' if digits else ''

#=========================================
# FRAGMENTOS (HTML generado acá, escapado)
#=========================================
def _product_fragment(store, products = None):
    from StoreApp.domains.catalog.models import Product
    from StoreApp.domains.stores.services.storage import object_url

    if products is None:
        products = (
            Product.objects.filter(store = store, is_active = True)
            .select_related('category', 'brand')
            .order_by('-created_at')[:FRAGMENT_LIMIT]
        )
    cards = []
    for product in products:
        image = object_url(product.image_key)
        amount = product.offer_price if product.offer_price is not None else product.price
        #Sin precio cargado la tarjeta no inventa un $0: manda a consultar.
        price = _money(amount) if _amount(amount) else 'Consultar'
        old = ''
        off = ''
        if product.offer_price is not None and _amount(product.price):
            old = f'<s class="ds-product-old">{_money(product.price)}</s>'
            #Porcentaje de ahorro para el badge del marketplace: solo el
            #número, la etiqueta la dibuja la hoja del diseño.
            off = str(max(1, min(99, int(round((1 - _amount(amount) / _amount(product.price)) * 100)))))
        media = (
            f'<img class="ds-product-img" src="{_attr(image)}" alt="{_attr(product.name)}" loading="lazy">'
            if image else '<span class="ds-product-img is-empty" aria-hidden="true"></span>'
        )
        category = _text(getattr(product.category, 'name', ''), 40)
        brand = _text(getattr(product.brand, 'name', ''), 40)
        off_attr = f' data-off="{off}"' if off else ''
        #Los datos de la tarjeta viajan como atributos: el catálogo del
        #diseño filtra y ordena en el navegador sin volver al servidor.
        cards.append(
            f'<article class="ds-product" data-cat="{_attr(category)}"'
            f' data-brand="{_attr(brand)}"'
            f' data-name="{_attr(product.name.lower())}"'
            f' data-price="{_attr(product.offer_price if product.offer_price is not None else product.price)}">'
            f'<a class="ds-product-link" href="#catalogo" data-ds-product="{product.pk}"'
            f' aria-label="{_attr(product.name)}">'
            f'{media}'
            '<span class="ds-product-copy">'
            f'<h3 class="ds-product-name">{escape(_text(product.name, 120))}</h3>'
            f'<small class="ds-product-desc">{escape(_text(product.description, 110))}</small>'
            '</span>'
            f'<span class="ds-product-cat">{escape(category)}</span>'
            f'<span class="ds-product-price"{off_attr}>'
            f'<span class="ds-product-amount">{price}</span>{old}</span>'
            '</a></article>'
        )
    if not cards:
        return (
            '<p class="ds-empty" role="status">Todavía no cargaste productos: '
            'agregalos desde el panel y aparecen acá.</p>'
        )
    return ''.join(cards)

def _category_fragment(store):
    from StoreApp.domains.catalog.models import Category

    rows = Category.objects.filter(store = store).order_by('position', 'name')[:FRAGMENT_LIMIT]
    links = [
        f'<a class="ds-cat" href="#catalogo"><span>{escape(_text(row.name, 60))}</span></a>'
        for row in rows
    ]
    return ''.join(links)

def _service_fragment(store):
    from StoreApp.domains.services.models import StoreService

    rows = StoreService.objects.filter(store = store, is_active = True).order_by('position', 'name')[:FRAGMENT_LIMIT]
    items = [
        '<li class="ds-service">'
        f'<strong class="ds-service-name">{escape(_text(row.name, 80))}</strong>'
        f'<span class="ds-service-desc">{escape(_text(getattr(row, "description", ""), 200))}</span>'
        '</li>'
        for row in rows
    ]
    return f'<ul class="ds-services-list">{"".join(items)}</ul>' if items else ''

def _gallery_fragment(store, customization):
    from StoreApp.domains.stores.models import StoreGalleryImage
    from StoreApp.domains.stores.services.storage import object_url

    if customization is not None and customization.show_gallery is False:
        return ''
    rows = store.gallery_images.all()[:FRAGMENT_LIMIT]
    shots = []
    for row in rows:
        if row.kind != StoreGalleryImage.KIND_GALLERY:
            continue
        url = object_url(row.image_key)
        if not url:
            continue
        alt = _text(getattr(row, 'alt', ''), 80)
        shots.append(
            f'<figure class="ds-shot"><img src="{_attr(url)}" alt="{_attr(alt)}" loading="lazy"></figure>'
        )
    return ''.join(shots)

def _features_fragment(product):
    """Filas `<tr>` de la ficha técnica: primero las del schema de su
    categoría, después las libres (mismo criterio que la vista Vue)."""
    features = product.features if isinstance(product.features, dict) else {}
    if not features:
        return ''
    schema = getattr(getattr(product, 'category', None), 'feature_schema', None) or []
    order = {str(name).lower(): i for i, name in enumerate(schema)}
    rows = sorted(
        features.items(),
        key = lambda item: (order.get(str(item[0]).lower(), len(schema)), str(item[0]).lower()),
    )
    return ''.join(
        f'<tr class="ds-pdp-spec"><th scope="row">{escape(_text(key, 60))}</th>'
        f'<td>{escape(_text(value, 200))}</td></tr>'
        for key, value in rows
    )

def _related_fragment(store, product):
    from StoreApp.domains.catalog.models import Product

    base = Product.objects.filter(store = store, is_active = True).exclude(pk = product.pk).select_related('category', 'brand')
    #Mismo criterio de sugerencia de un marketplace: categoría, marca y
    #después el resto, hasta 4 tarjetas.
    same_cat = list(base.filter(category_id = product.category_id)[:4]) if product.category_id else []
    same_brand = list(base.filter(brand_id = product.brand_id).exclude(pk__in = [p.pk for p in same_cat])[:4 - len(same_cat)]) if product.brand_id and len(same_cat) < 4 else []
    picked = same_cat + same_brand
    if len(picked) < 4:
        picked += list(base.exclude(pk__in = [p.pk for p in picked]).order_by('-created_at')[:4 - len(picked)])
    return _product_fragment(store, picked)

def _product_whatsapp_url(phone, product, store_name):
    from urllib.parse import quote

    digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
    if not digits:
        return ''
    amount = product.offer_price if product.offer_price is not None else product.price
    price = _money(amount) if _amount(amount) else ''
    text = f'Hola {store_name}, me interesa "{_text(product.name, 80)}"'
    if price:
        text += f' ({price})'
    text += ' que vi en tu catálogo.'
    return f'https://wa.me/{digits}?text={quote(text)}'

def _product_values(store, product, customization, store_name):
    """Variables `product_*` del documento (ficha de producto)."""
    from StoreApp.domains.stores.services.storage import object_url

    if product is None:
        return {name: '' for name in (
            'product_name', 'product_description', 'product_price', 'product_old_price',
            'product_offer_pct', 'product_image', 'product_category', 'product_brand',
            'product_ref', 'product_whatsapp_url',
        )}, {'product_features': '', 'product_related': ''}
    amount = product.offer_price if product.offer_price is not None else product.price
    old = ''
    pct = ''
    if product.offer_price is not None and _amount(product.price):
        old = _money(product.price)
        pct = f'-{max(1, min(99, int(round((1 - _amount(amount) / _amount(product.price)) * 100))))}%'
    phone = _text(getattr(customization, 'whatsapp', ''), 30)
    context = {
        'product_name':         _text(product.name, 120),
        'product_description':  _text(product.description, 600),
        'product_price':        _money(amount) if _amount(amount) else 'Consultar',
        'product_old_price':    old,
        'product_offer_pct':    pct,
        'product_image':        object_url(product.image_key) or '',
        'product_category':     _text(getattr(product.category, 'name', ''), 60),
        'product_brand':        _text(getattr(product.brand, 'name', ''), 60),
        'product_ref':          str(product.pk),
        'product_whatsapp_url': _product_whatsapp_url(phone, product, store_name),
    }
    raw = {
        'product_features': _features_fragment(product),
        'product_related':  _related_fragment(store, product),
    }
    return context, raw

#=========================================
# CONTEXTO DE LA TIENDA
#=========================================
def build_store_context(store, product = None):
    """
    Devuelve `(context, raw)`: `context` son las variables de texto que
    interpola el patrón y `raw` los fragmentos HTML ya escapados.
    """
    customization = getattr(store, 'customization', None)
    user = store.user
    name = _text(
        getattr(customization, 'display_name', '') or getattr(user, 'business_name', ''),
        60,
    )
    city = _text(getattr(getattr(user, 'city', None), 'name_city', ''), 60)
    province = _text(getattr(getattr(user, 'province', None), 'name_province', ''), 60)
    location = ', '.join(part for part in (city, province) if part)
    address = _text(getattr(user, 'address', ''), 160) if customization and customization.show_location else ''
    phone = _text(getattr(customization, 'whatsapp', ''), 30)
    description = _text(getattr(customization, 'description', ''), 400)
    headline = _text(getattr(customization, 'headline', ''), 140)
    about = _text(getattr(customization, 'about_text', ''), 400)
    from django.utils import timezone

    context = {
        'store_name': name,
        'store_initial': name[:1].upper(),
        'store_tagline': headline or description,
        'store_description': description,
        'store_about': about,
        'store_location': location,
        'store_address': address,
        'store_phone': phone,
        'store_whatsapp_url': _whatsapp_url(phone),
        'store_email': _text(getattr(customization, 'contact_email', ''), 120),
        'store_hours': _hours_text(customization),
        'store_instagram_url': _social_url('instagram', getattr(customization, 'instagram', '')),
        'store_facebook_url': _social_url('facebook', getattr(customization, 'facebook', '')),
        'store_tiktok_url': _social_url('tiktok', getattr(customization, 'tiktok', '')),
        'store_logo': '',
        'store_cover': '',
        'store_accent': '',
        'year': str(timezone.now().year),
    }
    from StoreApp.domains.stores.services.storage import object_url

    if customization is not None:
        context['store_logo'] = object_url(customization.logo_key) or ''
        context['store_cover'] = object_url(customization.cover_key) or ''
        context['store_accent'] = _text(customization.accent_custom, 7) or ''
    raw = {
        'products': _product_fragment(store),
        'categories': _category_fragment(store),
        'services': _service_fragment(store),
        'gallery': _gallery_fragment(store, customization),
    }
    product_ctx, product_raw = _product_values(store, product, customization, name)
    context.update(product_ctx)
    raw.update(product_raw)
    return context, raw

#=========================================
# TEMA DEL ESTILO (custom properties)
#=========================================
RADIUS_MAP = {'none': '0', 'sm': '4px', 'md': '8px', 'lg': '14px', 'xl': '22px', 'pill': '999px'}
SHADOW_MAP = {
    'none': 'none',
    'soft': '0 1px 2px rgba(0,0,0,.06)',
    'medium': '0 6px 18px rgba(0,0,0,.10)',
    'strong': '0 16px 40px rgba(0,0,0,.18)',
}
SPACE_MAP = {'compact': '.75', 'normal': '1', 'spacious': '1.25'}
BUTTON_MAP = {'square': '0', 'rounded': '8px', 'pill': '999px'}
DIVIDER_MAP = {'none': 'transparent', 'line': 'currentColor', 'dots': 'currentColor'}


def _contrast_ink(value):
    """
    Texto legible sobre un color de acento: oscuro en acentos claros,
    claro en acentos oscuros. Evita un botón amarillo con texto blanco.
    """
    match = re.fullmatch(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})', str(value or '').strip())
    if not match:
        return ''
    digits = match.group(1)
    if len(digits) == 3:
        digits = ''.join(ch * 2 for ch in digits)
    r, g, b = (int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    #Umbral AA real para texto blanco (ratio 4.5): L = 0.1833. Con 0.42
    #quedaban acentos medios (p. ej. #3483FA) con blanco a 3.6:1.
    return '#191611' if luminance > 0.1833 else '#FFFDF8'


def theme_css(customization, pattern = None):
    """
    Bloque `:root { --ds-* }` con lo que el estilo puede tocar. Los
    `effects` del estilo ya vienen saneados por `clean_style_effects`; acá
    solo se traducen a custom properties.
    """
    style = None
    palette = {}
    if customization is not None:
        site_theme = customization.site_theme if isinstance(customization.site_theme, dict) else {}
        style = site_theme.get('style')
        if isinstance(site_theme.get('palette'), dict):
            palette = site_theme['palette']
    effects = {}
    if isinstance(style, dict) and isinstance(style.get('effects'), dict):
        effects = style['effects']
    tokens = pattern.tokens if pattern is not None and isinstance(pattern.tokens, dict) else {}
    #El acento del panel de Diseño manda sobre el del estilo y el del patrón.
    color = (
        _text(getattr(customization, 'accent_custom', ''), 7)
        or _text(palette.get('accent'), 7)
        or tokens.get('accent')
        or effects.get('accent')
        or ''
    )
    vars_ = {
        '--ds-radius': RADIUS_MAP.get(effects.get('radius', ''), ''),
        '--ds-radius-btn': BUTTON_MAP.get(effects.get('button_shape', ''), ''),
        '--ds-shadow': SHADOW_MAP.get(effects.get('shadow', ''), ''),
        '--ds-space': SPACE_MAP.get(effects.get('space', ''), ''),
        '--ds-border-width': str(effects.get('border_width')) + 'px' if isinstance(effects.get('border_width'), int) else '',
        '--ds-border-style': effects.get('border_style', ''),
        '--ds-divider': DIVIDER_MAP.get(effects.get('divider', ''), ''),
        '--ds-accent': color if str(color).startswith('#') else '',
        '--ds-accent-ink': _contrast_ink(color),
    }
    #Superficies, bordes y texto del tema aplicado: la paleta del panel de
    #Diseño manda sobre los effects del estilo. Sin paleta, la hoja del
    #diseño usa su propia piel (fallback en CSS).
    for key in ('primary', 'secondary', 'bg', 'surface', 'text', 'muted', 'border', 'success', 'danger'):
        value = _text(palette.get(key), 7) or _text(effects.get(key), 7)
        if value.startswith('#'):
            vars_[f'--ds-{key}'] = value
    #Texto legible sobre cada relleno de marca (mismo criterio que --st-*).
    for key in ('primary', 'secondary', 'success'):
        fill = vars_.get(f'--ds-{key}')
        if fill:
            vars_[f'--ds-{key}-ink'] = _contrast_ink(fill)
    body = ''.join(f'{name}:{value};' for name, value in vars_.items() if value)
    return f':root{{{body}}}' if body else ''

#=========================================
# RESOLUCION DEL PATRON DE UNA TIENDA
#=========================================
def pattern_for_template(template):
    """
    Patrón activo de un diseño: primero el que tiene el slug de la
    plantilla, después el primero que la declara en `template`, y por
    último el predeterminado del catálogo.
    """
    template = str(template or '').strip()
    if template:
        own = DesignPattern.objects.filter(slug = template, is_active = True).first()
        if own is not None:
            return own
        by_template = (
            DesignPattern.objects.filter(template = template, is_active = True)
            .order_by('position', 'id').first()
        )
        if by_template is not None:
            return by_template
    return DesignPattern.objects.filter(is_default = True, is_active = True).first()

def render_store_pattern(store, customization = None, product = None):
    """
    Documento del patrón resuelto contra la tienda:
    `{slug, nombre, html, css, js, dark}`. `None` si el diseño no trae
    markup (la web sigue con la plantilla Vue). Con `product` resuelve
    además las variables `product_*` (ficha del diseño).
    """
    customization = customization if customization is not None else getattr(store, 'customization', None)
    template = getattr(customization, 'template', '') if customization is not None else ''
    pattern = pattern_for_template(template)
    if pattern is None or not (pattern.html or '').strip():
        return None
    context, raw = build_store_context(store, product)
    html = pattern.render(context, raw = raw)
    from StoreApp.domains.catalog.models import Product

    site_theme = customization.site_theme if customization is not None and isinstance(customization.site_theme, dict) else {}
    style = site_theme.get('style') if isinstance(site_theme.get('style'), dict) else {}
    return {
        'slug': pattern.slug,
        'nombre': pattern.nombre,
        #Estilo elegido (DesignStyle.slug): el documento lo expone como
        #`data-ds-style` para que la piel y los menús móviles varíen por estilo.
        'style': str(style.get('id') or (pattern.style.slug if pattern.style_id else '')),
        #Un patrón sin variables declaradas todavía es demo estático: la
        #web publicada sigue con la plantilla Vue hasta convertirlo.
        'ready': bool(pattern.variables),
        #Superficies que el documento sabe pintar (`data-surface`): el host
        #solo usa el patrón en las rutas que el diseño cubre.
        'surfaces': sorted(set(SURFACE_RE.findall(html))),
        #El catálogo del diseño trae los productos ya renderizados: si la
        #tienda tiene más de los que entran en el documento, esa ruta sigue
        #con la plantilla Vue (que pagina) para no esconder productos.
        'products_total': Product.objects.filter(store = store, is_active = True).count(),
        'products_shown': FRAGMENT_LIMIT,
        'html': html,
        'css': f'{theme_css(customization, pattern)}\n{pattern.css or ""}',
        'js': pattern.js or '',
        'dark': bool(pattern.supports_dark_mode),
    }
