import re
import secrets

from django.conf import settings
from django.utils import timezone

"""

Dominio propio de la tienda (StoreDomain): normalización del input del
dueño y verificación DNS. El dominio queda 'verified' cuando resuelve
CNAME al host canónico de la plataforma o cuando el TXT
'_davent-verify.<dominio>' contiene su token. Si la consulta DNS no está
disponible (sin dnspython o sin red) se responde 'pending', nunca 'failed':
'failed' solo significa que el DNS respondió y no apunta donde debe.

"""
#=========================================
# HELPERS
#=========================================
_DOMAIN_LABEL   =   re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
def public_domain():
    """Host canónico al que deben apuntar los CNAME de los dominios propios."""
    return getattr(settings, 'PUBLIC_DOMAIN', 'davent.com.ar').strip().lower().strip('.')
def normalize_domain(raw):
    """
    Limpia el input del usuario ('https://www.MiTienda.com/path' →
    'mitienda.com'): sin esquema, path, puerto ni 'www.' inicial, en
    minúsculas y punycode (idna). Devuelve '' si el formato no es un
    dominio válido con al menos un punto.
    """
    value   =   str(raw or '').strip().lower()
    if not value or len(value) > 253:
        return ''
    #El usuario suele pegar la URL completa: se recorta esquema, path y query.
    value   =   re.sub(r'^[a-z][a-z0-9+.-]*://', '', value)
    value   =   value.split('/')[0].split('?')[0].split('#')[0]
    #Sin puerto (host:8080) — un IPv6 literal no es dominio de cliente.
    value   =   value.split(':')[0].rstrip('.')
    if value.startswith('www.'):
        value   =   value[4:]
    try:
        value   =   value.encode('idna').decode('ascii')
    except (UnicodeError, ValueError):
        return ''
    labels  =   value.split('.')
    if len(labels) < 2 or not all(_DOMAIN_LABEL.match(piece) for piece in labels):
        return ''
    return value
def is_platform_domain(domain):
    """El dominio propio no puede ser la plataforma misma ni un subdominio de ella."""
    base    =   public_domain()
    return domain == base or domain.endswith(f'.{base}')
def new_verify_token():
    return secrets.token_hex(16)
def verify_txt_name(domain):
    return f'_davent-verify.{domain}'
def check_domain(store_domain):
    """
    Consulta DNS del dominio: True si el CNAME apunta al host canónico o
    el TXT de verificación contiene el token. False si el DNS respondió
    sin coincidencias. Lanza la excepción de red si el resolver no existe.
    """
    import dns.exception
    import dns.resolver
    target  =   public_domain()
    resolver    =   dns.resolver.Resolver()
    resolver.lifetime   =   8.0
    resolver.timeout    =   4.0
    #CNAME: www.mitienda.com o mitienda.com -> davent.com.ar.
    try:
        answers =   resolver.resolve(store_domain.domain, 'CNAME')
        for answer in answers:
            name    =   str(answer.target).rstrip('.').lower()
            if name == target or name.endswith(f'.{target}'):
                return True
    except dns.exception.DNSException:
        pass
    #TXT alternativo (registrars sin CNAME en el apex): el token prueba
    #propiedad aunque todavía no apunte el tráfico.
    try:
        answers =   resolver.resolve(verify_txt_name(store_domain.domain), 'TXT')
        for answer in answers:
            text    =   b''.join(answer.strings).decode('utf-8', 'ignore').strip()
            if text == store_domain.verify_token:
                return True
    except dns.exception.DNSException:
        pass
    return False
def refresh_status(store_domain):
    """
    Re-corre la verificación y persiste status/verified_at/last_checked_at.
    Errores de red/resolver -> queda 'pending' (reintento silencioso).
    """
    store_domain.last_checked_at    =   timezone.now()
    try:
        ok  =   check_domain(store_domain)
    except Exception:
        ok  =   None
    if ok:
        store_domain.status         =   store_domain.STATUS_VERIFIED
        store_domain.verified_at    =   store_domain.verified_at or timezone.now()
    elif ok is False:
        store_domain.status         =   store_domain.STATUS_FAILED
        store_domain.verified_at    =   None
    else:
        store_domain.status         =   store_domain.STATUS_PENDING
        store_domain.verified_at    =   None
    store_domain.save(update_fields = ['status', 'verified_at', 'last_checked_at'])
    return store_domain
def serialize_domain(store_domain):
    """Payload de la sección "Mi dirección web" (panel del dueño)."""
    if store_domain is None:
        return None
    return {
        'domain'        :   store_domain.domain,
        'status'        :   store_domain.status,
        'txt_name'      :   verify_txt_name(store_domain.domain),
        'txt_value'     :   store_domain.verify_token,
        'cname_target'  :   public_domain(),
        'verified_at'   :   store_domain.verified_at,
        'last_checked_at':  store_domain.last_checked_at,
        'created_at'    :   store_domain.created_at,
    }
def resolve_slug(domain):
    """Slug de la tienda dueña de un dominio verificado y publicable ('' si no)."""
    from StoreApp.domains.stores.models import StoreDomain
    store_domain    =   (
        StoreDomain.objects
        .select_related('store')
        .filter(domain = domain, status = StoreDomain.STATUS_VERIFIED, store__is_published = True, store__is_blocked = False)
        .first()
    )
    return store_domain.store.slug if store_domain else ''
