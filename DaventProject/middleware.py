from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

"""

Middleware transversales del proyecto.

"""


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
