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
    'products':          {'type': 'list',  'label': 'Productos'},
    'categories':        {'type': 'list',  'label': 'Categorías'},
    'services':          {'type': 'list',  'label': 'Servicios'},
    'gallery':           {'type': 'list',  'label': 'Galería'},
}
LIST_VARIABLES = frozenset(name for name, spec in PATTERN_VARIABLES.items() if spec['type'] == 'list')

#Cantidad máxima de items por fragmento: el patrón nunca recibe más de lo
#que puede mostrar sin paginar.
FRAGMENT_LIMIT = 12

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

def _money(value):
    try:
        amount = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return ''
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
def _product_fragment(store):
    from StoreApp.domains.catalog.models import Product
    from StoreApp.domains.stores.services.storage import object_url

    products = (
        Product.objects.filter(store = store, is_active = True)
        .select_related('category')
        .order_by('-created_at')[:FRAGMENT_LIMIT]
    )
    cards = []
    for product in products:
        image = object_url(product.image_key)
        price = _money(product.offer_price if product.offer_price is not None else product.price)
        old = ''
        if product.offer_price is not None and product.price:
            old = f'<s class="ds-product-old">{_money(product.price)}</s>'
        media = (
            f'<img class="ds-product-img" src="{_attr(image)}" alt="{_attr(product.name)}" loading="lazy">'
            if image else '<span class="ds-product-img is-empty" aria-hidden="true"></span>'
        )
        category = _text(getattr(product.category, 'name', ''), 40)
        cards.append(
            '<article class="ds-product">'
            f'<a class="ds-product-link" href="#catalogo" aria-label="{_attr(product.name)}">'
            f'{media}'
            '<span class="ds-product-copy">'
            f'<h3 class="ds-product-name">{escape(_text(product.name, 120))}</h3>'
            f'<small class="ds-product-desc">{escape(_text(product.description, 110))}</small>'
            '</span>'
            f'<span class="ds-product-cat">{escape(category)}</span>'
            f'<span class="ds-product-price">{price}{old}</span>'
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

#=========================================
# CONTEXTO DE LA TIENDA
#=========================================
def build_store_context(store):
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


def theme_css(customization, pattern = None):
    """
    Bloque `:root { --ds-* }` con lo que el estilo puede tocar. Los
    `effects` del estilo ya vienen saneados por `clean_style_effects`; acá
    solo se traducen a custom properties.
    """
    style = None
    if customization is not None:
        style = customization.site_theme.get('style') if isinstance(customization.site_theme, dict) else None
    effects = {}
    if isinstance(style, dict) and isinstance(style.get('effects'), dict):
        effects = style['effects']
    tokens = pattern.tokens if pattern is not None and isinstance(pattern.tokens, dict) else {}
    color = _text(getattr(customization, 'accent_custom', ''), 7) or tokens.get('accent') or effects.get('accent') or ''
    vars_ = {
        '--ds-radius': RADIUS_MAP.get(effects.get('radius', ''), ''),
        '--ds-radius-btn': BUTTON_MAP.get(effects.get('button_shape', ''), ''),
        '--ds-shadow': SHADOW_MAP.get(effects.get('shadow', ''), ''),
        '--ds-space': SPACE_MAP.get(effects.get('space', ''), ''),
        '--ds-border-width': str(effects.get('border_width')) + 'px' if isinstance(effects.get('border_width'), int) else '',
        '--ds-border-style': effects.get('border_style', ''),
        '--ds-divider': DIVIDER_MAP.get(effects.get('divider', ''), ''),
        '--ds-accent': color if str(color).startswith('#') else '',
    }
    for key in ('primary', 'secondary', 'bg', 'surface', 'text', 'muted', 'border', 'success', 'danger'):
        value = effects.get(key)
        if isinstance(value, str) and value.startswith('#'):
            vars_[f'--ds-{key}'] = value
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

def render_store_pattern(store, customization = None):
    """
    Documento del patrón resuelto contra la tienda:
    `{slug, nombre, html, css, js, dark}`. `None` si el diseño no trae
    markup (la web sigue con la plantilla Vue).
    """
    customization = customization if customization is not None else getattr(store, 'customization', None)
    template = getattr(customization, 'template', '') if customization is not None else ''
    pattern = pattern_for_template(template)
    if pattern is None or not (pattern.html or '').strip():
        return None
    context, raw = build_store_context(store)
    return {
        'slug': pattern.slug,
        'nombre': pattern.nombre,
        #Un patrón sin variables declaradas todavía es demo estático: la
        #web publicada sigue con la plantilla Vue hasta convertirlo.
        'ready': bool(pattern.variables),
        'html': pattern.render(context, raw = raw),
        'css': f'{theme_css(customization, pattern)}\n{pattern.css or ""}',
        'js': pattern.js or '',
        'dark': bool(pattern.supports_dark_mode),
    }
