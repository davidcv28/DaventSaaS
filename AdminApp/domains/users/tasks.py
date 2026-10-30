import logging

from celery import shared_task

"""

Tareas de correo (Celery).

Todos los correos salen del request: un SMTP lento (timeout 10 s) ocupaba
los hilos de gunicorn (3 workers × 4 threads) y bloqueaba el panel; además
el tiempo de envío delataba si una cuenta existía (reset de contraseña).
Los services encolan post-commit con `.delay(...)` y estas tasks hacen el
trabajo real con reintento exponencial.

Sin broker configurado (dev/tests) `CELERY_TASK_ALWAYS_EAGER` queda en True
y la task corre en el mismo proceso — mismo resultado, sin worker.

"""

logger = logging.getLogger(__name__)

_RETRY = dict(autoretry_for = (Exception,), retry_backoff = True, max_retries = 3)


@shared_task(**_RETRY)
def send_verification_email(user_id : int) -> None:
    from django.contrib.auth.models import User
    from AdminApp.domains.users.services import SendVerificationEmailQuery
    user    =   User.objects.filter(pk = user_id).first()
    if user:
        SendVerificationEmailQuery(user)


@shared_task(**_RETRY)
def send_password_reset_email(user_id : int) -> None:
    from django.contrib.auth.models import User
    from AdminApp.domains.users.services import SendPasswordResetEmailQuery
    user    =   User.objects.filter(pk = user_id).first()
    if user:
        SendPasswordResetEmailQuery(user)


@shared_task(**_RETRY)
def send_invoice_email(invoice_id : int) -> None:
    from AdminApp.domains.invoices.models import Invoice
    from AdminApp.domains.invoices.services.services import SendInvoiceEmailQuery
    invoice =   Invoice.objects.select_related(
        'user__user', 'user__province', 'user__city',
        'payment__suscription__plan_suscription',
    ).filter(pk = invoice_id).first()
    if invoice:
        SendInvoiceEmailQuery(invoice)


@shared_task(**_RETRY)
def send_contact_email(store_id : int, name : str, email : str, message : str) -> None:
    from StoreApp.domains.stores.models import Store
    from StoreApp.domains.stores.services.contact import deliver_contact_message
    store   =   Store.objects.filter(pk = store_id).first()
    if store:
        deliver_contact_message(store, name = name, email = email, message = message)


@shared_task(**_RETRY)
def send_legal_report_email(report_id : int) -> None:
    from AdminApp.domains.legal.models import ContentReport
    from AdminApp.domains.legal.services.services import NotifyContentReportQuery
    report  =   ContentReport.objects.filter(pk = report_id).first()
    if report:
        NotifyContentReportQuery(report)
