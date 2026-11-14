import logging

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from DaventProject.middleware import client_ip

"""

Throttles compartidos entre dominios.

"""

logger = logging.getLogger(__name__)


def _pinned_ident(ident, request):
    """
    Pinnea REMOTE_ADDR dentro del ident del throttle: con NUM_PROXIES=1
    DRF toma el ÚLTIMO X-Forwarded-For — correcto tras nginx, pero un
    cliente que llega directo al app (o un proxy que no reescribe XFF)
    puede inyectar y rotar valores para renovar su cuota. Componiendo
    `remote|ident` el bucket siempre incluye la IP de conexión real:
    detrás del proxy es proxy|cliente y en acceso directo es la propia
    IP del atacante — en ambos casos el spoof de XFF no suma cuota.
    """
    remote  =   (request.META.get('REMOTE_ADDR') or '').strip()
    if remote and remote not in (ident or ''):
        return f'{remote}|{ident}'
    return ident


class PublicReadThrottle(AnonRateThrottle):
    """
    Lecturas públicas (webs de clientes, catálogos, planes, locations).

    No pueden compartir el scope 'anon' global (100/day): con CGNAT los
    carriers móviles agrupan miles de usuarios por IP y la cuota se agota
    a los pocos minutos, devolviendo 429 a visitantes legítimos. Scope
    propio holgado (settings DEFAULT_THROTTLE_RATES['public_read']).

    El bucket es POR ENDPOINT (action del view), no uno solo para todo el
    scope: una página de tienda dispara ~8-12 lecturas públicas (ficha,
    pattern meta/document/bridge/script, catálogo, reseñas, legales…) y
    compartir un único contador hacía que ~100 pageviews/hora por IP
    devolvieran 429 — la web del cliente caía en "La tienda está ocupada"
    para todos los visitantes de esa IP (CGNAT, oficinas, QA masivo).
    Con clave por acción cada endpoint conserva su cuota propia y la
    página deja de competir consigo misma.
    """
    scope   =   'public_read'

    def get_ident(self, request):
        #client_ip() aplica la regla de proxy confiable y descarta XFF en
        #acceso directo (REMOTE_ADDR público): el ident ya no es rotable
        #por header — _pinned_ident solo agregaba ruido sin cerrar el hueco.
        return client_ip(request) or super().get_ident(request)

    def get_cache_key(self, request, view):
        ident   =   self.get_ident(request)
        if not ident:
            return None
        #`view.action` es el nombre del @action del ViewSet ('public',
        # 'public_catalog', 'public_pattern_document'…); fuera de un
        # ViewSet se usa la clase vista como bucket.
        action  =   getattr(view, 'action', None) or view.__class__.__name__
        return  'throttle_%s_%s_%s' % (self.scope, action, ident)


class _ResilientThrottleMixin:
    """
    SimpleRateThrottle habla con django.core.cache directamente: si Redis no
    responde, `allow_request` lanza y el endpoint devuelve 500. El rate-limit
    es una defensa, no parte del contrato — sin cache se deja pasar
    (fail-open) y queda el warning en el log; el gate de autenticación sigue
    intacto. El único rate-limit fail-closed es el del login del admin
    (AdminLoginRateLimitMiddleware).
    """
    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as exc:                 # noqa: BLE001 — fail-open deliberado
            logger.warning('throttle %s sin cache (%s) — fail-open',
                           self.__class__.__name__, exc.__class__.__name__)
            return True

    def wait(self):
        try:
            return super().wait()
        except Exception:                        # noqa: BLE001
            return None

    def get_ident(self, request):
        #Misma razón que PublicReadThrottle: client_ip() ya descarta XFF
        #cuando el request no vino de un proxy interno — el bucket no se
        #renueva rotando el header en acceso directo.
        return client_ip(request) or super().get_ident(request)


class ResilientAnonRateThrottle(_ResilientThrottleMixin, AnonRateThrottle):
    pass


class ResilientUserRateThrottle(_ResilientThrottleMixin, UserRateThrottle):
    pass


class MpWebhookThrottle(_ResilientThrottleMixin, AnonRateThrottle):
    """
    Webhooks de Mercado Pago (suscripciones de la plataforma y de cada
    tienda). La autenticación es la firma HMAC, no la sesión — pero los IPs
    de egreso de MP son compartidos entre TODOS los vendedores: con el
    throttle default 'anon' (100/día por IP) todas las notificaciones de
    pago del sistema compartían un solo bucket y una tienda exitosa podía
    dejar sin cupo a las demás (pagos acreditados tarde o nunca).

    Bucket propio por (slug de tienda | 'platform', IP) con rate holgado:
    el volumen legítimo por tienda es ínfimo y el de plataforma acotado —
    un atacante sin el secreto solo quema su propia IP, nunca la de MP.
    """
    scope   =   'mp_webhook'

    def get_cache_key(self, request, view):
        kwargs  =   getattr(request, 'parser_context', {}).get('kwargs') or {}
        slug    =   kwargs.get('slug') or 'platform'
        return  'throttle_%s_%s_%s' % (self.scope, slug, self.get_ident(request))
