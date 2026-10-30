import ipaddress

from django.conf import settings
from django.http import HttpResponse

from DaventProject.cache_utils import (
    CacheUnavailable,
    cache_add_strict,
    cache_incr_strict,
    cache_set_strict,
)

"""

Middleware transversales del proyecto.

"""


def _trusted_proxies() -> int:
    #Misma fuente que el throttle de DRF (NUM_PROXIES): la cantidad de saltos
    #que agregamos NOSOTROS. 0 = sin proxy confiable.
    try:
        return max(int(settings.REST_FRAMEWORK.get('NUM_PROXIES') or 0), 0)
    except (AttributeError, TypeError, ValueError):
        return 0


def _valid_ip(value : str) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return ''


def client_ip(request) -> str:
    """
    IP del cliente con la MISMA regla que el throttle de DRF: se toma el
    X-Forwarded-For que agregó el proxy confiable (NUM_PROXIES saltos), nunca
    el primero — el cliente puede inyectar ese header y falsear la IP con la
    que se cuenta el rate-limit (bypass de fuerza bruta). Sin proxies
    confiables el XFF se ignora por completo y manda REMOTE_ADDR.
    """
    proxies     =   _trusted_proxies()
    forwarded   =   request.META.get('HTTP_X_FORWARDED_FOR') or ''
    if proxies and forwarded:
        parts   =   [p.strip() for p in forwarded.split(',') if p.strip()]
        if len(parts) >= proxies:
            ip  =   _valid_ip(parts[-proxies])
            if ip:
                return ip
    return _valid_ip(request.META.get('REMOTE_ADDR') or '') or '-'


class ContentSecurityPolicyMiddleware:
    """
    CSP de respaldo para las respuestas HTML que sirve Django (admin de
    Django, browsable API de DRF, páginas de error). Defensa en profundidad:
    la SPA ya sale con su propia CSP más estricta (urls.py -> vista spa, y
    nginx en Docker la publica aparte); este middleware solo rellena el
    header cuando ninguna capa anterior lo seteó, para despliegues sin nginx
    (serverless con whitenoise) o un proxy mal configurado.

    'unsafe-inline' en script/style es inevitable: el admin de Django y la
    browsable API usan scripts y estilos inline. La política igual acota los
    orígenes de recursos externos (object-src 'none', base-uri, frame y
    form acotados).
    """
    POLICY  =   (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://accounts.google.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://accounts.google.com; "
        "frame-src 'self' https://maps.google.com https://www.google.com https://accounts.google.com; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
    )

    def __init__(self, get_response):
        self.get_response   =   get_response

    def __call__(self, request):
        response    =   self.get_response(request)
        content_type    =   response.headers.get('Content-Type', '')
        #Solo aplica a HTML: una CSP sobre JSON/binario no protege nada y el
        #header ya seteado (SPA, futuras vistas) nunca se pisa.
        if 'text/html' in content_type and 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] =   self.POLICY
        return response


class SecurityHeadersMiddleware:
    """
    Cabeceras que Django no pone por default y aplican a TODA respuesta
    (HTML, JSON, binarios):

      - Permissions-Policy: apaga APIs del navegador que la app no usa
        (micrófono, USB, serial, pantalla). cámara/geolocalización/clipboard
        quedan en (self) porque el panel las usa (preview de fotos,
        "copiar link"). Sin esta cabecera cualquier origen puede pedirlas.
      - X-Permitted-Cross-Domain-Policies: corta los crossdomain.xml viejos
        (Flash/PDF) que permitían leer contenido del dominio.
      - X-Robots-Tag en el admin: el login y el panel no deben indexarse
        aunque el path se filtre (ADMIN_URL ofuscado + robots).
    """
    POLICY  =   (
        "camera=(self), microphone=(), geolocation=(self), payment=(), "
        "usb=(), serial=(), midi=(), hid=(), display-capture=(), "
        "magnetometer=(), gyroscope=(), accelerometer=(), "
        "clipboard-write=(self), browsing-topics=()"
    )

    def __init__(self, get_response):
        self.get_response   =   get_response
        self.admin_prefix   =   f'/{settings.ADMIN_URL.strip("/")}/'

    def __call__(self, request):
        response    =   self.get_response(request)
        response.setdefault('Permissions-Policy', self.POLICY)
        response.setdefault('X-Permitted-Cross-Domain-Policies', 'none')
        if request.path.startswith(self.admin_prefix):
            response.setdefault('X-Robots-Tag', 'noindex, nofollow, noarchive')
        return response


class AdminLoginRateLimitMiddleware:
    """
    Fuerza bruta contra el login del admin de Django: admin.site.login no
    pasa por los throttles de DRF, así que el POST a <ADMIN_URL>/login/ se
    acota por IP acá. La ofuscación de ADMIN_URL no reemplaza un límite —
    cualquier path obvio agota intentos y fuerza cooldown.

    La IP sale de client_ip() (XFF del proxy confiable, no el primero): con
    el header crudo un atacante rota el X-Forwarded-For y nunca llega al
    límite. El contador se crea con cache.add + incr (atómico en Redis y
    locmem): el incr-sobre-missing anterior permitía que dos requests
    concurrentes reiniciaran la ventana.
    """
    LIMIT           =   10
    WINDOW_SECONDS  =   300

    def __init__(self, get_response):
        self.get_response   =   get_response
        self.login_path     =   f'/{settings.ADMIN_URL.strip("/")}/login/'.rstrip('/')

    def __call__(self, request):
        if request.method == 'POST' and request.path.rstrip('/') == self.login_path:
            ip      =   client_ip(request)
            if ip != '-':
                key =   f'admin-login:{ip}'
                #FAIL-CLOSED: sin cache no se puede contar intentos — servir
                #el login del admin a ciegas habilita fuerza bruta. 503 con
                #Retry-After en vez de un 500 con traza.
                try:
                    if cache_add_strict(key, 1, self.WINDOW_SECONDS):
                        attempts    =   1
                    else:
                        try:
                            attempts    =   cache_incr_strict(key)
                        except ValueError:
                            #La clave venció entre el add y el incr (o el
                            #backend no soporta incr sobre ella).
                            cache_set_strict(key, 1, self.WINDOW_SECONDS)
                            attempts    =   1
                except CacheUnavailable:
                    response    =   HttpResponse('Servicio temporalmente no disponible.', status = 503)
                    response['Retry-After'] =   str(self.WINDOW_SECONDS)
                    return response
                if attempts > self.LIMIT:
                    response    =   HttpResponse('Demasiados intentos. Probá más tarde.', status = 429)
                    response['Retry-After'] =   str(self.WINDOW_SECONDS)
                    return response
        return self.get_response(request)
