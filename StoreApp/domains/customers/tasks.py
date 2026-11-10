import logging

from celery import shared_task

"""
Tareas de correo de la cuenta de comprador (Celery).

Mismo patrón que AdminApp/domains/users/tasks.py: los services encolan
post-commit con `.delay(...)` y estas tasks hacen el envío real con
reintento exponencial. Sin broker (dev/tests) CELERY_TASK_ALWAYS_EAGER
corre la task en el mismo proceso.
"""

logger  =   logging.getLogger(__name__)

_RETRY  =   dict(autoretry_for = (Exception,), retry_backoff = True, max_retries = 3)


@shared_task(**_RETRY)
def send_customer_verification_email(customer_id : int, store_slug : str = '') -> None:
    from StoreApp.domains.customers.models import Customer
    from StoreApp.domains.customers.services.customers import (
        SendCustomerVerificationEmailQuery,
    )
    customer    =   Customer.objects.filter(pk = customer_id).first()
    if customer:
        SendCustomerVerificationEmailQuery(customer, store_slug = store_slug)


@shared_task(**_RETRY)
def send_customer_password_reset_email(customer_id : int) -> None:
    from StoreApp.domains.customers.models import Customer
    from StoreApp.domains.customers.services.customers import (
        SendCustomerPasswordResetEmailQuery,
    )
    customer    =   Customer.objects.filter(pk = customer_id).first()
    if customer:
        SendCustomerPasswordResetEmailQuery(customer)
