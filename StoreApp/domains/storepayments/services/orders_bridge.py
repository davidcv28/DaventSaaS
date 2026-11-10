"""
Puente lazy hacia el dominio `orders` (track B — en desarrollo paralelo).

Order / OrderItem / OrderEvent y los services `mark_order_paid`,
`mark_order_refunded` y `events.append_event` los implementa el track B en
`StoreApp.domains.orders`. Como orders todavía no existe en el árbol, acá
TODO se resuelve por import perezoso DENTRO de cada llamada:

- `order_model()` usa `apps.get_model('orders', 'Order')` en runtime —
  `manage.py check` y `makemigrations` de storepayments no necesitan que
  orders tenga modelos.
- `mark_paid`/`mark_refunded` importan
  `StoreApp.domains.orders.services.payments` en el momento de uso y lo
  reintentan en cada llamada (si el módulo aparece después, funciona sin
  tocar este archivo).
- `append_event` es best-effort: si orders aún no expone
  `services.events.append_event`, solo loguea y sigue — un fallo del
  event log NUNCA debe romper el webhook de cobro.

Si orders no está disponible levanta `OrdersUnavailableError`; las vistas
lo traducen a 503/404 controlado y el webhook lo loguea y acusa 200 (MP
reintentaría para siempre contra un problema de código, no de datos).
"""
import importlib
import logging

from django.apps import apps

logger  =   logging.getLogger(__name__)

ORDER_MODEL_PATH        =   'orders.Order'
PAYMENTS_SERVICE_PATH   =   'StoreApp.domains.orders.services.payments'
EVENTS_SERVICE_PATH     =   'StoreApp.domains.orders.services.events'


class OrdersUnavailableError(Exception):
    """El dominio orders no está migrado/no expone el modelo Order todavía."""


def order_model():
    """Resuelve orders.Order en runtime (LookupError -> OrdersUnavailableError)."""
    app_label, _, model_name =   ORDER_MODEL_PATH.partition('.')
    try:
        return apps.get_model(app_label, model_name)
    except (LookupError, ValueError) as exc:
        raise OrdersUnavailableError('El dominio de pedidos no está disponible') from exc


def find_order_by_token(store, tracking_token):
    """
    Pedido por su identificador público, ACOTADO a la tienda del webhook/
    checkout (IDOR: un token válido de otra tienda nunca matchea acá).
    """
    Order   =   order_model()
    return Order.objects.filter(store_id = store.id, tracking_token = tracking_token).first()


def get_order_for_store(store, order_id):
    """Pedido por PK solo si pertenece a `store` (refund del dueño — IDOR -> None)."""
    Order   =   order_model()
    return Order.objects.filter(store_id = store.id, pk = order_id).first()


def _load_callable(module_path, attr):
    try:
        module  =   importlib.import_module(module_path)
        return getattr(module, attr)
    except (ImportError, AttributeError) as exc:
        #El dominio orders existe pero aún no expone el service (o el
        #módulo no está): mismo tratamiento que la falta del modelo.
        raise OrdersUnavailableError(f'{module_path}.{attr} no disponible') from exc


def mark_paid(order, *, source = 'manual', reference = '', actor = None):
    """
    Contrato track B: `mark_order_paid(order, *, source='manual'|'mp',
    reference='', actor=None) -> Order` — idempotente, hace la transición
    PAID->PACKING y descuenta stock. Se importa en cada llamada para no
    romper storepayments mientras orders está en desarrollo.
    """
    fn      =   _load_callable(PAYMENTS_SERVICE_PATH, 'mark_order_paid')
    return fn(order, source = source, reference = reference, actor = actor)


def mark_refunded(order, *, actor = None):
    """Contrato track B: `mark_order_refunded(order, *, actor=None)`."""
    fn      =   _load_callable(PAYMENTS_SERVICE_PATH, 'mark_order_refunded')
    return fn(order, actor = actor)


def append_event(order, kind, message = '', actor = None, **extra):
    """
    Registra un OrderEvent si el dominio orders ya expone
    `services.events.append_event(order, kind=..., ...)`. Best-effort:
    cualquier ImportError/AttributeError se loguea y devuelve None — el
    cobro no depende de la bitácora.
    """
    try:
        module  =   importlib.import_module(EVENTS_SERVICE_PATH)
        fn      =   getattr(module, 'append_event', None)
        if fn is None:
            logger.info('orders.services.events.append_event no existe todavía (kind=%s)', kind)
            return None
        return fn(order, kind = kind, message = message, actor = actor, **extra)
    except Exception:
        logger.warning('No se pudo registrar OrderEvent kind=%s', kind, exc_info = True)
        return None
