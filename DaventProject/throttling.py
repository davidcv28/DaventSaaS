import logging

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

"""

Throttles compartidos entre dominios.

"""

logger = logging.getLogger(__name__)


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


class ResilientAnonRateThrottle(_ResilientThrottleMixin, AnonRateThrottle):
    pass


class ResilientUserRateThrottle(_ResilientThrottleMixin, UserRateThrottle):
    pass
