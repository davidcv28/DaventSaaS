import logging

from celery import shared_task

"""
Tareas Celery del dominio memberships (autodiscovery: `<app>.tasks`).

`send_membership_expiry_notice` la encola el comando
`membership_expiry_notices` (cron diario) por cada suscripción que
vence en la ventana — el worker hace el SMTP con reintento exponencial.
Sin broker (dev/tests) CELERY_TASK_ALWAYS_EAGER corre en el proceso.

`send_membership_expiry_email` ya es tolerante a fallos SMTP; el
autoretry cubre errores inesperados (DB caída, etc.).
"""

logger  =   logging.getLogger(__name__)

_RETRY  =   dict(autoretry_for = (Exception,), retry_backoff = True, max_retries = 3)


@shared_task(**_RETRY)
def send_membership_expiry_notice(subscription_id : int) -> None:
    """Manda el aviso de membresía por vencer (una suscripción por task)."""
    from StoreApp.domains.memberships.models import StoreSubscription
    from StoreApp.domains.memberships.services.mails import send_membership_expiry_email
    subscription   =   (
        StoreSubscription.objects
        .filter(pk = subscription_id)
        .select_related(
            'plan',
            'membership__customer',
            'membership__store__customization',
            'membership__store__user',
            'membership__store__domain',
        )
        .first()
    )
    if subscription is not None:
        send_membership_expiry_email(subscription)
