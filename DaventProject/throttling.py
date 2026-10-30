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
    """
    scope   =   'public_read'


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
