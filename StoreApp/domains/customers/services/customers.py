"""
Queries del dominio customers: alta/login de la cuenta global del
comprador, membresías por tienda, verificación de email y reset de
contraseña.

Convenciones del proyecto replicadas:
- Transacciones + `transaction.on_commit` para los mails (un rollback no
  dispara correos) y tareas Celery `.delay()` para no bloquear el request.
- Password reset: respuesta genérica anti-enumeración en la vista; acá
  solo se resuelve el envío.
- Errores de negocio como `serializers.ValidationError` → 400 en la vista.
"""
import logging

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from StoreApp.domains.customers.models import Customer, CustomerAddress, StoreMembership
from StoreApp.domains.customers.services.mails import (
    _mail_html,
    account_url,
    send_branded_mail,
)

logger  =   logging.getLogger(__name__)
#Hash pbkdf2 real para igualar el tiempo del login cuando el email no
#existe (anti-enumeración por timing). Se calcula una vez al importar.
_DUMMY_PASSWORD_HASH    =   make_password('timing-equalizer-not-a-real-password')
#=========================================
# HELPERS
#=========================================
def normalize_email(email):
    """Email canónico de cuenta: strip + minúsculas (la unique es case-sensitive)."""
    return (email or '').strip().lower()


def resolve_store(slug):
    """
    Tienda pública comprable por slug: publicada y no bloqueada.
    Devuelve None si no existe o no es visible — la vista decide 400/404.
    """
    slug    =   (slug or '').strip().lower()
    if not slug:
        return None
    from StoreApp.domains.stores.models import Store
    return Store.objects.filter(
        slug = slug, is_published = True, is_blocked = False,
    ).first()


class MembershipSuspended(PermissionDenied):
    """El comprador existe pero su membresía en ESA tienda está suspendida."""
    default_detail = 'Tu cuenta está suspendida en esta tienda.'


def ensure_membership(customer, store):
    """
    get_or_create de la membresía customer×store. Si ya existía
    suspendida lanza MembershipSuspended (403) — el alta/login con
    store_slug no puede bypassear la suspensión del dueño.
    """
    membership, _created  =   StoreMembership.objects.get_or_create(
        customer = customer, store = store,
        defaults = {'status': StoreMembership.STATUS_ACTIVE},
    )
    if membership.status == StoreMembership.STATUS_SUSPENDED:
        raise MembershipSuspended()
    return membership


def mark_login(customer):
    customer.last_login_at   =   timezone.now()
    customer.save(update_fields = ['last_login_at'])


#=========================================
# REGISTER / AUTH
#=========================================
def RegisterCustomerQuery(validated_data):
    """
    Crea el Customer (password hasheado) y, si vino `store`, su
    StoreMembership. Devuelve (customer, membership|None).
    Lanza serializers.ValidationError en email duplicado (carrera
    incluida: el pre-check del serializer no alcanza bajo concurrencia).
    """
    data            =   dict(validated_data)
    store           =   data.pop('store', None)
    email           =   normalize_email(data['email'])
    try:
        with transaction.atomic():
            customer    =   Customer(
                email           =   email,
                first_name      =   (data.get('first_name') or '').strip()[:150],
                last_name       =   (data.get('last_name') or '').strip()[:150],
            )
            customer.set_password(data['password'])
            customer.save()
            membership  =   ensure_membership(customer, store) if store else None
            #VERIFICACIÓN DE EMAIL post-commit: si la tx rollbackea el alta
            #no existió y el mail no debe salir igual. Celery eager en dev.
            #El slug de la tienda viaja al mail: el link cae en SU web.
            slug    =   store.slug if store else ''
            transaction.on_commit(lambda: _enqueue_verification_email(customer.pk, slug))
            return customer, membership
    except IntegrityError:
        raise serializers.ValidationError({'email': 'Ya existe una cuenta con ese correo.'})


def authenticate_customer(email, password):
    """
    Devuelve el Customer si email+password son válidos (incluye cuentas
    inactivas — la vista decide 401 vs 403 sin filtrar cuál falló),
    None si las credenciales no matchean.
    """
    customer    =   Customer.objects.filter(email__iexact = normalize_email(email)).first()
    if customer is None:
        #Timing: corre el hasher igual para no delatar si el email existe.
        from django.contrib.auth.hashers import check_password as _check
        _check(password or '', _DUMMY_PASSWORD_HASH)
        return None
    if not customer.check_password(password):
        return None
    return customer


def _enqueue_verification_email(customer_id, store_slug = ''):
    from StoreApp.domains.customers.tasks import send_customer_verification_email
    send_customer_verification_email.delay(customer_id, store_slug)


def _enqueue_password_reset_email(customer_id):
    from StoreApp.domains.customers.tasks import send_customer_password_reset_email
    send_customer_password_reset_email.delay(customer_id)


#=========================================
# EMAIL VERIFICATION (token firmado — django.core.signing)
#=========================================
#Token único firmado con SECRET_KEY: {cid, em} — `em` invalida el link si
#el correo cambiara (hoy el PATCH de perfil no permite cambiar email, pero
#el binding cuesta nada y cubre futuros flujos). TTL 24 h.
VERIFY_EMAIL_SALT       =   'customers.email_verify'
VERIFY_EMAIL_MAX_AGE    =   60 * 60 * 24

def make_verify_email_token(customer):
    return signing.dumps(
        {'cid': customer.pk, 'em': customer.email},
        salt = VERIFY_EMAIL_SALT, compress = True,
    )


def verify_email_token(token):
    """Devuelve el Customer si el token es válido y vigente, None si no."""
    try:
        payload =   signing.loads(
            token or '', salt = VERIFY_EMAIL_SALT,
            max_age = VERIFY_EMAIL_MAX_AGE,
        )
        if not isinstance(payload, dict):
            return None
        customer    =   Customer.objects.filter(pk = payload.get('cid')).first()
    except (signing.BadSignature, signing.SignatureExpired, ValueError, TypeError):
        return None
    if customer is None or payload.get('em') != customer.email:
        return None
    return customer


def SendCustomerVerificationEmailQuery(customer, store_slug = ''):
    if not (customer.email or '').strip() or customer.email_verified:
        return
    token   =   make_verify_email_token(customer)
    link    =   account_url(store_slug, f'/cuenta/verificar?token={token}')
    name    =   (customer.first_name or customer.email).strip()
    send_branded_mail(
        customer,
        subject     =   'Verificá tu correo — DAVENT',
        body        =   (
            f'Hola {name},\n\n'
            f'Creaste tu cuenta de comprador. Verificá tu correo acá: {link}\n\n'
            f'Si no creaste esta cuenta, ignorá este correo.'
        ),
        html        =   _verification_html(name, link),
    )


def _verification_html(name, link):
    from html import escape
    return _mail_html(
        title           =   'Verificá tu correo electrónico',
        intro           =   f'Hola {escape(name)}, confirmá que este correo es tuyo para terminar de crear tu cuenta de comprador.',
        button_label    =   'Verificar mi correo',
        link            =   link,
        note            =   'El enlace vence en 24 horas. Si no creaste esta cuenta, ignorá este correo.',
    )


def VerifyCustomerEmailQuery(token):
    """Marca email_verified; idempotente si ya estaba verificado."""
    customer    =   verify_email_token(token)
    if customer is None:
        return False
    if not customer.email_verified:
        customer.email_verified      =   True
        customer.email_verified_at   =   timezone.now()
        customer.save(update_fields = ['email_verified', 'email_verified_at'])
    return True


#=========================================
# PASSWORD RESET (uid + token — patrón users, contrato {uid, token})
#=========================================
class CustomerPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """
    Token firmado de reset para Customer. `_make_hash_value` se adapta:
    el default de Django usa `user.last_login` (auth.User) — acá va
    `password` (cualquier cambio de clave invalida tokens viejos),
    `is_active` y el email. Misma ventana que settings.PASSWORD_RESET_TIMEOUT.
    """
    key_salt    =   'StoreApp.domains.customers.password_reset'
    timeout     =   settings.PASSWORD_RESET_TIMEOUT
    def _make_hash_value(self, customer, timestamp):
        return f'{customer.pk}{customer.password}{timestamp}{customer.email}{customer.is_active}'


customer_reset_token    =   CustomerPasswordResetTokenGenerator()

def _uid_token(customer):
    return (
        urlsafe_base64_encode(force_bytes(customer.pk)),
        customer_reset_token.make_token(customer),
    )


def SendCustomerPasswordResetEmailQuery(customer):
    if not (customer.email or '').strip():
        return
    uid, token  =   _uid_token(customer)
    link        =   account_url('', f'/cuenta/restablecer?uid={uid}&token={token}')
    hours       =   settings.PASSWORD_RESET_TIMEOUT // 3600
    name        =   (customer.first_name or customer.email).strip()
    from html import escape
    send_branded_mail(
        customer,
        subject     =   'Restablecé tu contraseña — DAVENT',
        body        =   (
            f'Hola {name},\n\n'
            f'Recibimos un pedido para restablecer la contraseña de tu cuenta de comprador.\n\n'
            f'Abrí este enlace para elegir una contraseña nueva: {link}\n\n'
            f'El enlace vence en {hours} horas. Si no pediste el cambio, ignorá este correo: tu clave no se modifica.'
        ),
        html        =   _mail_html(
            title           =   'Restablecé tu contraseña',
            intro           =   f'Hola {escape(name)}, recibimos un pedido para cambiar la contraseña de tu cuenta. Elegí una clave nueva desde el botón.',
            button_label    =   'Elegir nueva contraseña',
            link            =   link,
            note            =   f'El enlace vence en {hours} horas y al usarse cierra todas tus sesiones abiertas. Si no pediste el cambio, ignorá este correo: tu contraseña no se modifica.',
        ),
    )


#REQUEST PASSWORD RESET — la vista responde siempre genérico (anti-enumeración)
def RequestCustomerPasswordResetQuery(email):
    customer    =   Customer.objects.filter(email__iexact = normalize_email(email)).first()
    if customer:
        #Encolado post-commit: el tiempo de envío no delata si la cuenta existe.
        transaction.on_commit(lambda: _enqueue_password_reset_email(customer.pk))


def ConfirmCustomerPasswordResetQuery(customer, new_password):
    """
    Setea la clave y sella `tokens_valid_after`: todo JWT emitido antes
    queda revocado en auth y en refresh (paridad con _revoke_sessions de
    users — OutstandingToken.user es auth.User, no sirve para clientes).
    """
    customer.set_password(new_password)
    customer.tokens_valid_after   =   timezone.now()
    customer.save(update_fields = ['password', 'tokens_valid_after'])
    logger.info('Reset de contraseña de cliente confirmado (customer_id=%s)', customer.pk)
    return customer


#=========================================
# ADDRESSES (un solo is_default por cliente)
#=========================================
def save_address_defaults(address, is_default):
    """
    Garantiza UN solo default por cliente: al marcar uno, desmarca el resto.
    """
    if not is_default:
        return
    with transaction.atomic():
        CustomerAddress.objects.filter(customer = address.customer).exclude(pk = address.pk).update(is_default = False)
        if not address.is_default:
            address.is_default  =   True
            address.save(update_fields = ['is_default'])


def promote_default_address(customer, exclude_pk = None):
    """Tras borrar la default, promueve la más reciente restante."""
    qs  =   CustomerAddress.objects.filter(customer = customer, is_default = False)
    if exclude_pk:
        qs  =   qs.exclude(pk = exclude_pk)
    nxt =   qs.order_by('-created_at').first()
    if nxt:
        nxt.is_default  =   True
        nxt.save(update_fields = ['is_default'])
