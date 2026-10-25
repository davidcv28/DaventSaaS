from rest_framework.throttling import AnonRateThrottle
"""

Throttles compartidos entre dominios.

"""


class PublicReadThrottle(AnonRateThrottle):
    """
    Lecturas públicas (webs de clientes, catálogos, planes, locations).

    No pueden compartir el scope 'anon' global (100/day): con CGNAT los
    carriers móviles agrupan miles de usuarios por IP y la cuota se agota
    a los pocos minutos, devolviendo 429 a visitantes legítimos. Scope
    propio holgado (settings DEFAULT_THROTTLE_RATES['public_read']).
    """
    scope   =   'public_read'
