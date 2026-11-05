import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from AdminApp.domains.suscriptions.models import SubscriptionNotice, Suscription
from AdminApp.domains.users.services.services import (
    FRONTEND_URL,
    _display_name,
    _mail_html,
    _send_branded_mail,
)

logger          =   logging.getLogger(__name__)

"""

Mails automáticos de estado de cuenta (comando `subscription_notices`,
cron diario). Dos avisos por período de acceso:

- `ending`: quedan NOTICE_DAYS días o menos para perder el acceso.
- `expired`: el acceso se cortó hace EXPIRED_DAYS días o menos.

Idempotencia: cada envío deja un SubscriptionNotice con key
`<kind>:<fecha de access_until>` — si el plan se renueva o se canjea otro
cupón (end_date nuevo) la key cambia y vuelve a avisar; el mismo período
nunca manda dos veces. Las suscripciones con débito automático vivo
(auto_renew sin baja) se saltean: Mercado Pago renueva solo y el usuario
ya recibe la factura por mail.

"""

NOTICE_DAYS     =   3
EXPIRED_DAYS    =   3


def _plans_url() -> str:
    return f'{FRONTEND_URL}/dashboard?s=plans'


def _already_sent(suscription, key) -> bool:
    #Savepoint propio: el IntegrityError del duplicado no puede romper la
    #transacción exterior (tests corren dentro de un atomic).
    try:
        with transaction.atomic():
            SubscriptionNotice.objects.create(suscription = suscription, key = key)
        return False
    except IntegrityError:
        return True


def _period_label(suscription) -> str:
    plan    =   suscription.plan_suscription
    if getattr(plan, 'is_trial', False):
        return 'tu período de prueba'
    return f'tu plan {plan.name}'


def SendSubscriptionNoticesQuery(dry_run : bool = False) -> dict:
    now     =   timezone.now()
    window_end   =   now + timedelta(days = NOTICE_DAYS)
    window_start =   now - timedelta(days = EXPIRED_DAYS)
    sent    =   {'ending': 0, 'expired': 0}
    candidates   =   []
    qs      =   (
        Suscription.objects
        .select_related('user__user', 'plan_suscription')
        .filter(status = Suscription.STATUS_ACTIVE)
    )
    for suscription in qs:
        #Débito automático vivo: MP renueva solo, no hay nada que avisar.
        if suscription.auto_renew and not suscription.cancelled_at:
            continue
        auth_user   =   getattr(suscription.user, 'user', None)
        email       =   (getattr(auth_user, 'email', '') or '').strip()
        if not email:
            continue
        until       =   suscription.access_until()
        kind        =   None
        if until and until > now and until <= window_end:
            kind    =   'ending'
        elif until and window_start <= until <= now:
            kind    =   'expired'
        if kind is None:
            continue
        key         =   f'{kind}:{until.date().isoformat()}'
        if dry_run:
            candidates.append((suscription.pk, kind, email))
            sent[kind] += 1
            continue
        if _already_sent(suscription, key):
            continue
        _send_notice(suscription, auth_user, kind, until, now)
        sent[kind] += 1
    logger.info('Avisos de suscripción: %s', sent)
    return {'sent': sent, 'candidates': candidates}


def _send_notice(suscription, auth_user, kind : str, until, now) -> None:
    plan_name   =   _period_label(suscription)
    link        =   _plans_url()
    name        =   _display_name(auth_user)
    if kind == 'ending':
        days_left   =   max(1, (until - now).days)
        when        =   until.strftime('%d/%m/%Y')
        _send_branded_mail(
            auth_user,
            subject     =   f'{plan_name.capitalize()} en DAVENT vence el {when}',
            body        =   (
                f'Hola {name},\n\n'
                f'Te queda{"n" if days_left != 1 else ""} {days_left} día{"s" if days_left != 1 else ""} de {plan_name}. '
                f'Si querés seguir usando tu web después del {when}, elegí un plan desde tu panel:\n\n'
                f'{link}\n\n'
                f'Si ya pagaste o activaste un cupón, ignorá este correo.'
            ),
            html        =   _mail_html(
                title           =   'Tu plan está por vencer',
                intro           =   f'Hola {name}, te queda{"n" if days_left != 1 else ""} {days_left} día{"s" if days_left != 1 else ""} de {plan_name} (hasta el {when}).',
                button_label    =   'Ver planes y renovar',
                link            =   link,
                note            =   'Después de esa fecha tu web pública deja de estar disponible hasta que elijas un plan. Si ya renovaste, ignorá este correo.',
            ),
        )
    else:
        _send_branded_mail(
            auth_user,
            subject     =   'Tu acceso a DAVENT terminó',
            body        =   (
                f'Hola {name},\n\n'
                f'Tu {plan_name} venció y tu web pública ya no está disponible. '
                f'Tus datos siguen guardados: elegí un plan y volvé a publicarla en minutos:\n\n'
                f'{link}\n\n'
                f'— El equipo de DAVENT'
            ),
            html        =   _mail_html(
                title           =   'Tu acceso terminó',
                intro           =   f'Hola {name}, tu {plan_name} venció y tu web pública ya no está disponible.',
                button_label    =   'Elegir un plan',
                link            =   link,
                note            =   'Tus datos y tu catálogo siguen guardados: apenas elijas un plan tu web vuelve a estar en línea.',
            ),
        )
