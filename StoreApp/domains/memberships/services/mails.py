"""
Correo de aviso de membresía de tienda por vencer (track F — Ola 2).

Lo dispara el comando `membership_expiry_notices` (cron diario) vía la
task Celery `send_membership_expiry_notice`: suscripciones 'active'
con `vigente_hasta` dentro de los próximos N días → email al
`membership.customer.email` con el plan, la fecha y link a la página
pública de suscripciones de ESA tienda (`{store_web}/suscripciones`).

La idempotencia NO vive acá: el comando marca
`StoreSubscription.expiry_notified_until = vigente_hasta` antes de
encolar — este módulo solo compone y envía (tolerante a fallos SMTP,
mismo patrón que customers/services/mails.py).

`store_web_url` se importa PEREZOSO desde storepayments (mismo motivo
que orders/services/mails.py: no acoplar memberships→storepayments a
nivel módulo).
"""
import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from StoreApp.domains.customers.services.mails import _mail_html

logger  =   logging.getLogger(__name__)


def _store_name(store):
    #display_name → business_name del perfil → slug (mismo orden que
    #benefits.store_display_name, sin importar memberships→benefits acá).
    customization    =   getattr(store, 'customization', None)
    display          =   (getattr(customization, 'display_name', '') or '').strip()
    if display:
        return display
    business         =   (getattr(getattr(store, 'user', None), 'business_name', '') or '').strip()
    return business or getattr(store, 'slug', '') or 'la tienda'


def _store_web_url(store):
    from StoreApp.domains.storepayments.services.preferences import store_web_url
    return store_web_url(store)


def _customer_email(subscription):
    return (getattr(getattr(subscription.membership, 'customer', None), 'email', '') or '').strip()


def membership_expiry_context(subscription):
    """
    Datos del aviso: tienda, plan, fecha de vencimiento y días que
    quedan — lo comparten el mail y el --dry-run del comando.
    """
    store       =   subscription.membership.store
    until       =   subscription.vigente_hasta
    now         =   timezone.now()
    days_left   =   max(1, (until - now).days) if until else 0
    return {
        'store'         :   store,
        'store_name'    :   _store_name(store),
        'plan_name'     :   getattr(subscription.plan, 'name', '') or 'tu plan',
        'until'         :   until,
        'until_label'   :   until.strftime('%d/%m/%Y') if until else '',
        'days_left'     :   days_left,
        'link'          :   f'{_store_web_url(store)}/suscripciones',
        'email'         :   _customer_email(subscription),
    }


def send_membership_expiry_email(subscription):
    """
    Manda el aviso de vencimiento al cliente. Devuelve True si el mail
    salió (o al menos se intentó sin excepción de SMTP — el envío ya es
    tolerante), False si no hay email destino.
    """
    ctx     =   membership_expiry_context(subscription)
    email   =   ctx['email']
    if not email:
        logger.warning('membership_expiry: suscripción %s sin email de cliente', subscription.pk)
        return False
    #Mismo criterio que orders/services/mails.py: el alta no prueba la
    #titularidad del email — lifecycle mail solo a direcciones verificadas.
    customer    =   getattr(getattr(subscription, 'membership', None), 'customer', None)
    if customer is not None and not getattr(customer, 'email_verified', False):
        logger.info('membership_expiry: email no verificado, mail omitido (subscription=%s)', subscription.pk)
        return False
    store_name  =   ctx['store_name']
    plan_name   =   ctx['plan_name']
    when        =   ctx['until_label']
    days_left   =   ctx['days_left']
    link        =   ctx['link']
    subject     =   f'Tu membresía {plan_name} en {store_name} vence el {when}'
    body        =   (
        f'Hola,\n\n'
        f'Tu membresía {plan_name} en {store_name} vence el {when} '
        f'(te quedan {days_left} {"día" if days_left == 1 else "días"}).\n\n'
        f'Para no perder tus beneficios, renovala desde la página de '
        f'suscripciones de la tienda:\n\n'
        f'{link}\n\n'
        f'— DAVENT'
    )
    html        =   _mail_html(
        title           =   'Tu membresía está por vencer',
        intro           =   f'Tu membresía <strong>{escape(plan_name)}</strong> en {escape(store_name)} vence el <strong>{escape(when)}</strong> — te quedan {days_left} {"día" if days_left == 1 else "días"}.',
        button_label    =   'Ver suscripciones',
        link            =   link,
        note            =   'Si ya renovaste o el pago está en curso, ignorá este correo.',
    )
    try:
        mail    =   EmailMultiAlternatives(
            subject     =   subject,
            body        =   body,
            from_email  =   settings.DEFAULT_FROM_EMAIL,
            to          =   [email],
        )
        mail.attach_alternative(html, 'text/html')
        mail.send(fail_silently = False)
    except Exception:
        logger.exception('No se pudo enviar el aviso de vencimiento de membresía (subscription=%s)', subscription.pk)
        return False
    return True
