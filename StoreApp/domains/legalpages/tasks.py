from celery import shared_task

"""
Tareas Celery del dominio legalpages (autodiscovery: `<app>.tasks`).

El email de solicitud de devolución nunca viaja en el request público:
se encola post-creación y el worker hace el SMTP (mismo criterio que
AdminApp.domains.users.tasks). Sin broker (dev/tests) corre eager.
"""
_RETRY = dict(autoretry_for = (Exception,), retry_backoff = True, max_retries = 3)


@shared_task(**_RETRY)
def send_return_request_email(request_id : int) -> None:
    from StoreApp.domains.legalpages.models import ReturnRequest
    from StoreApp.domains.legalpages.services import deliver_return_request_email
    req =   ReturnRequest.objects.select_related(
        'store__user__user', 'store__customization',
    ).filter(pk = request_id).first()
    if req is not None:
        deliver_return_request_email(req)
