from django.utils import timezone

from StoreApp.domains.design.services.pattern_document import SURFACE_CSS
from StoreApp.domains.design.services.pattern_render import theme_css

"""
Vista previa de un DesignPattern sin tienda: el panel muestra el diseño
fuente tal como se vería, con datos de ejemplo en lugar de los
placeholders `{{variable}}` sin interpolar.

Devuelve `{html, css, js}` con las variables resueltas y los fragmentos de
lista armados con la misma estructura que publica `pattern_render`
(`.ds-product`, `.ds-cat`, `.ds-service`), así la hoja del diseño aplica.
"""

SAMPLE_PRODUCTS = [
    ('Auriculares inalámbricos', 'Cancelación de ruido y estuche de carga.', 'Audio', '89.999'),
    ('Reloj deportivo', 'GPS, pulsómetro y batería de 7 días.', 'Deportes', '129.999'),
    ('Mochila urbana 24 L', 'Nylon resistente al agua y bolsillo para notebook.', 'Accesorios', '64.999'),
    ('Lámpara de escritorio', 'Luz cálida regulable con brazo articulado.', 'Hogar', '42.500'),
    ('Zapatillas de running', 'Amortiguación liviana para entrenamiento diario.', 'Deportes', '98.000'),
    ('Set de sartenes', 'Tres tamaños con recubrimiento antiadherente.', 'Hogar', '75.999'),
    ('Cargador rápido 65 W', 'Carga notebook y celular al mismo tiempo.', 'Tecnología', '39.999'),
    ('Botella térmica 1 L', 'Mantiene la temperatura 12 horas.', 'Accesorios', '28.500'),
]
SAMPLE_CATEGORIES = ['Tecnología', 'Audio', 'Deportes', 'Hogar', 'Accesorios']
SAMPLE_SERVICES = [
    ('Envíos a domicilio', 'Coordinamos la entrega en el día dentro de la ciudad.'),
    ('Retiro en el local', 'Preparado y listo para retirar en el horario de atención.'),
    ('Cambios y devoluciones', 'Tenés 30 días para cambiar el producto sin vueltas.'),
    ('Asesoramiento', 'Te ayudamos a elegir por WhatsApp antes de comprar.'),
]


def _product_fragment():
    cards = []
    for name, desc, category, price in SAMPLE_PRODUCTS:
        cards.append(
            f'<article class="ds-product" data-cat="{category}"'
            f' data-name="{name.lower()}" data-price="{price}">'
            '<a class="ds-product-link" href="#catalogo" aria-label="' + name + '">'
            '<span class="ds-product-img is-empty" aria-hidden="true"></span>'
            '<span class="ds-product-copy">'
            f'<h3 class="ds-product-name">{name}</h3>'
            f'<small class="ds-product-desc">{desc}</small>'
            '</span>'
            f'<span class="ds-product-cat">{category}</span>'
            f'<span class="ds-product-price">${price}</span>'
            '</a></article>'
        )
    return ''.join(cards)


def _category_fragment():
    return ''.join(
        f'<a class="ds-cat" href="#catalogo"><span>{name}</span></a>'
        for name in SAMPLE_CATEGORIES
    )


def _service_fragment():
    items = ''.join(
        f'<li class="ds-service"><strong class="ds-service-name">{name}</strong>'
        f'<span class="ds-service-desc">{desc}</span></li>'
        for name, desc in SAMPLE_SERVICES
    )
    return f'<ul class="ds-services-list">{items}</ul>'


def sample_context():
    return {
        'store_name': 'Tu negocio',
        'store_initial': 'T',
        'store_tagline': 'Todo lo que buscás, en un solo lugar',
        'store_description': 'Un catálogo simple, precios claros y atención directa por WhatsApp.',
        'store_about': 'Atendemos en el local y enviamos a todo el país. Cada compra tiene garantía y seguimiento.',
        'store_location': 'La Plata, Buenos Aires',
        'store_address': 'Calle 7 1234',
        'store_phone': '221 555 0123',
        'store_whatsapp_url': 'https://wa.me/5492215550123',
        'store_email': 'hola@tunegocio.com',
        'store_hours': 'Lun a Vie 9 a 18 h',
        'store_logo': '',
        'store_cover': '',
        'store_accent': '',
        'year': str(timezone.now().year),
    }


def preview_pattern(pattern):
    """`{html, css, js}` del patrón con datos de ejemplo (para el modal)."""
    raw = {
        'products': _product_fragment(),
        'categories': _category_fragment(),
        'services': _service_fragment(),
        'gallery': '',
    }
    html = pattern.render(sample_context(), raw = raw)
    return {
        'slug': pattern.slug,
        'nombre': pattern.nombre,
        'html': html,
        'css': f'{theme_css(None, pattern)}\n{SURFACE_CSS}\n{pattern.css or ""}',
        'js': pattern.js or '',
    }
