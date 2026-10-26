from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

"""

Middleware transversales del proyecto.

"""


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


class AdminLoginRateLimitMiddleware:
    """
    Fuerza bruta contra el login del admin de Django: admin.site.login no
    pasa por los throttles de DRF, así que el POST a <ADMIN_URL>/login/ se
    acota por IP acá. La ofuscación de ADMIN_URL no reemplaza un límite —
    cualquier path obvio agota intentos y fuerza cooldown.
    """
    LIMIT           =   10
    WINDOW_SECONDS  =   300

    def __init__(self, get_response):
        self.get_response   =   get_response
        self.login_path     =   f'/{settings.ADMIN_URL.strip("/")}/login/'

    def __call__(self, request):
        if request.method == 'POST' and request.path == self.login_path:
            forwarded   =   request.META.get('HTTP_X_FORWARDED_FOR') or ''
            #Último hop: el que agregó el proxy confiable (misma regla que
            #NUM_PROXIES / _client_ip).
            ip          =   forwarded.split(',')[-1].strip() or request.META.get('REMOTE_ADDR') or ''
            if ip:
                key     =   f'admin-login:{ip}'
                try:
                    attempts    =   cache.incr(key)
                except ValueError:
                    cache.set(key, 1, self.WINDOW_SECONDS)
                    attempts    =   1
                if attempts > self.LIMIT:
                    return HttpResponse('Demasiados intentos. Probá más tarde.', status = 429)
        return self.get_response(request)
