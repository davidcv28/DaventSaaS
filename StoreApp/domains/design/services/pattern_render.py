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

#Placeholders `{{variable}}` del markup: se usan para armar solo los
#fragmentos que el patrón consume de verdad (categorías, galería, FAQ…
#quedaban fuera del render aunque el diseño no los tuviera).
VAR_RE = re.compile(r'{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}')

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
    'store_about_title': {'type': 'text',  'label': 'Sobre nosotros: título'},
    'store_about_years': {'type': 'text',  'label': 'Años de trayectoria'},
    'store_about_mission': {'type': 'text', 'label': 'Misión'},
    'store_about_specialties': {'type': 'text', 'label': 'Especialidades'},
    'store_location':    {'type': 'text',  'label': 'Ciudad y provincia'},
    'store_address':     {'type': 'text',  'label': 'Dirección'},
    'store_phone':       {'type': 'text',  'label': 'Teléfono / WhatsApp'},
    'store_whatsapp_url': {'type': 'text', 'label': 'Link de WhatsApp'},
    'store_email':       {'type': 'text',  'label': 'Email de contacto'},
    'store_hours':       {'type': 'text',  'label': 'Horarios'},
    'store_instagram_url': {'type': 'text', 'label': 'Instagram'},
    'store_facebook_url': {'type': 'text', 'label': 'Facebook'},
    'store_tiktok_url':  {'type': 'text',  'label': 'TikTok'},
    'store_maps_url':    {'type': 'text',  'label': 'Link al mapa'},
    'contact_form':      {'type': 'list',  'label': 'Formulario de contacto'},
    'store_logo':        {'type': 'image', 'label': 'Logo'},
    'store_cover':       {'type': 'image', 'label': 'Portada'},
    'store_accent':      {'type': 'color', 'label': 'Color de acento'},
    'year':              {'type': 'number', 'label': 'Año'},
    'product_name':      {'type': 'text',  'label': 'Producto: nombre'},
    'product_description': {'type': 'text', 'label': 'Producto: descripción'},
    'product_price':     {'type': 'text',  'label': 'Producto: precio'},
    'product_old_price': {'type': 'text',  'label': 'Producto: precio antes de la oferta'},
    'product_offer_pct': {'type': 'text',  'label': 'Producto: % de ahorro'},
    'product_save':      {'type': 'text',  'label': 'Producto: ahorro'},
    'product_campaign_label': {'type': 'list', 'label': 'Producto: etiqueta de campaña'},
    'product_image':     {'type': 'image', 'label': 'Producto: imagen'},
    'product_category':  {'type': 'text',  'label': 'Producto: categoría'},
    'product_brand':     {'type': 'text',  'label': 'Producto: marca'},
    'product_ref':       {'type': 'text',  'label': 'Producto: referencia'},
    'product_whatsapp_url': {'type': 'text', 'label': 'Producto: consulta por WhatsApp'},
    'product_rating_avg':{'type': 'text',  'label': 'Producto: valoración promedio'},
    'product_rating_count': {'type': 'text', 'label': 'Producto: cantidad de valoraciones'},
    'product_features':  {'type': 'list',  'label': 'Producto: características'},
    'product_related':   {'type': 'list',  'label': 'Producto: relacionados'},
    'product_reviews':   {'type': 'list',  'label': 'Producto: opiniones'},
    'products':          {'type': 'list',  'label': 'Productos'},
    'categories':        {'type': 'list',  'label': 'Categorías'},
    'services':          {'type': 'list',  'label': 'Servicios'},
    'offerings':         {'type': 'list',  'label': 'Qué ofrecemos'},
    'offerings_title':   {'type': 'text',  'label': 'Título de Qué ofrecemos'},
    'stats':             {'type': 'list',  'label': 'Números del negocio'},
    'testimonials':      {'type': 'list',  'label': 'Testimonios'},
    'testimonials_title': {'type': 'text', 'label': 'Título de Testimonios'},
    'faqs':              {'type': 'list',  'label': 'Preguntas frecuentes'},
    'faqs_title':        {'type': 'text',  'label': 'Título de Preguntas frecuentes'},
    'benefits':          {'type': 'list',  'label': 'Garantías y beneficios'},
    'timeline':          {'type': 'list',  'label': 'Hitos del negocio'},
    'team':              {'type': 'list',  'label': 'Equipo'},
    'announcements':     {'type': 'list',  'label': 'Cinta de anuncios'},
    'video_url':         {'type': 'text',  'label': 'Video (URL)'},
    'video_title':       {'type': 'text',  'label': 'Título de la sección Video'},
    'videos':            {'type': 'list',  'label': 'Videos de redes'},
    'live_stream_url':   {'type': 'text',  'label': 'Transmisión en vivo (URL)'},
    'cta_title':         {'type': 'text',  'label': 'Título del llamado a la acción'},
    'cta_text':          {'type': 'text',  'label': 'Texto del llamado a la acción'},
    'cta_label':         {'type': 'text',  'label': 'Botón del llamado a la acción'},
    'footer_text':       {'type': 'text',  'label': 'Texto del pie'},
    'plans':             {'type': 'list',  'label': 'Planes de suscripción'},
    'plans_title':       {'type': 'text',  'label': 'Título de la sección Planes'},
    'gallery':           {'type': 'list',  'label': 'Galería'},
    'carousel':          {'type': 'list',  'label': 'Carrusel de portada'},
    'decor':             {'type': 'list',  'label': 'Imágenes decorativas'},
    'brands':            {'type': 'list',  'label': 'Marcas'},
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

def _contact_link(store, customization, kind, field, text = ''):
    """
    Path del redirect público (/api/stores/public/<slug>/r/<kind>/): el
    documento enlaza ahí y el dato real (número/usuario) nunca aparece en
    el HTML servido — anti-scraping de contactos.
    """
    from StoreApp.domains.stores.services import contact_redirect_path

    if not str(getattr(customization, field, '') or '').strip():
        return ''
    return contact_redirect_path(store, kind, text)

#=========================================
# FRAGMENTOS (HTML generado acá, escapado)
#=========================================
def _page_flags(store, customization):
    """
    Interruptores por sección/página del diseño: el `show_*` del dueño Y
    el `site_templates` efectivo (guardado ∩ plan). El documento los
    respeta dos veces: el fragmento sale vacío y, si el patrón marca la
    zona con `data-flag="<nombre>"`, la regla `[data-flag]{display:none}`
    la apaga entera (título, CTA y enlaces del menú incluidos).
    """
    from StoreApp.domains.services.services import effective_site_templates

    pages = set(effective_site_templates(store))
    def on(name, default = True):
        return bool(getattr(customization, name, default))
    catalog_on = 'catalog' in pages and on('show_catalog')
    return {
        'catalog':  catalog_on,
        #Bloques de landing que viven del catálogo: apagar la página también
        #apaga sus zonas; el bloque individual las apaga vía _BLOCK_FLAGS.
        'categories': catalog_on,
        'featured':   catalog_on,
        #Bloques de landing sin show_* propio: solo los apaga "Qué mostrar".
        'steps':      True,
        'compare':    True,
        'services': 'services' in pages and on('show_services'),
        'plans':    'plans' in pages and on('show_plans'),
        'contact':  on('show_contact'),
        'gallery':  on('show_gallery'),
        #Interruptores finos del dueño: el documento apaga las zonas que el
        #diseño marque `data-flag="<nombre>"` cuando el show_* está off, así
        #la vista previa y la web no pintan cáscaras de secciones quitadas.
        'hours':        on('show_hours'),
        'benefits':     on('show_benefits'),
        'highlights':   on('show_highlights'),
        'stats':        on('show_stats'),
        'testimonials': on('show_testimonials'),
        'faq':          on('show_faq'),
        'timeline':     on('show_timeline'),
        'team':         on('show_team'),
        'cta':          on('show_cta'),
        'announcements': on('show_announcements'),
        'video':        on('show_video'),
        'about':        on('show_about'),
        'location':     on('show_location'),
        'offers':       on('show_offers'),
        'brands':       on('show_brands'),
        'countdown':    on('show_countdown'),
        'reviews':      on('show_reviews', False),
        'comments':     on('show_comments', False),
    }

#Bloques de "Qué mostrar" (layout_config) que comparten nombre con las
#zonas `data-flag` del documento: apagarlos apaga la zona igual que el
#show_*. 'catalog' y 'services' quedan fuera a propósito: son páginas
#(site_templates) y sus bloques de inicio comparten el flag con la
#superficie entera — un toggle de sección no puede apagar la página.
_BLOCK_FLAGS = frozenset({
    'about', 'announcements', 'benefits', 'brands', 'categories', 'compare',
    'contact', 'countdown', 'cta', 'faq', 'featured', 'gallery', 'highlights',
    'offers', 'plans', 'stats', 'steps', 'team', 'testimonials', 'timeline',
    'video',
})

def _zone_flags(flags, customization):
    """
    Flags de zona = flags de página ∪ bloques apagados en "Qué mostrar"
    (layout_config: {superficie: {blocks: [{id, enabled:false}]}}). El
    filtro de superficies sigue usando los flags de página: un bloque
    apagado oculta sus zonas `data-flag` pero nunca quita una página.
    """
    layout = getattr(customization, 'layout_config', None) if customization is not None else None
    if not isinstance(layout, dict):
        return flags
    off = set()
    for surface in layout.values():
        blocks = surface.get('blocks') if isinstance(surface, dict) else None
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if isinstance(block, dict) and block.get('enabled') is False:
                off.add(str(block.get('id') or ''))
    off &= _BLOCK_FLAGS
    if not off:
        return flags
    return {name: enabled and name not in off for name, enabled in flags.items()}

def _product_fragment(store, products = None, flags = None):
    from StoreApp.domains.catalog.models import Product
    from StoreApp.domains.stores.services.storage import object_url

    if flags is None:
        flags = _page_flags(store, getattr(store, 'customization', None))
    if not flags.get('catalog', True):
        return ''
    if products is None:
        products = (
            Product.objects.filter(store = store, is_active = True)
            .select_related('category', 'brand')
            .order_by('-created_at')[:FRAGMENT_LIMIT]
        )
    from StoreApp.domains.catalog.services.services import (
        effective_pricing_of,
        running_discounts_of,
    )
    discounts = running_discounts_of(store)
    cards = []
    for product in products:
        image = object_url(product.image_key)
        effective_offer, effective_discount = effective_pricing_of(product, discounts)
        amount = effective_offer if effective_offer is not None else product.price
        #Sin precio cargado la tarjeta no inventa un $0: manda a consultar.
        price = _money(amount) if _amount(amount) else 'Consultar'
        old = ''
        off = ''
        if effective_offer is not None and _amount(product.price):
            old = f'<s class="ds-product-old">{_money(product.price)}</s>'
            #Porcentaje de ahorro para el badge del marketplace: solo el
            #número, la etiqueta la dibuja la hoja del diseño.
            off = str(max(1, min(99, int(round((1 - _amount(amount) / _amount(product.price)) * 100)))))
        #Etiqueta de campaña del descuento que firma la oferta (máx. 1 por
        #tarjeta): la URL y el alt viajan en data-attrs para que el documento
        #la pinte sin pedir nada — el <img> ya trae width/height (sin CLS).
        campaign = getattr(effective_discount, 'campaign', None)
        campaign_attr = ''
        campaign_img = ''
        if campaign is not None:
            label_url = object_url(campaign.label_key, private = True)
            if label_url:
                campaign_attr = f' data-campaign-label="{_attr(label_url)}"'
                campaign_img = (
                    f'<img class="ds-campaign-label" src="{_attr(label_url)}"'
                    f' width="{campaign.label_width or 90}" height="{campaign.label_height or 24}"'
                    f' alt="{_attr(campaign.label_alt or campaign.name)}" loading="lazy" decoding="async">'
                )
        media = (
            f'<img class="ds-product-img" src="{_attr(image)}" alt="{_attr(product.name)}" loading="lazy" decoding="async">'
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
            #Todo producto publicado está en stock: el sistema no maneja
            #inventario, así que el tag va siempre.
            '<span class="ds-stock"><i aria-hidden="true"></i>En stock</span>'
            f'<span class="ds-product-price"{off_attr}{campaign_attr}>'
            f'{campaign_img}<span class="ds-product-amount">{price}</span>{old}</span>'
            '</a></article>'
        )
    if not cards:
        return (
            '<p class="ds-empty" role="status">Todavía no cargaste productos: '
            'agregalos desde el panel y aparecen acá.</p>'
        )
    return ''.join(cards)

def _category_fragment(store, flags = None):
    from StoreApp.domains.catalog.models import Category

    if flags is None:
        flags = _page_flags(store, getattr(store, 'customization', None))
    if not flags.get('catalog', True):
        return ''
    rows = Category.objects.filter(store = store).order_by('position', 'name')[:FRAGMENT_LIMIT]
    links = [
        f'<a class="ds-cat" href="#catalogo"><span>{escape(_text(row.name, 60))}</span></a>'
        for row in rows
    ]
    return ''.join(links)

def _service_fragment(store, flags = None):
    from StoreApp.domains.services.models import StoreService

    if flags is None:
        flags = _page_flags(store, getattr(store, 'customization', None))
    if not flags.get('services', True):
        return ''
    rows = StoreService.objects.filter(store = store, is_active = True).order_by('position', 'name')[:FRAGMENT_LIMIT]
    items = []
    for row in rows:
        #Precio/duración/icono viajan como data-attrs: los patrones que no
        #los usan no cambian nada; el que sí (p. ej. silicio) arma su propia
        #tarjeta interactiva sin pedir endpoints extra.
        price_num = ''
        price_label = 'A convenir'
        if row.price is not None and _amount(row.price):
            price_num = str(row.price)
            price_label = _money(row.price)
        items.append(
            '<li class="ds-service"'
            f' data-price="{_attr(price_num)}"'
            f' data-price-label="{_attr(price_label)}"'
            f' data-duration="{_attr(_text(getattr(row, "duration", ""), 40))}"'
            f' data-icon="{_attr(_text(getattr(row, "icon", ""), 30))}"'
            f' data-icon-svg="{_attr(_icon_svg(getattr(row, "icon", "")))}">'
            f'<strong class="ds-service-name">{escape(_text(row.name, 80))}</strong>'
            f'<span class="ds-service-desc">{escape(_text(getattr(row, "description", ""), 200))}</span>'
            '</li>'
        )
    return f'<ul class="ds-services-list">{"".join(items)}</ul>' if items else ''

def _plans_fragment(store, customization, flags = None):
    """Tarjetas de membresías/packs del negocio (customization.plans):
    solo publicidad — el alta se coordina por WhatsApp, nunca se cobra
    online. Vacío cuando la sección está apagada, la página Suscripciones
    salió de site_templates o no hay planes."""
    if customization is None or not customization.show_plans:
        return ''
    if flags is None:
        flags = _page_flags(store, customization)
    if not flags.get('plans', True):
        return ''
    cards = []
    for plan in customization.plans or []:
        if not isinstance(plan, dict) or not _text(plan.get('name')):
            continue
        feats = ''.join(
            f'<li>{escape(_text(item, 60))}</li>'
            for item in (plan.get('items') or [])[:8]
        )
        feat_list = f'<ul class="ds-plan-feats">{feats}</ul>' if feats else ''
        cards.append(
            '<article class="ds-plan">'
            f'<h3 class="ds-plan-name">{escape(_text(plan.get("name"), 40))}</h3>'
            f'<span class="ds-plan-price">{escape(_text(plan.get("price"), 20))}</span>'
            f'<p class="ds-plan-note">{escape(_text(plan.get("note"), 80))}</p>'
            f'{feat_list}'
            '</article>'
        )
    return ''.join(cards)

#Iconos del panel (mismos ids que SERVICE_ICONS del front): paths lucide
#24×24 trazo, `currentColor`. El patrón los envuelve en su propia marca.
_ICON_PATHS = {
    'package':        '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    'truck':          '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18h-5"/><path d="M15 8h4l4 4v4a1 1 0 0 1-1 1h-1"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    'wrench':         '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    'tag':            '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42Z"/><circle cx="7.5" cy="7.5" r="1"/>',
    'percent':        '<line x1="19" x2="5" y1="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    'gift':           '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5A4.8 8 0 0 1 12 8a4.8 8 0 0 1 4.5-5 2.5 2.5 0 0 1 0 5"/>',
    'star':           '<path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/>',
    'zap':            '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
    'shield-check':   '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    'clock':          '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    'map-pin':        '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    'users':          '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'phone':          '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    'message-circle': '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    'store':          '<path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4"/><path d="M2 7h20"/><path d="M22 7v3a2 2 0 0 1-2 2 2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 16 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 12 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 8 12a2.7 2.7 0 0 1-1.59-.63.7.7 0 0 0-.82 0A2.7 2.7 0 0 1 4 12a2 2 0 0 1-2-2V7"/>',
    'credit-card':    '<rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>',
    'wallet':         '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
    'crown':          '<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>',
    'badge-check':    '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>',
    'trending-up':    '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    'calendar':       '<path d="M8 2v4"/><path d="M16 2v4"/><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18"/>',
    'flame':          '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    'megaphone':      '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
    'sparkles':       '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    'award':          '<circle cx="12" cy="8" r="6"/><path d="M15.5 13 17 22l-5-3-5 3 1.5-9"/>',
    'check':          '<path d="M20 6 9 17l-5-5"/>',
    'heart':          '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    'leaf':           '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    'camera':         '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/>',
    'book':           '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    'music':          '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    'graduation-cap': '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',
    'dumbbell':       '<path d="M14.4 14.4 9.6 9.6"/><path d="M18.657 21.485a2 2 0 1 1-2.829-2.828l-1.767 1.768a2 2 0 1 1-2.829-2.829l6.364-6.364a2 2 0 1 1 2.829 2.828l-1.768 1.768a2 2 0 1 1 2.829 2.829Z"/><path d="m21.5 21.5-1.4-1.4"/><path d="M3.9 3.9 2.5 2.5"/><path d="M6.404 12.768a2 2 0 1 1-2.829-2.829l1.768-1.767a2 2 0 1 1-2.828-2.829l2.828-2.828a2 2 0 1 1 2.829 2.828l1.767-1.768a2 2 0 1 1 2.829 2.829Z"/>',
    'paw-print':      '<circle cx="11" cy="4" r="2"/><circle cx="18" cy="8" r="2"/><circle cx="20" cy="16" r="2"/><path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10Z"/>',
    'scissors':       '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88"/><path d="M14.47 14.48 20 20"/><path d="M8.12 8.12 12 12"/>',
    'coffee':         '<path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><path d="M6 2v2"/><path d="M10 2v2"/><path d="M14 2v2"/>',
    'umbrella':       '<path d="M22 12a10.06 10.06 0 0 0-20 0Z"/><path d="M12 12v8a2 2 0 0 0 4 0"/><path d="M12 2v1"/>',
    'hard-hat':       '<path d="M2 18a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1z"/><path d="M10 5V3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2"/><path d="M4 15v-3a6 6 0 0 1 6-6"/><path d="M14 6a6 6 0 0 1 6 6v3"/>',
    'film':           '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18"/><path d="M17 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
    'flower':         '<circle cx="12" cy="12" r="3"/><path d="M12 16.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 1 1 4.5 4.5 4.5 4.5 0 1 1-4.5 4.5"/><path d="M12 7.5V9"/><path d="M7.5 12H9"/><path d="M16.5 12H15"/><path d="M12 16.5V15"/>',
    'hand':           '<path d="M18 11V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2"/><path d="M14 10V4a2 2 0 0 0-2-2 2 2 0 0 0-2 2v2"/><path d="M10 10.5V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>',
}

def _icon_svg(name):
    key = str(name or '').strip()
    return (
        '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'{_ICON_PATHS.get(key, _ICON_PATHS["check"])}</svg>'
    )

def _rows(value):
    return [row for row in (value or []) if isinstance(row, dict)]

def _offerings_fragment(customization, flags):
    if customization is None or not flags.get('services', True):
        return ''
    cards = []
    for row in _rows(customization.services):
        title = _text(row.get('title'), 60)
        if not title:
            continue
        cards.append(
            '<article class="ds-offer">'
            f'<span class="ds-offer-icon">{_icon_svg(row.get("icon"))}</span>'
            f'<h3 class="ds-offer-name">{escape(title)}</h3>'
            f'<p class="ds-offer-text">{escape(_text(row.get("text"), 160))}</p>'
            '</article>'
        )
    return ''.join(cards)

def _stats_fragment(customization, flags):
    if customization is None or not flags.get('stats', True):
        return ''
    cards = []
    for row in _rows(customization.stats):
        value = _text(row.get('value'), 20)
        label = _text(row.get('label'), 60)
        if not (value or label):
            continue
        cards.append(
            '<article class="ds-stat">'
            f'<b class="ds-stat-value">{escape(value)}</b>'
            f'<span class="ds-stat-label">{escape(label)}</span>'
            '</article>'
        )
    return ''.join(cards)

def _testimonials_fragment(customization, flags):
    if customization is None or not flags.get('testimonials', True):
        return ''
    cards = []
    for row in _rows(customization.testimonials):
        text = _text(row.get('text'), 300)
        if not text:
            continue
        name = _text(row.get('name'), 60)
        cards.append(
            '<figure class="ds-quote">'
            f'<blockquote class="ds-quote-text">{escape(text)}</blockquote>'
            f'<figcaption class="ds-quote-name">{escape(name)}</figcaption>'
            '</figure>'
        )
    return ''.join(cards)

def _faqs_fragment(customization, flags):
    if customization is None or not flags.get('faq', True):
        return ''
    items = []
    for row in _rows(customization.faqs):
        q = _text(row.get('q'), 160)
        a = _text(row.get('a'), 600)
        if not q:
            continue
        items.append(
            '<details class="ds-faq">'
            f'<summary class="ds-faq-q">{escape(q)}</summary>'
            f'<p class="ds-faq-a">{escape(a)}</p>'
            '</details>'
        )
    return ''.join(items)

def _benefits_fragment(customization, flags):
    if customization is None or not flags.get('benefits', True):
        return ''
    cards = []
    for row in _rows(customization.benefits):
        title = _text(row.get('title'), 40)
        if not title:
            continue
        cards.append(
            '<article class="ds-guar">'
            f'<span class="ds-guar-icon">{_icon_svg(row.get("icon"))}</span>'
            f'<span class="ds-guar-copy"><b>{escape(title)}</b>'
            f'<span>{escape(_text(row.get("text"), 90))}</span></span>'
            '</article>'
        )
    return ''.join(cards)

def _timeline_fragment(customization, flags):
    if customization is None or not flags.get('timeline', True):
        return ''
    items = []
    for row in _rows(customization.timeline):
        label = _text(row.get('label'), 24)
        text = _text(row.get('text'), 160)
        if not (label or text):
            continue
        items.append(
            '<li class="ds-mile">'
            f'<b class="ds-mile-label">{escape(label)}</b>'
            f'<span class="ds-mile-text">{escape(text)}</span>'
            '</li>'
        )
    return f'<ol class="ds-miles">{"".join(items)}</ol>' if items else ''

def _team_fragment(customization, flags):
    if customization is None or not flags.get('team', True):
        return ''
    cards = []
    for row in _rows(customization.team):
        name = _text(row.get('name'), 60)
        if not name:
            continue
        initials = ''.join(part[0] for part in name.split()[:2]).upper()
        cards.append(
            '<article class="ds-mate">'
            f'<span class="ds-mate-mark" aria-hidden="true">{escape(initials)}</span>'
            f'<b class="ds-mate-name">{escape(name)}</b>'
            f'<span class="ds-mate-role">{escape(_text(row.get("role"), 60))}</span>'
            '</article>'
        )
    return ''.join(cards)

def _announcements_fragment(customization, flags):
    """Spans de la cinta: el patrón duplica el track para el marquee."""
    if customization is None or not flags.get('announcements', True):
        return ''
    notes = []
    for row in _rows(customization.announcements):
        text = _text(row.get('text'), 120)
        if text:
            notes.append(
                f'<span class="ds-note">{_icon_svg(row.get("icon"))}{escape(text)}</span>'
            )
    return ''.join(notes)

def _contact_fragment(store, flags):
    """
    Contenedor del formulario "Contáctanos": el puente arma los campos,
    pide el captcha y publica por `ds-api` — mismos endpoints que el
    bloque Vue `contact` (email + honeypot + captcha firmado).
    """
    if not flags.get('contact', True):
        return ''
    slug = store.slug
    return (
        f'<div class="ds-contact" data-ds-contact '
        f'data-url="/api/stores/public/{slug}/contact/" '
        f'data-cap-url="/api/stores/public/{slug}/contact/captcha/"></div>'
    )

def _brands_fragment(store, flags = None):
    """
    Marcas de la tienda: logo WebP (o inicial) + nombre. Cada item enlaza
    al catálogo filtrado por esa marca — el puente fija `state.brands` con
    `data-ds-brand` antes de navegar (`data-ds-route="catalog"`). Sin
    página de catálogo el enlace no filtraría nada y el item va estático.
    """
    if flags is None:
        flags = _page_flags(store, getattr(store, 'customization', None))
    if not flags.get('brands', True):
        return ''
    from StoreApp.domains.catalog.models import Brand
    from StoreApp.domains.stores.services.storage import object_url

    can_link = bool(flags.get('catalog', True))
    rows = Brand.objects.filter(store = store).order_by('position', 'name')[:FRAGMENT_LIMIT]
    items = []
    for row in rows:
        name = _text(row.name, 60)
        if not name:
            continue
        #Mismo corte que `data-brand` de las tarjetas: el filtro del
        #puente compara strings exactos.
        key = _text(name, 40)
        url = object_url(row.image_key)
        media = (
            f'<img class="ds-brand-img" src="{_attr(url)}" alt="" loading="lazy" decoding="async">'
            if url else f'<span class="ds-brand-initial" aria-hidden="true">{escape(name[:1].upper())}</span>'
        )
        label = f'<span class="ds-brand-name">{escape(name)}</span>'
        if can_link:
            inner = (
                f'<a class="ds-brand-link" href="#catalogo" data-ds-route="catalog"'
                f' data-ds-brand="{_attr(key)}" aria-label="Ver productos de {escape(name)}">'
                f'{media}{label}</a>'
            )
        else:
            inner = f'<span class="ds-brand-link">{media}{label}</span>'
        items.append(f'<li class="ds-brand">{inner}</li>')
    return ''.join(items)

def _shots_fragment(rows):
    """
    Figure `.ds-shot` por imagen (portada/carrusel/galería/decor): el
    patrón las distribuye donde quiera — filmstrip, vitrina, collage —
    y cada hoja les da su marco. El tope es FRAGMENT_LIMIT igual que el
    resto de los fragmentos.
    """
    from StoreApp.domains.stores.services.storage import object_url

    shots = []
    for row in rows[:FRAGMENT_LIMIT]:
        url = object_url(row.image_key)
        if not url:
            continue
        alt = _text(getattr(row, 'alt', ''), 80)
        shots.append(
            f'<figure class="ds-shot"><img src="{_attr(url)}" alt="{_attr(alt)}" loading="lazy"></figure>'
        )
    return ''.join(shots)

def _gallery_fragment(store, customization):
    from StoreApp.domains.stores.models import StoreGalleryImage

    if customization is not None and customization.show_gallery is False:
        return ''
    rows = [
        row for row in store.gallery_images.all()
        if row.kind == StoreGalleryImage.KIND_GALLERY
    ]
    return _shots_fragment(rows)

def _carousel_fragment(store):
    """
    Carrusel de portada (StoreCarouselImage): contenido premium — sin
    `has_design_advanced` las imágenes no viajan al documento, igual que
    en la plantilla Vue.
    """
    from StoreApp.domains.stores.services import profile_has_benefit

    if not profile_has_benefit(store.user, 'has_design_advanced'):
        return ''
    return _shots_fragment(store.carousel_images.all())

def _decor_fragment(store):
    """
    Imágenes `decor` de la galería (KIND_DECOR, hasta 3): decoración de
    portada premium. No depende de `show_gallery` — en la web Vue se
    usan en about/contacto aunque la sección Galería esté apagada.
    """
    from StoreApp.domains.stores.models import StoreGalleryImage
    from StoreApp.domains.stores.services import profile_has_benefit

    if not profile_has_benefit(store.user, 'has_design_advanced'):
        return ''
    rows = [
        row for row in store.gallery_images.all()
        if row.kind == StoreGalleryImage.KIND_DECOR
    ]
    return _shots_fragment(rows)

MONTHS_ES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
    7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
}
REVIEW_LIST_MAX = 50

THUMB_UP_SVG = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg>'
)
THUMB_DOWN_SVG = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M17 14V2"/><path d="m9 18.12 1 4.88H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/></svg>'
)


def _review_flags(store, customization):
    """(can_rate, can_comment): mismas reglas que `product_reviews` —
    el toggle del dueño Y el beneficio `has_product_comments` del plan."""
    from StoreApp.domains.stores.services import profile_has_benefit

    has_reviews = profile_has_benefit(store.user, 'has_product_comments')
    can_rate = bool(getattr(customization, 'show_reviews', False) and has_reviews)
    can_comment = bool(getattr(customization, 'show_comments', False) and has_reviews)
    return can_rate, can_comment


def _reviews_fragment(store, product, customization):
    """
    Opiniones del producto: lista renderizada + contenedor del formulario
    que arma el puente (la API pública es la misma de la vista Vue).
    Cadena vacía cuando el dueño apagó las opiniones o el plan no las
    incluye: la sección del diseño se apaga sola con `:has()`.
    """
    can_rate, can_comment = _review_flags(store, customization)
    if not (can_rate or can_comment):
        return ''
    items = []
    for review in product.reviews.all()[:REVIEW_LIST_MAX]:
        if review.is_positive is None and not (can_comment and review.text):
            continue
        surname = (review.surname or '').strip()
        initial = f'{surname[0]}.' if surname else ''
        vote = ''
        if review.is_positive is not None:
            cls = 'up' if review.is_positive else 'down'
            vote = (
                f'<span class="ds-rev-vote ds-rev-{cls}" title="{"Le gustó" if review.is_positive else "No le gustó"}">'
                f'{THUMB_UP_SVG if review.is_positive else THUMB_DOWN_SVG}</span>'
            )
        text = (
            f'<p class="ds-rev-text">{escape(_text(review.text, 600))}</p>'
            if can_comment and review.text else ''
        )
        #Respuesta pública del dueño: la escribe desde su panel (PATCH
        #/api/reviews/<pk>/reply/) y se muestra bajo la opinión.
        reply = (
            f'<p class="ds-rev-reply"><strong>Respuesta del comercio</strong>'
            f'<span>{escape(_text(review.owner_reply, 600))}</span></p>'
            if review.owner_reply else ''
        )
        date = review.created_at.date()
        items.append(
            '<li class="ds-rev-item">'
            f'<strong class="ds-rev-name">{escape(_text(review.name, 60))} {escape(initial)}</strong>'
            f'<time class="ds-rev-date" datetime="{date.isoformat()}">'
            f'{date.day} de {MONTHS_ES[date.month]} de {date.year}</time>'
            f'{vote}{text}{reply}</li>'
        )
    return (
        f'<div class="ds-reviews" data-rev-url="/api/stores/public/{store.slug}/products/{product.pk}/reviews/"'
        f' data-cap-url="/api/stores/public/{store.slug}/reviews/captcha/"'
        f' data-rate="{1 if can_rate else 0}" data-comment="{1 if can_comment else 0}">'
        f'<ul class="ds-rev-list" data-ds-rev-list>{"".join(items)}</ul>'
        '<div class="ds-rev-form" data-ds-rev-form></div>'
        '</div>'
    )


def _rating_values(store, product, customization):
    """('4.5', '12') cuando las valoraciones están habilitadas; ('', '') si no."""
    can_rate, _ = _review_flags(store, customization)
    if not can_rate:
        return '', ''
    votes = product.reviews.filter(is_positive__isnull = False)
    count = votes.count()
    if not count:
        return '', ''
    avg = round(votes.filter(is_positive = True).count() / count * 5, 1)
    return f'{avg:g}', str(count)


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

def _product_whatsapp_url(store, customization, product, store_name, amount = None):
    if not str(getattr(customization, 'whatsapp', '') or '').strip():
        return ''
    if amount is None:
        amount = product.offer_price if product.offer_price is not None else product.price
    price = _money(amount) if _amount(amount) else ''
    text = f'Hola {store_name}, me interesa "{_text(product.name, 80)}"'
    if price:
        text += f' ({price})'
    text += ' que vi en tu catálogo.'
    return _contact_link(store, customization, 'whatsapp', 'whatsapp', text)

def _product_values(store, product, customization, store_name, flags = None):
    """Variables `product_*` del documento (ficha de producto)."""
    from StoreApp.domains.stores.services.storage import object_url

    if product is None:
        return {name: '' for name in (
            'product_name', 'product_description', 'product_price', 'product_old_price',
            'product_offer_pct', 'product_save', 'product_image', 'product_category',
            'product_brand', 'product_ref', 'product_whatsapp_url', 'product_rating_avg',
            'product_rating_count',
        )}, {'product_features': '', 'product_related': '', 'product_reviews': '', 'product_campaign_label': ''}
    from StoreApp.domains.catalog.services.services import (
        effective_pricing_of,
        running_discounts_of,
    )
    #La ficha resuelve el mismo precio que la tarjeta: oferta manual o el
    #mejor descuento vigente (incluidas las campañas), el que quede más bajo.
    discounts = running_discounts_of(store)
    effective_offer, effective_discount = effective_pricing_of(product, discounts)
    amount = effective_offer if effective_offer is not None else product.price
    old = ''
    pct = ''
    save = ''
    if effective_offer is not None and _amount(product.price):
        old = _money(product.price)
        pct = f'-{max(1, min(99, int(round((1 - _amount(amount) / _amount(product.price)) * 100))))}%'
        save = _money(_amount(product.price) - _amount(amount))
    #Sticker de la campaña que firma la oferta: fragmento raw como el de la
    #tarjeta, para que el diseño lo ancle donde quiera (o lo ignore).
    campaign_label = ''
    campaign = getattr(effective_discount, 'campaign', None)
    if campaign is not None:
        label_url = object_url(campaign.label_key, private = True)
        if label_url:
            campaign_label = (
                f'<img class="ds-campaign-label" src="{_attr(label_url)}"'
                f' width="{campaign.label_width or 90}" height="{campaign.label_height or 24}"'
                f' alt="{_attr(campaign.label_alt or campaign.name)}" loading="lazy" decoding="async">'
            )
    rating_avg, rating_count = _rating_values(store, product, customization)
    context = {
        'product_name':         _text(product.name, 120),
        'product_description':  _text(product.description, 600),
        'product_price':        _money(amount) if _amount(amount) else 'Consultar',
        'product_old_price':    old,
        'product_offer_pct':    pct,
        'product_save':         save,
        'product_image':        object_url(product.image_key) or '',
        'product_category':     _text(getattr(product.category, 'name', ''), 60),
        'product_brand':        _text(getattr(product.brand, 'name', ''), 60),
        'product_ref':          str(product.pk),
        'product_whatsapp_url': _product_whatsapp_url(store, customization, product, store_name, amount),
        'product_rating_avg':   rating_avg,
        'product_rating_count': rating_count,
    }
    raw = {
        'product_features': _features_fragment(product),
        'product_related':  _related_fragment(store, product) if flags is None or flags.get('catalog', True) else '',
        'product_reviews':  _reviews_fragment(store, product, customization),
        'product_campaign_label': campaign_label,
    }
    return context, raw

def _videos_fragment(customization, flags):
    """
    Grilla de embeds de redes (videos[] ya normalizados a embed oficial
    por el serializer). Se recorta al tope max_videos del plan vigente —
    igual que la web Vue— y sin filas cae al video_url legado. Apagada
    con el flag 'video' (show_video / bloque de "Qué mostrar").
    """
    if customization is None or not flags.get('video'):
        return ''
    videos = [v for v in (customization.videos or []) if isinstance(v, str) and v.strip()]
    if not videos:
        legacy = _text(getattr(customization, 'video_url', ''), 400)
        videos = [legacy] if legacy else []
    if not videos:
        return ''
    from StoreApp.domains.stores.models import StoreCustomization
    from StoreApp.domains.stores.services import plan_benefits_of

    limit = plan_benefits_of(customization.store.user).get('max_videos')
    cap = StoreCustomization.VIDEOS_MAX if limit is None else min(int(limit), StoreCustomization.VIDEOS_MAX)
    cards = ''.join(
        '<figure style="margin:0"><div style="position:relative;aspect-ratio:16/9;overflow:hidden;border-radius:12px;background:#000">'
        f'<iframe src="{_attr(url)}" style="position:absolute;inset:0;width:100%;height:100%;border:0" '
        'loading="lazy" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div></figure>'
        for url in videos[:cap]
    )
    return f'<div class="ds-videos" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px">{cards}</div>'


#=========================================
# CONTEXTO DE LA TIENDA
#=========================================
def build_store_context(store, product = None, flags = None, raw_keys = None):
    """
    Devuelve `(context, raw)`: `context` son las variables de texto que
    interpola el patrón y `raw` los fragmentos HTML ya escapados. Con
    `raw_keys` solo se arman los fragmentos que el markup usa: un diseño sin
    galería/FAQ no paga esas consultas ni ese HTML.
    """
    customization = getattr(store, 'customization', None)
    flags = flags if flags is not None else _page_flags(store, customization)
    user = store.user
    name = _text(
        getattr(customization, 'display_name', '') or getattr(user, 'business_name', ''),
        60,
    )
    city = _text(getattr(getattr(user, 'city', None), 'name_city', ''), 60)
    province = _text(getattr(getattr(user, 'province', None), 'name_province', ''), 60)
    location = ', '.join(part for part in (city, province) if part)
    address = _text(getattr(user, 'address', ''), 160) if customization and customization.show_location else ''
    has_whatsapp = bool(str(getattr(customization, 'whatsapp', '') or '').strip())
    description = _text(getattr(customization, 'description', ''), 400)
    headline = _text(getattr(customization, 'headline', ''), 140)
    about = _text(getattr(customization, 'about_text', ''), 400)
    from django.utils import timezone

    from StoreApp.domains.stores.services import (
        contact_redirect_path,
        profile_has_benefit,
    )

    #El stream en vivo es Premium (has_live_stream): sin el flag la URL no
    #viaja al documento (queda guardada para cuando vuelva el plan).
    live_ok = bool(flags.get('video')) and profile_has_benefit(store.user, 'has_live_stream')

    context = {
        'store_name': name,
        'store_initial': name[:1].upper(),
        'store_tagline': headline or description,
        'store_description': description,
        'store_about': about,
        'store_about_title': _text(getattr(customization, 'about_title', ''), 80),
        'store_about_years': str(getattr(customization, 'about_years', None) or ''),
        'store_about_mission': _text(getattr(customization, 'about_mission', ''), 400),
        'store_about_specialties': _text(getattr(customization, 'about_specialties', ''), 300),
        'store_location': location,
        'store_address': address,
        #El número y el email no viajan en el HTML: el canal se muestra por
        #nombre ("WhatsApp") y los links pasan por el redirect público.
        'store_phone': 'WhatsApp' if has_whatsapp else '',
        'store_whatsapp_url': _contact_link(store, customization, 'whatsapp', 'whatsapp'),
        'store_email': '',
        'store_hours': _hours_text(customization),
        'store_instagram_url': _contact_link(store, customization, 'instagram', 'instagram'),
        'store_facebook_url': _contact_link(store, customization, 'facebook', 'facebook'),
        'store_tiktok_url': _contact_link(store, customization, 'tiktok', 'tiktok'),
        'store_maps_url': contact_redirect_path(store, 'maps') if address else '',
        'store_logo': '',
        'store_cover': '',
        'store_accent': '',
        'plans_title': _text(getattr(customization, 'plans_title', ''), 80) or 'Suscripciones y membresías',
        'offerings_title': _text(getattr(customization, 'services_title', ''), 80) or 'Qué ofrecemos',
        'testimonials_title': _text(getattr(customization, 'testimonials_title', ''), 80) or 'Testimonios',
        'faqs_title': _text(getattr(customization, 'faqs_title', ''), 80) or 'Preguntas frecuentes',
        'video_url': _text(getattr(customization, 'video_url', ''), 400) if flags.get('video') else '',
        'video_title': _text(getattr(customization, 'video_title', ''), 80),
        'live_stream_url': _text(getattr(customization, 'live_stream_url', ''), 400) if live_ok else '',
        'cta_title': _text(getattr(customization, 'cta_title', ''), 120),
        'cta_text': _text(getattr(customization, 'cta_text', ''), 280),
        'cta_label': _text(getattr(customization, 'cta_label', ''), 40),
        'footer_text': _text(getattr(customization, 'footer_text', ''), 200),
        'year': str(timezone.now().year),
    }
    from StoreApp.domains.stores.services.storage import object_url

    if customization is not None:
        context['store_logo'] = object_url(customization.logo_key) or ''
        context['store_cover'] = object_url(customization.cover_key) or ''
        context['store_accent'] = _text(customization.accent_custom, 7) or ''
    builders = {
        'products': lambda: _product_fragment(store, flags = flags),
        'categories': lambda: _category_fragment(store, flags = flags),
        'services': lambda: _service_fragment(store, flags = flags),
        'plans': lambda: _plans_fragment(store, customization, flags = flags),
        'offerings': lambda: _offerings_fragment(customization, flags),
        'stats': lambda: _stats_fragment(customization, flags),
        'testimonials': lambda: _testimonials_fragment(customization, flags),
        'faqs': lambda: _faqs_fragment(customization, flags),
        'benefits': lambda: _benefits_fragment(customization, flags),
        'timeline': lambda: _timeline_fragment(customization, flags),
        'team': lambda: _team_fragment(customization, flags),
        'announcements': lambda: _announcements_fragment(customization, flags),
        'videos': lambda: _videos_fragment(customization, flags),
        'contact_form': lambda: _contact_fragment(store, flags),
        'gallery': lambda: _gallery_fragment(store, customization),
        'carousel': lambda: _carousel_fragment(store),
        'decor': lambda: _decor_fragment(store),
        'brands': lambda: _brands_fragment(store, flags = flags),
    }
    keys = builders.keys() if raw_keys is None else [key for key in builders if key in raw_keys]
    raw = {key: builders[key]() for key in keys}
    product_ctx, product_raw = _product_values(store, product, customization, name, flags = flags)
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


_HEX_RE   =   re.compile(r'^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$')

def _hex_rgb(value):
    match   =   _HEX_RE.match(str(value or '').strip())
    if not match:
        return None
    d   =   match.group(1)
    if len(d) == 3:
        d   =   ''.join(ch * 2 for ch in d)
    return  [int(d[i:i + 2], 16) for i in (0, 2, 4)]

def _rgb_hex(rgb):
    return  '#' + ''.join(f'{max(0, min(255, round(c))):02x}' for c in rgb)

def _rel_lum(rgb):
    def channel(v):
        s   =   v / 255
        return  s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b   =   rgb
    return  0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def _ratio(a, b):
    la, lb   =   _rel_lum(a), _rel_lum(b)
    return  (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

def _fix_contrast(fg, bg, min_ratio = 4.5):
    """
    Acerca `fg` al extremo (negro o blanco) que mejor contraste con `bg`
    hasta alcanzar `min_ratio` — espejo de `fixContrast` del contrato
    (studio/contract.js): el acento conserva su tono pero nunca deja un
    texto ilegible (botones outline/ghost/transparent de los diseños).
    """
    f, b   =   _hex_rgb(fg), _hex_rgb(bg)
    if not f or not b:
        return  ''
    if _ratio(f, b) >= min_ratio:
        return  _rgb_hex(f)
    black   =   _ratio([0, 0, 0], b) >= _ratio([255, 255, 255], b)
    target  =   [0, 0, 0] if black else [255, 255, 255]
    for step in range(1, 51):
        t   =   step / 50
        hexv    =   _rgb_hex([c + (target[i] - c) * t for i, c in enumerate(f)])
        if _ratio(_hex_rgb(hexv), b) >= min_ratio:
            return  hexv
    return  _rgb_hex(target)


def theme_css(customization, pattern = None, site_theme = None):
    """
    Bloque `:root { --ds-* }` con lo que el estilo puede tocar. Los
    `effects` del estilo ya vienen saneados por `clean_style_effects`; acá
    solo se traducen a custom properties. `site_theme` permite pasar el
    tema EFECTIVO (filtrado por plan) sin tocar el objeto customization.
    """
    style = None
    palette = {}
    if site_theme is None and customization is not None:
        site_theme = getattr(customization, 'site_theme', None)
    if not isinstance(site_theme, dict):
        site_theme = {}
    if customization is not None or site_theme:
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
    #Acento como COLOR DE TEXTO (botones outline/ghost/transparent, enlaces):
    #se ajusta a AA contra la superficie efectiva para que un acento claro
    #nunca deje letras ilegibles. Sin superficie conocida no se emite y el
    #CSS cae al --ds-accent de siempre.
    surface_bg  =   _text(palette.get('surface'), 7) or _text(palette.get('bg'), 7)
    if surface_bg.startswith('#') and str(color).startswith('#'):
        accent_text    =   _fix_contrast(color, surface_bg)
        if accent_text:
            vars_['--ds-accent-text'] = accent_text
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

#=====================================================================
# STUDIO — editores finos de `site_theme` sobre los hooks compartidos
#=====================================================================
# Los documentos de diseño no usan las clases .sp-* de la plantilla Vue:
# comparten un vocabulario propio (.btn, .ds-product*, section.hero,
# header fijado, footer). Estos selectores son el puente: el Studio
# (surfaces/images/background/buttons/typography.roles) escribe reglas
# !important sobre ellos, igual que data-st-* lo hace en store-page.css.
_STUDIO_BTN_SEL   =   '.btn, .svc-cta, .pdp-buy, .nav-cta, .top-cta, .rail-btn, .deck-btn'
_STUDIO_CARD_SEL  =   '.ds-product, .ds-cat, .ds-service, .ds-plan, .ds-faq, .ds-guar, .ds-offer, .ds-contact'
_STUDIO_IMG_SEL   =   '.ds-product-img'
#La barra superior se reconoce por el pin del puente (position:fixed) con
#fallback a las clases top/head que usan los diseños sin pin.
_STUDIO_NAV_SEL   =   '[data-ds-pin="top"], header.top, header.head'
_STUDIO_FOOT_SEL  =   'footer, .foot'
_STUDIO_HERO_SEL  =   'section.hero, .hero'
#Rol tipográfico -> selector del documento (espejo del contrato v2).
_STUDIO_ROLE_SEL  =   {
    'display':  'section.hero h1, .hero h1, h1.display',
    'h1':       'h1',
    'h2':       'h2',
    'h3':       'h3',
    'body':     'body',
    'lead':     '.lead, section.hero p, .hero p',
    'eyebrow':  '.eyebrow, .kicker, [class*="kicker"], [class*="eyebrow"]',
    'label':    '.label, [class*="label"]',
    'quote':    'blockquote, .quote, q',
    'price':    '.ds-product-price, .ds-product-amount, .ds-plan-price',
    'nav':      '.nav a, nav a',
    'button':   '.btn',
    'footer':   'footer, .foot',
}
#Espejo de los mapas de frontend/src/studio/contract.js.
_STUDIO_BTN_RADIUS    =   {'square': '8px', 'rounded': '14px', 'pill': '999px'}
_STUDIO_BTN_SIZE      =   {'sm': ('38px', '16px', '13px'), 'md': ('46px', '22px', '14.5px'), 'lg': ('54px', '28px', '16px')}
_STUDIO_IMG_ASPECT    =   {'square': '1 / 1', 'portrait': '4 / 5', 'tall': '3 / 4', 'wide': '16 / 10'}
_STUDIO_IMG_RADIUS    =   {'none': '0', 'sm': '8px', 'md': '14px', 'lg': '20px'}
_STUDIO_IMG_BORDER    =   {'none': '0', 'thin': '1px', 'bold': '2px'}
_STUDIO_ROLE_SIZE     =   {'xs': '0.75rem', 'sm': '0.875rem', 'md': '1rem', 'lg': '1.25rem', 'xl': '1.5rem', '2xl': '2rem', '3xl': '2.75rem', 'display': 'clamp(2.5rem, 6vw, 4.5rem)'}
_STUDIO_ROLE_TRACKING =   {'tighter': '-0.03em', 'tight': '-0.015em', 'normal': '0', 'wide': '0.04em', 'wider': '0.09em'}
_STUDIO_ROLE_LEADING  =   {'tight': '1.08', 'snug': '1.25', 'normal': '1.55', 'relaxed': '1.75'}
_STUDIO_ROLE_CASE     =   {'none': 'none', 'upper': 'uppercase'}
_STUDIO_OVERLAY_CSS   =   {'soft': 'rgba(9, 12, 24, .32)', 'strong': 'rgba(9, 12, 24, .6)'}
#Familias del catálogo de roles (ai_design_typography.FONT_FAMILIES):
#slug -> (query css2 de Google Fonts, stack font-family). El documento no
#puede cargar hojas externas (style-src 'unsafe-inline'), así que las
#@font-face se descargan acá y viajan inline — los .woff2 de gstatic sí
#entran por font-src https:.
_STUDIO_FONT_FACE = {
    'inter':                 ('Inter:opsz,wght@14..32,100..900', 'Inter, system-ui, sans-serif'),
    'manrope':               ('Manrope:wght@400..800', "'Manrope', sans-serif"),
    'figtree':               ('Figtree:wght@400..700', "'Figtree', system-ui, sans-serif"),
    'dm-sans':               ('DM+Sans:wght@400..800', "'DM Sans', sans-serif"),
    'space-grotesk':         ('Space+Grotesk:wght@400..700', "'Space Grotesk', sans-serif"),
    'archivo':               ('Archivo:wdth,wght@62..125,400..900', "'Archivo', 'Helvetica Neue', sans-serif"),
    'sora':                  ('Sora:wght@400..800', "'Sora', sans-serif"),
    'work-sans':             ('Work+Sans:wght@400..800', "'Work Sans', sans-serif"),
    'outfit':                ('Outfit:wght@300..900', "'Outfit', system-ui, sans-serif"),
    'plus-jakarta-sans':     ('Plus+Jakarta+Sans:wght@300..800', "'Plus Jakarta Sans', system-ui, sans-serif"),
    'nunito':                ('Nunito:wght@400..800', "'Nunito', sans-serif"),
    'raleway':               ('Raleway:wght@400..800', "'Raleway', sans-serif"),
    'playfair-display':      ('Playfair+Display:ital,wght@0,400..800;1,400..800', "'Playfair Display', Georgia, serif"),
    'fraunces':              ('Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900', "'Fraunces', Georgia, serif"),
    'lora':                  ('Lora:ital,wght@0,400..700;1,400..700', "'Lora', Georgia, serif"),
    'cormorant-garamond':    ('Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400', "'Cormorant Garamond', Georgia, serif"),
    'dm-serif-display':      ('DM+Serif+Display', "'DM Serif Display', Georgia, serif"),
    'libre-baskerville':     ('Libre+Baskerville:ital,wght@0,400;0,700;1,400', "'Libre Baskerville', Georgia, serif"),
    'cinzel':                ('Cinzel:wght@400..800', "'Cinzel', Georgia, serif"),
    'oswald':                ('Oswald:wght@400..700', "'Oswald', sans-serif"),
    'archivo-black':         ('Archivo+Black', "'Archivo Black', sans-serif"),
    'bebas-neue':            ('Bebas+Neue', "'Bebas Neue', sans-serif"),
    'space-mono':            ('Space+Mono:ital,wght@0,400;0,700;1,400;1,700', "'Space Mono', monospace"),
    'jetbrains-mono':        ('JetBrains+Mono:ital,wght@0,400..800;1,400..800', "'JetBrains Mono', monospace"),
}
_GOOGLE_FONTS_UA =   ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

def _studio_font_slugs(site_theme):
    """Slugs del catálogo usados por typography.roles (para @font-face)."""
    typo    =   site_theme.get('typography') if isinstance(site_theme.get('typography'), dict) else {}
    roles   =   typo.get('roles') if isinstance(typo.get('roles'), dict) else {}
    out     =   []
    for spec in roles.values():
        slug    =   spec.get('font') if isinstance(spec, dict) else None
        if slug in _STUDIO_FONT_FACE and slug not in out:
            out.append(slug)
    return out

def studio_font_css(site_theme):
    """
    @font-face de las familias elegidas en los roles tipográficos: el CSS2
    de Google Fonts llega con URLs de gstatic (font-src https: las acepta)
    y se inlinea porque style-src no permite hojas externas. Cacheado por
    query; si Google no responde se omite (la pila cae a la siguiente).
    """
    import urllib.request
    from django.core.cache import cache

    parts   =   []
    for slug in _studio_font_slugs(site_theme):
        query, _family =   _STUDIO_FONT_FACE[slug]
        key     =   f'dsfont:{query}'
        css     =   cache.get(key)
        if css is None:
            try:
                req =   urllib.request.Request(
                    f'https://fonts.googleapis.com/css2?family={query}&display=swap',
                    headers = {'User-Agent': _GOOGLE_FONTS_UA},
                )
                with urllib.request.urlopen(req, timeout = 4) as res:
                    css =   res.read().decode('utf-8', 'replace')
            except Exception:
                css =   ''
            #Lo que no responde se reintenta en 5 min; lo bueno una semana.
            cache.set(key, css, 300 if not css else 60 * 60 * 24 * 7)
        if css:
            parts.append(css)
    return '\n'.join(parts)

def _studio_ink(value):
    """
    Tinta sobre una superficie del Studio: los dos extremos de
    `_contrast_ink` (casi tinta / casi papel) según luminancia — espejo
    exacto del `textOn` simplificado que usa el preview en vivo.
    """
    match = re.fullmatch(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})', str(value or '').strip())
    if not match:
        return '#191611'
    digits = match.group(1)
    if len(digits) == 3:
        digits = ''.join(ch * 2 for ch in digits)
    r, g, b = (int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    return '#191611' if luminance > 0.1833 else '#FFFDF8'

def studio_theme_css(site_theme):
    """
    Reglas del Studio sobre los hooks compartidos de los documentos de
    diseño (`.btn`, `.ds-product*`, `section.hero`, barra fijada, footer,
    body). Espejo de `patternStudioCss` del frontend: misma entrada
    (site_theme parcial ya filtrado por plan), misma salida CSS — el
    documento publicado la hornea en `css` y la vista previa del Studio
    la inyecta en vivo por postMessage.
    """
    theme   =   site_theme if isinstance(site_theme, dict) else {}
    def sect(name):
        value   =   theme.get(name)
        return  value if isinstance(value, dict) else {}

    surfaces    =   sect('surfaces')
    images      =   sect('images')
    buttons     =   sect('buttons')
    background  =   sect('background')
    roles       =   sect('typography').get('roles')
    roles       =   roles if isinstance(roles, dict) else {}

    rules   =   []

    #--- Tipografía por rol: familia del catálogo (con su @font-face en
    #studio_font_css), tamaño, peso, tracking, leading y caja. Va PRIMERO:
    #a igual especificidad las reglas de secciones (botones, superficies)
    #ganan después — p.ej. buttons.size manda sobre el font-size del rol
    #'button' pero la familia/peso del rol se conservan.
    for role, sel in _STUDIO_ROLE_SEL.items():
        spec    =   roles.get(role)
        if not isinstance(spec, dict):
            continue
        decl    =   []
        font    =   spec.get('font')
        if font in _STUDIO_FONT_FACE:
            decl.append(f'font-family:{_STUDIO_FONT_FACE[font][1]}')
        if spec.get('size') in _STUDIO_ROLE_SIZE:
            decl.append(f'font-size:{_STUDIO_ROLE_SIZE[spec["size"]]}')
        weight  =   spec.get('weight')
        if isinstance(weight, (int, float)) and 300 <= weight <= 900:
            decl.append(f'font-weight:{int(round(weight / 100) * 100)}')
        if spec.get('tracking') in _STUDIO_ROLE_TRACKING:
            decl.append(f'letter-spacing:{_STUDIO_ROLE_TRACKING[spec["tracking"]]}')
        if spec.get('leading') in _STUDIO_ROLE_LEADING:
            decl.append(f'line-height:{_STUDIO_ROLE_LEADING[spec["leading"]]}')
        if spec.get('case') in _STUDIO_ROLE_CASE:
            decl.append(f'text-transform:{_STUDIO_ROLE_CASE[spec["case"]]}')
        if decl:
            body    =   ';'.join(f'{prop}!important' for prop in decl)
            rules.append(f'{sel}{{{body}}}')

    #--- Superficies: fondo propio + tinta derivada (AA por luminancia).
    surf_sel    =   {'card': _STUDIO_CARD_SEL, 'nav': _STUDIO_NAV_SEL,
                     'footer': _STUDIO_FOOT_SEL, 'hero': _STUDIO_HERO_SEL}
    for key, sel in surf_sel.items():
        hexv    =   _text(surfaces.get(key), 7)
        if not hexv.startswith('#'):
            continue
        ink     =   _studio_ink(hexv)
        rules.append(f'{sel}{{background:{hexv}!important;color:{ink}!important}}')

    #--- Marco de fotos de producto (.ds-product-img es el <img>/<span>).
    img_decl   =   {}
    if images.get('ratio') in _STUDIO_IMG_ASPECT:
        img_decl['aspect-ratio']    =   _STUDIO_IMG_ASPECT[images['ratio']]
    if images.get('fit') in ('cover', 'contain'):
        img_decl['object-fit']      =   images['fit']
    img_bg     =   _text(images.get('bg'), 7)
    if img_bg.startswith('#'):
        img_decl['background']      =   img_bg
    if images.get('radius') in _STUDIO_IMG_RADIUS:
        img_decl['border-radius']   =   _STUDIO_IMG_RADIUS[images['radius']]
    if images.get('border') in _STUDIO_IMG_BORDER:
        bw  =   _STUDIO_IMG_BORDER[images['border']]
        img_decl['border']          =   '0' if bw == '0' else f'{bw} solid var(--ds-border, currentColor)'
    if img_decl:
        body    =   ';'.join(f'{prop}:{val}!important' for prop, val in img_decl.items())
        rules.append(f'{_STUDIO_IMG_SEL}{{{body}}}')

    #--- Fondo de página: 'solid' ya viaja por palette.bg (--ds-bg);
    #gradient/mesh/pattern traen la declaración CSS saneada al guardar e
    #image una URL propia de la tienda.
    bg_type  =   background.get('type')
    bg_value =   _text(background.get('value'), 400)
    if bg_type == 'image' and bg_value:
        safe    =   bg_value.replace('"', '%22')
        rules.append(f'body, main{{background:url("{safe}") center / cover no-repeat!important}}')
    elif bg_type in ('gradient', 'mesh', 'pattern') and bg_value:
        rules.append(f'body, main{{background:{bg_value}!important}}')
    overlay    =   _STUDIO_OVERLAY_CSS.get(background.get('overlay'), '')
    if overlay:
        rules.append(
            'body::after{content:"";position:fixed;inset:0;'
            f'background:{overlay};pointer-events:none;z-index:2147483000}}'
        )

    #--- Botones: estilo de relleno, borde, forma y tamaño sobre .btn y
    #los CTA-link propios de cada diseño (mismo alcance que .sp-btn).
    btn_style  =   buttons.get('style')
    if btn_style in ('solid', 'outline', 'ghost', 'gradient', 'transparent'):
        if btn_style == 'solid':
            decl    =   'background:var(--ds-accent, currentColor)!important;'
            decl    +=  'color:var(--ds-accent-ink, #fff)!important;'
            decl    +=  'border-color:transparent!important'
        elif btn_style == 'outline':
            decl    =   'background:transparent!important;'
            decl    +=  'color:var(--ds-accent-text, var(--ds-accent, currentColor))!important;'
            decl    +=  'border-color:var(--ds-accent, currentColor)!important'
        elif btn_style == 'ghost':
            decl    =   'background:color-mix(in srgb, var(--ds-accent, currentColor) 12%, transparent)!important;'
            decl    +=  'color:var(--ds-accent-text, var(--ds-accent, currentColor))!important;'
            decl    +=  'border-color:transparent!important'
        elif btn_style == 'gradient':
            decl    =   'background:linear-gradient(120deg, var(--ds-primary, var(--ds-accent, currentColor)), var(--ds-secondary, var(--ds-accent, currentColor)))!important;'
            decl    +=  'color:#fff!important;'
            decl    +=  'border-color:transparent!important'
        else:  # transparent
            decl    =   'background:color-mix(in srgb, var(--ds-accent, currentColor) 8%, transparent)!important;'
            decl    +=  'color:var(--ds-accent-text, var(--ds-accent, currentColor))!important;'
            decl    +=  'border-color:transparent!important'
        rules.append(f'{_STUDIO_BTN_SEL}{{{decl}}}')
    btn_border  =   buttons.get('borderStyle')
    if btn_border in ('solid', 'dashed', 'dotted', 'none'):
        if btn_border == 'none':
            decl    =   'border-color:transparent!important'
        else:
            width   =   '1.5px' if btn_border == 'solid' else '2px'
            decl    =   (f'border-style:{btn_border}!important;'
                         f'border-width:{width}!important;'
                         'border-color:color-mix(in srgb, currentColor 72%, transparent)!important')
        rules.append(f'{_STUDIO_BTN_SEL}{{{decl}}}')
    if buttons.get('shape') in _STUDIO_BTN_RADIUS:
        rules.append(f'{_STUDIO_BTN_SEL}{{border-radius:{_STUDIO_BTN_RADIUS[buttons["shape"]]}!important}}')
    if buttons.get('size') in _STUDIO_BTN_SIZE:
        h, px, fs   =   _STUDIO_BTN_SIZE[buttons['size']]
        rules.append(
            f'{_STUDIO_BTN_SEL}{{min-height:{h}!important;'
            f'padding-inline:{px}!important;font-size:{fs}!important}}'
        )

    return '\n'.join(rules)

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

def _effective_site_theme(store, site_theme):
    """
    site_theme filtrado por el plan vigente de la tienda (espejo del
    serializer público). Si la consulta de beneficios falla se devuelve
    lo guardado: mejor un tema de más que un documento sin estilos.
    """
    try:
        from StoreApp.domains.stores.services.services import profile_has_benefit
        from StoreApp.domains.stores.site_theme import filter_site_theme

        user    =   getattr(store, 'user', None)
        return  filter_site_theme(
            site_theme,
            has_plus     =   profile_has_benefit(user, 'has_design_plus'),
            has_advanced =   profile_has_benefit(user, 'has_design_advanced'),
            has_style    =   profile_has_benefit(user, 'has_customization'),
        )
    except Exception:
        return site_theme if isinstance(site_theme, dict) else {}

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
    flags = _page_flags(store, customization)
    zone_flags = _zone_flags(flags, customization)
    #Solo los fragmentos que el markup referencia: el resto de la tienda
    #(galería, FAQ, equipo, testimonios…) no se consulta ni se renderiza.
    needed = set(VAR_RE.findall(pattern.html or ''))
    context, raw = build_store_context(store, product, flags = zone_flags, raw_keys = needed)
    html = pattern.render(context, raw = raw)
    from StoreApp.domains.catalog.models import Product

    site_theme_raw = (
        customization.site_theme
        if customization is not None and isinstance(getattr(customization, 'site_theme', None), dict)
        else {}
    )
    #Tema EFECTIVO según el plan vigente — el mismo filtro que aplica la
    #API pública de la plantilla Vue: sin has_design_advanced las secciones
    #premium del Studio no se publican en el documento.
    site_theme = _effective_site_theme(store, site_theme_raw)
    style = site_theme.get('style') if isinstance(site_theme.get('style'), dict) else {}
    #Las páginas apagadas en "Qué mostrar" también se apagan en el
    #documento: se quita la superficie (la ruta sigue con la plantilla
    #Vue, que redirige) y las zonas marcadas `data-flag` se ocultan por
    #CSS (sección, CTA y enlace del menú van con la misma marca).
    surfaces = sorted(set(SURFACE_RE.findall(html)))
    if not flags['catalog']:
        surfaces = [name for name in surfaces if name not in ('catalog', 'product')]
    if not flags['services']:
        surfaces = [name for name in surfaces if name != 'services']
    flags_css = ''.join(
        f'[data-flag="{name}"]{{display:none!important}}'
        for name, enabled in zone_flags.items() if not enabled
    )
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
        'surfaces': surfaces,
        #El catálogo del diseño trae los productos ya renderizados: si la
        #tienda tiene más de los que entran en el documento, esa ruta sigue
        #con la plantilla Vue (que pagina) para no esconder productos.
        'products_total': Product.objects.filter(store = store, is_active = True).count(),
        'products_shown': FRAGMENT_LIMIT,
        'html': html,
        #theme_css con el tema efectivo + las reglas del Studio (superficies,
        #fotos, fondo, botones, roles) y las @font-face de las familias
        #elegidas — todo inline por el CSP del documento.
        'css': (
            f'{theme_css(customization, pattern, site_theme)}\n'
            f'{studio_font_css(site_theme)}\n'
            f'{studio_theme_css(site_theme)}\n'
            f'{flags_css}\n{pattern.css or ""}'
        ),
        'js': pattern.js or '',
        #Imágenes críticas del primer viewport: el documento las preloadea
        #en el head (portada del hero y logo) en vez de descubrirlas al
        #parsear el body.
        'preload': [url for url in (context.get('store_cover'), context.get('store_logo')) if url],
        'dark': bool(pattern.supports_dark_mode),
    }
