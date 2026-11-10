from celery import shared_task

"""
Tareas Celery del dominio support (autodiscovery: `<app>.tasks`).

El email al dueño por mensaje del comprador nunca viaja en el request:
se encola post-creación y el worker hace el SMTP (mismo criterio que
legalpages/tasks.py). Sin broker (dev/tests) corre eager.
"""
_RETRY = dict(autoretry_for = (Exception,), retry_backoff = True, max_retries = 3)


@shared_task(**_RETRY)
def send_support_message_email(message_id : int) -> None:
    from StoreApp.domains.support.models import SupportMessage
    from StoreApp.domains.support.services import deliver_support_email
    message =   SupportMessage.objects.select_related(
        'thread__store__user__user', 'thread__store__customization', 'thread__customer', 'thread__order',
    ).filter(pk = message_id).first()
    if message is not None:
        deliver_support_email(message)
