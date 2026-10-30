import logging

from django.core.cache import cache

"""

Acceso resiliente al cache (Redis en producción, locmem en tests/dev).

Redis es una dependencia de infraestructura: si se cae o llega a maxmemory,
un `cache.add/incr` crudo propaga la excepción y convierte cualquier endpoint
con throttle, dedup o contador en un 500. Estos helpers centralizan la
política:

  - fail-OPEN (log + valor por defecto): throttles de DRF, dedup de webhooks,
    contador de visitas, cache del catálogo público y de beneficios — perder
    una entrada de cache no puede tumbar el request.
  - fail-CLOSED (la excepción sube, el caller responde 503): rate-limit del
    login del admin y lockout de login de la API — sin cache no hay forma de
    contar intentos y servir el login a ciegas habilita fuerza bruta.

Los valores de timeout son los mismos que usaba el acceso directo: el helper
no cambia la semántica, solo el manejo de errores.

"""
logger = logging.getLogger(__name__)


class CacheUnavailable(Exception):
    """El backend de cache no respondió (Redis caído/lleno)."""


def _warn(action : str, key : str, exc : Exception) -> None:
    logger.warning('cache %s falló (key=%s): %s — fail-open', action, key, exc.__class__.__name__)


#=========================================
# FAIL-OPEN
#=========================================
def cache_get(key, default = None):
    try:
        return cache.get(key, default)
    except Exception as exc:                     # noqa: BLE001 — fail-open deliberado
        _warn('get', key, exc)
        return default


def cache_get_many(keys):
    try:
        return cache.get_many(list(keys))
    except Exception as exc:                     # noqa: BLE001
        _warn('get_many', ','.join(str(k) for k in keys), exc)
        return {}


def cache_set(key, value, timeout = None) -> bool:
    try:
        cache.set(key, value, timeout)
        return True
    except Exception as exc:                     # noqa: BLE001
        _warn('set', key, exc)
        return False


def cache_add(key, value, timeout = None) -> bool:
    try:
        return bool(cache.add(key, value, timeout))
    except Exception as exc:                     # noqa: BLE001
        _warn('add', key, exc)
        return False


def cache_incr(key):
    try:
        return cache.incr(key)
    except ValueError:
        #La clave no existe (o no soporta incr): el caller decide reabrirla.
        raise
    except Exception as exc:                     # noqa: BLE001
        _warn('incr', key, exc)
        return None


def cache_delete(key) -> bool:
    try:
        cache.delete(key)
        return True
    except Exception as exc:                     # noqa: BLE001
        _warn('delete', key, exc)
        return False


#=========================================
# FAIL-CLOSED (el caller responde 503)
#=========================================
def cache_get_strict(key, default = None):
    try:
        return cache.get(key, default)
    except Exception as exc:                     # noqa: BLE001
        raise CacheUnavailable(f'cache get falló: {exc.__class__.__name__}') from exc


def cache_add_strict(key, value, timeout = None) -> bool:
    try:
        return bool(cache.add(key, value, timeout))
    except Exception as exc:                     # noqa: BLE001
        raise CacheUnavailable(f'cache add falló: {exc.__class__.__name__}') from exc


def cache_incr_strict(key):
    try:
        return cache.incr(key)
    except ValueError:
        raise
    except Exception as exc:                     # noqa: BLE001
        raise CacheUnavailable(f'cache incr falló: {exc.__class__.__name__}') from exc


def cache_set_strict(key, value, timeout = None) -> None:
    try:
        cache.set(key, value, timeout)
    except Exception as exc:                     # noqa: BLE001
        raise CacheUnavailable(f'cache set falló: {exc.__class__.__name__}') from exc
