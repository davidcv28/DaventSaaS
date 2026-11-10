import logging

from celery import shared_task

"""
Tareas de correo de pedidos (Celery) — e-commerce DAVENT, track F.

Mismo patrón que customers/tasks.py y legalpages/tasks.py: los services
encolan post-commit con `.delay(...)` y estas tasks hacen el envío real
con reintento exponencial. Sin broker (dev/tests)
CELERY_TASK_ALWAYS_EAGER corre la task en el mismo proceso.

`deliver_order_event_email` ya es tolerante a fallos (loguea y traga),
pero el autoretry cubre errores inesperados (DB caída, etc.).
"""

logger  =   logging.getLogger(__name__)

_RETRY  =   dict(autoretry_for = (Exception,), retry_backoff = True, max_retries = 3)


@shared_task(**_RETRY)
def send_order_event_email(order_id : int, event_id : int) -> None:
    """Manda el mail del OrderEvent (estado al comprador / aviso al dueño)."""
    from StoreApp.domains.orders.services.mails import deliver_order_event_email
    deliver_order_event_email(order_id, event_id)
