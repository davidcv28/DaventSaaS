from django.core.exceptions import ValidationError as DjValidationError

from StoreApp.domains.stores.models import StoreCustomization
from StoreApp.domains.stores.services import plan_benefits_of

"""

Servicios del dominio Services.

Reglas de las páginas de la web (site_templates) y del catálogo de
servicios del cliente. Los beneficios del plan vigente
(SuscriptionApp/benefits) son la fuente de verdad: 'has_services_site'
habilita la página Servicios y 'max_site_templates' fija cuántas páginas
puede tener la web (None = todas). Básico queda con landing+catálogo
como única combinación válida: sin el flag no puede elegir 'services' y
el tope 2 agota las otras dos.

"""
#=========================================
# SITE TEMPLATES (páginas que componen la web pública)
#=========================================
SITE_TEMPLATES          =   StoreCustomization.SITE_TEMPLATES
#Conjunto por defecto: la web arranca con portada + catálogo (misma
#conducta que el site_mode='both' que reemplaza este campo).
DEFAULT_SITE_TEMPLATES  =   ('landing', 'catalog')
#Tope defensivo de servicios por tienda (no es un beneficio de plan).
SERVICES_MAX            =   24
#=========================================
# PLAN BENEFITS SAFE (profile=None -> sin beneficios)
#=========================================
def _benefits_of(profile):
    """plan_benefits_of tolerante: sin perfil devuelve {} (fail-closed)."""
    return plan_benefits_of(profile) if profile is not None else {}
#=========================================
# SERVICES ENABLED (flag has_services_site del plan)
#=========================================
def services_enabled(profile):
    """La página Servicios se habilita con el flag 'has_services_site' (Estándar+)."""
    return bool(_benefits_of(profile).get('has_services_site'))
#=========================================
# SITE TEMPLATES LIMIT (cupo max_site_templates del plan)
#=========================================
def site_templates_limit(profile):
    """
    Máximo de páginas de la web según el plan vigente. None = sin tope
    (las tres). Sin el beneficio declarado queda el piso histórico: 2
    (la web mínima siempre fue portada+catálogo).
    """
    benefits    =   _benefits_of(profile)
    if 'max_site_templates' not in benefits:
        return 2
    return benefits['max_site_templates']
def allowed_site_templates(profile):
    """
    Claves de SITE_TEMPLATES que el plan vigente puede elegir: 'services'
    exige el flag has_services_site; landing/catalog van con cualquier
    suscripción activa (los planes sin has_customization tampoco llegan
    acá: el PATCH de customization ya los frena antes).
    """
    allowed     =   [key for key in SITE_TEMPLATES if key != 'services']
    if services_enabled(profile):
        allowed     =   list(SITE_TEMPLATES)
    return tuple(allowed)
#=========================================
# NORMALIZE / VALIDATE (whitelist cerrada + reglas de plan)
#=========================================
def normalize_site_templates(value):
    """
    Lista limpia de páginas: solo claves del catálogo SITE_TEMPLATES, sin
    repetidas, en el orden canónico del catálogo. Cualquier otra cosa
    sale como lista vacía (el caller decide el fallback).
    """
    if not isinstance(value, (list, tuple)):
        return []
    chosen      =   {str(item) for item in value}
    return [key for key in SITE_TEMPLATES if key in chosen]
def validate_site_templates(profile, value):
    """
    Normaliza y fuerza las reglas de plan sobre el set de páginas:
    - la web no puede quedar vacía
    - 'services' exige has_services_site
    - la cantidad no puede superar max_site_templates
    Levanta Django ValidationError con la lista de mensajes (el
    serializer de customization lo reexpone como error de campo).
    """
    templates   =   normalize_site_templates(value)
    if not templates:
        raise DjValidationError(['Tu web necesita al menos una página.'])
    errors      =   []
    if 'services' in templates and not services_enabled(profile):
        errors.append('La página de servicios está disponible desde el plan Estándar.')
    limit       =   site_templates_limit(profile)
    if limit is not None and len(templates) > limit:
        errors.append(f'Tu plan admite hasta {limit} páginas en tu web. Pasate a un plan superior para sumar las tres.')
    if errors:
        raise DjValidationError(errors)
    return templates
def effective_site_templates(store):
    """
    Páginas que la web pública muestra HOY: lo que el dueño guardó,
    intersectado con lo que su plan vigente permite y recortado al cupo.
    Si la tienda bajó de plan, 'services' sale sola aunque siga guardada
    (vuelve al subir de plan, como las opiniones de producto). Si el
    resultado queda vacío (fila vieja o corrupta) cae al default.
    """
    customization   =   getattr(store, 'customization', None)
    stored          =   normalize_site_templates(getattr(customization, 'site_templates', None) or DEFAULT_SITE_TEMPLATES)
    allowed         =   allowed_site_templates(store.user)
    effective       =   [key for key in stored if key in allowed]
    limit           =   site_templates_limit(store.user)
    if limit is not None:
        effective       =   effective[:limit]
    return effective or list(DEFAULT_SITE_TEMPLATES)
def site_mode_of(templates):
    """
    site_mode derivado (compat con las plantillas del catálogo y el
    layout público, que leen custom.site_mode): 'catalog' cuando no hay
    portada (el home redirige a otra página), 'marketing' cuando no hay
    catálogo, 'both' en cualquier otro caso.
    """
    if 'landing' not in templates:
        return 'catalog'
    return 'both' if 'catalog' in templates else 'marketing'
#=========================================
# SERVICES CATALOG (ítems de la página Servicios del dueño)
#=========================================
def can_add_service(store):
    """True si la tienda no llegó al tope defensivo de servicios."""
    return store.service_items.count() < SERVICES_MAX
def apply_service_order(queryset, order):
    """
    Reasigna `position` según la lista de ids recibida (mismo criterio
    que el orden del carrusel/galería): los servicios que el payload no
    menciona conservan su orden relativo al final y los ids repetidos se
    ignoran — un PATCH malicioso o duplicado no puede corromper el orden.
    """
    services    =   {service.id: service for service in queryset}
    seen        =   set()
    position    =   0
    for service_id in order:
        service =   services.get(service_id)
        if service is None or service.id in seen:
            continue
        seen.add(service.id)
        if service.position != position:
            service.position    =   position
            service.save(update_fields = ['position'])
        position    +=  1
    for service in sorted((s for s in services.values() if s.id not in seen), key = lambda s: (s.position, s.id)):
        if service.position != position:
            service.position    =   position
            service.save(update_fields = ['position'])
        position    +=  1
