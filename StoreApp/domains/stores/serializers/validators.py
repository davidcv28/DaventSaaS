import re
"""

Validadores de campo del dominio Stores.

"""
#=========================================
# SLUG (link público)
#=========================================
# Palabras que no pueden usarse como link: pisan rutas del sistema
# o del sitio público (frontend + API + admin).
RESERVED_SLUGS = {
    'admin', 'administracion', 'api', 'app', 'auth', 'ayuda', 'catalogo',
    'catalog', 'contacto', 'dashboard', 'facturas', 'help', 'invoices',
    'legal', 'login', 'logout', 'mail', 'media', 'panel', 'pagos',
    'payments', 'planes', 'plans', 'privacidad', 'registro', 'register',
    'soporte', 'static', 'store', 'suscriptions', 'terminos', 'tienda',
    'token', 'web', 'www',
}
SLUG_PATTERN   =   re.compile(r'^[a-z0-9](?:[a-z0-9-]{1,58}[a-z0-9])?$')

def validate_slug_format(slug):
    """Formato: minúsculas, números y guiones internos. 3 a 60 caracteres."""
    return bool(SLUG_PATTERN.match(slug))

def validate_slug_available(slug):
    from StoreApp.domains.stores.models import Store
    return not Store.objects.filter(slug = slug).exists()
#=========================================
# CONTACTO PÚBLICO (personalización de la web)
#=========================================
# WhatsApp: solo dígitos con '+' inicial opcional (formato wa.me).
WHATSAPP_PATTERN   =   re.compile(r'^\+?\d{8,15}$')
# Instagram: handle sin '@' (letras, números, puntos y guiones bajos).
INSTAGRAM_PATTERN  =   re.compile(r'^[a-zA-Z0-9](?:[a-zA-Z0-9._]{0,28}[a-zA-Z0-9])?$')

def validate_whatsapp(value):
    """Número público de contacto: 8 a 15 dígitos, '+' opcional al inicio."""
    return bool(WHATSAPP_PATTERN.match(value))

def validate_instagram(value):
    """Handle de Instagram sin '@', 2 a 30 caracteres."""
    return bool(INSTAGRAM_PATTERN.match(value))
