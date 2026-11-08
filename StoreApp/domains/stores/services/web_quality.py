"""
Checklist "Calidad de tu web" (dashboard del dueño).

`web_quality_report(store)` devuelve `{score, checks}`: score 0-100 = suma
de los pesos de los checks ok (los pesos son explícitos y suman 100) y una
lista de checks `{id, weight, ok, label, action, tab}` donde `tab` es el id
de sección de DashboardView.vue a la que navega el botón de acción.

Sin N+1: la tienda llega con select_related('customization', 'user__*') y
los agregados de productos salen de una sola query anotada.
"""
from django.db.models import Count, Q
from django.db.models.functions import Length

from StoreApp.domains.catalog.models import Product
from StoreApp.domains.design.seed import DEFAULT_PATTERN, DEFAULT_STYLE
from StoreApp.domains.stores.models import StoreCustomization

#Umbrales del checklist (los mismos que el copy de cada check promete).
PRODUCTS_MIN             =   8       #productos activos mínimos
PRODUCTS_RATIO_MIN       =   0.8     #fracción con foto / con descripción larga
PRODUCT_DESC_MIN         =   120     #caracteres mínimos de descripción
ABOUT_TEXT_MIN           =   200     #caracteres mínimos de "Sobre nosotros"
#Diseño "no elegido": la tienda nueva arranca en la plantilla default
#('raiz' = TEMPLATE_DEFAULT, alias 'esencial' = DEFAULT_PATTERN del
#catálogo) y sin estilo propio (style.id vacío o el estilo 'base').
DEFAULT_TEMPLATES        =   frozenset({'', StoreCustomization.TEMPLATE_DEFAULT, DEFAULT_PATTERN})
DEFAULT_STYLES           =   frozenset({'', DEFAULT_STYLE})


def _product_stats(store):
    """(activos, con_foto, con_descripcion_larga) en una sola query."""
    agg     =   (
        Product.objects
        .filter(store = store, is_active = True)
        .annotate(_desc_len = Length('description'))
        .aggregate(
            total   =   Count('id'),
            photo   =   Count('id', filter = ~Q(image_key = '')),
            desc    =   Count('id', filter = Q(_desc_len__gte = PRODUCT_DESC_MIN)),
        )
    )
    return agg['total'], agg['photo'], agg['desc']


def _design_chosen(customization):
    """True si el dueño eligió un diseño/estilo distinto del default."""
    if customization is None:
        return False
    template    =   (customization.template or '').strip()
    if template not in DEFAULT_TEMPLATES:
        return True
    theme       =   customization.site_theme if isinstance(customization.site_theme, dict) else {}
    style       =   theme.get('style') if isinstance(theme.get('style'), dict) else {}
    return str(style.get('id') or '').strip() not in DEFAULT_STYLES


def web_quality_report(store):
    """
    Score 0-100 + checks accionables de la web del cliente.

    `store` debe venir con select_related('customization', 'user__city',
    'user__province'): el perfil (store.user) aporta domicilio/teléfono.
    """
    customization   =   getattr(store, 'customization', None)
    profile         =   store.user
    cust            =   customization  # alias corto para las lecturas

    total, photo, desc =   _product_stats(store)
    photo_ratio         =   (photo / total) if total else 0.0
    desc_ratio          =   (desc / total) if total else 0.0

    theme               =   (cust.site_theme if cust and isinstance(cust.site_theme, dict) else {}) or {}
    socials             =   [getattr(cust, field, '') for field in ('instagram', 'tiktok', 'facebook')] if cust else []
    has_address         =   bool((getattr(profile, 'address', '') or '').strip())
    show_location       =   bool(cust.show_location) if cust else False

    checks              =   [
        {
            'id'        :   'logo',
            'weight'    :   10,
            'ok'        :   bool(cust and cust.logo_key),
            'label'     :   'Subí el logo de tu negocio',
            'action'    :   'Subir logo',
            'tab'       :   'photos',
        },
        {
            'id'        :   'cover',
            'weight'    :   10,
            'ok'        :   bool(cust and cust.cover_key),
            'label'     :   'Subí una foto de portada',
            'action'    :   'Subir portada',
            'tab'       :   'photos',
        },
        {
            'id'        :   'products_min',
            'weight'    :   12,
            'ok'        :   total >= PRODUCTS_MIN,
            'label'     :   f'Cargá al menos {PRODUCTS_MIN} productos activos',
            'action'    :   'Cargar productos',
            'tab'       :   'catalogs',
        },
        {
            'id'        :   'products_photo',
            'weight'    :   8,
            'ok'        :   total > 0 and photo_ratio >= PRODUCTS_RATIO_MIN,
            'label'     :   'Que el 80% de tus productos tenga foto',
            'action'    :   'Revisar fotos',
            'tab'       :   'catalogs',
        },
        {
            'id'        :   'products_desc',
            'weight'    :   8,
            'ok'        :   total > 0 and desc_ratio >= PRODUCTS_RATIO_MIN,
            'label'     :   f'Que el 80% tenga una descripción de {PRODUCT_DESC_MIN}+ caracteres',
            'action'    :   'Mejorar descripciones',
            'tab'       :   'catalogs',
        },
        {
            'id'        :   'about',
            'weight'    :   6,
            'ok'        :   bool(cust and len((cust.about_text or '').strip()) >= ABOUT_TEXT_MIN),
            'label'     :   f'Contá quién sos en "Sobre nosotros" ({ABOUT_TEXT_MIN}+ caracteres)',
            'action'    :   'Escribir sobre nosotros',
            'tab'       :   'company',
        },
        {
            'id'        :   'hours',
            'weight'    :   6,
            'ok'        :   bool(cust and cust.hours),
            'label'     :   'Cargá tus horarios de atención',
            'action'    :   'Cargar horarios',
            'tab'       :   'company',
        },
        {
            'id'        :   'address',
            'weight'    :   8,
            'ok'        :   has_address and show_location,
            'label'     :   'Mostrá tu dirección en el mapa',
            'action'    :   'Cargar dirección',
            'tab'       :   'settings',
        },
        {
            'id'        :   'contact',
            'weight'    :   8,
            'ok'        :   bool((cust and cust.whatsapp) or getattr(profile, 'phone', '')),
            'label'     :   'Agregá tu WhatsApp o teléfono',
            'action'    :   'Agregar contacto',
            'tab'       :   'company',
        },
        {
            'id'        :   'social',
            'weight'    :   6,
            'ok'        :   any(str(value or '').strip() for value in socials),
            'label'     :   'Sumá al menos una red social',
            'action'    :   'Agregar redes',
            'tab'       :   'company',
        },
        {
            'id'        :   'design',
            'weight'    :   10,
            'ok'        :   _design_chosen(cust),
            'label'     :   'Elegí un diseño para tu web',
            'action'    :   'Elegir diseño',
            'tab'       :   'design',
        },
        {
            'id'        :   'theme',
            'weight'    :   8,
            'ok'        :   bool(theme),
            'label'     :   'Publicá un tema visual para tu web',
            'action'    :   'Elegir tema',
            'tab'       :   'design',
        },
    ]
    score   =   sum(check['weight'] for check in checks if check['ok'])
    return {'score': score, 'checks': checks}
