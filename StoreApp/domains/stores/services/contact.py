import hashlib
import hmac
import logging
import random
import secrets
import time

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage

from DaventProject.cache_utils import cache_add, cache_get, cache_incr, cache_set

"""
Formulario de contacto de la web pública + captcha antispam.

El captcha es una suma firmada con TimestampSigner: el challenge viaja al
visitante con el HASH de la respuesta (nunca la respuesta) y un timestamp —
el backend valida firma, antigüedad máxima y tiempo mínimo transcurrido.
Sin servicios externos ni keys: si en el futuro se quiere reCAPTCHA, este
módulo es el único punto a reemplazar.
"""
#=========================================
# CONSTANTS
#=========================================
CAPTCHA_SALT            =   'stores.contact.captcha'
CAPTCHA_MAX_AGE         =   300      # el challenge vence a los 5 minutos
CAPTCHA_MIN_SECONDS     =   3        # envíos instantáneos = bot
#Un challenge es de UN SOLO USO (nonce en cache) y admite pocos intentos:
#la suma de dos dígitos (17 valores) era sorteable con pocas IPs.
CAPTCHA_MAX_ATTEMPTS    =   5
CONTACT_SUBJECT_PREFIX  =   '[Web] Mensaje de contacto'
logger                  =   logging.getLogger(__name__)
#=========================================
# CAPTCHA
#=========================================
def _answer_hash(slug : str, answer : int) -> str:
    raw =   f'{slug}:{answer}:{settings.SECRET_KEY}'
    return hashlib.sha256(raw.encode()).hexdigest()

def _captcha_question():
    """
    Operación con respuesta de MUCHA más entropía que la suma de dos dígitos
    (2..18): suma de dos 2 dígitos, resta con resultado positivo o producto
    de dos factores. random.SystemRandom (no el Mersenne Twister global).
    """
    rnd     =   random.SystemRandom()
    kind    =   rnd.choice(('add', 'sub', 'mul'))
    if kind == 'add':
        a, b    =   rnd.randint(10, 99), rnd.randint(10, 99)
        return a + b, f'¿Cuánto es {a} + {b}?'
    if kind == 'sub':
        a, b    =   rnd.randint(10, 99), rnd.randint(1, 99)
        a, b    =   max(a, b), min(a, b)
        return a - b, f'¿Cuánto es {a} - {b}?'
    a, b    =   rnd.randint(3, 12), rnd.randint(3, 12)
    return a * b, f'¿Cuánto es {a} × {b}?'

def issue_captcha(slug : str) -> dict:
    """Genera el challenge: {challenge_id (firmado con nonce), question}."""
    answer, question    =   _captcha_question()
    payload     =   {'s': slug, 'h': _answer_hash(slug, answer), 't': time.time(), 'n': secrets.token_urlsafe(16)}
    return {
        'challenge_id'  :   signing.dumps(payload, salt = CAPTCHA_SALT),
        'question'      :   question,
    }

def verify_captcha(slug : str, challenge_id : str, answer : str) -> bool:
    """
    Valida firma, vencimiento, tiempo mínimo, intentos y respuesta. El nonce
    se marca usado al acertar: el mismo challenge no sirve dos veces (ni para
    el formulario de contacto ni para las reseñas).
    """
    try:
        payload =   signing.loads(challenge_id, salt = CAPTCHA_SALT, max_age = CAPTCHA_MAX_AGE)
    except signing.BadSignature:
        return False
    nonce   =   str(payload.get('n') or '')
    if not nonce:
        return False
    if cache_get(f'captcha:used:{nonce}'):
        return False
    #Contador de intentos por challenge: 5 respuestas malas lo queman aunque
    #el atacante conserve el challenge_id firmado.
    attempts_key    =   f'captcha:try:{nonce}'
    if cache_add(attempts_key, 1, CAPTCHA_MAX_AGE):
        attempts    =   1
    else:
        try:
            attempts    =   cache_incr(attempts_key) or 1
        except ValueError:
            cache_set(attempts_key, 1, CAPTCHA_MAX_AGE)
            attempts    =   1
    if attempts > CAPTCHA_MAX_ATTEMPTS:
        return False
    if payload.get('s') != slug:
        return False
    if time.time() - float(payload.get('t') or 0) < CAPTCHA_MIN_SECONDS:
        return False
    try:
        answer_int  =   int(str(answer).strip())
    except (TypeError, ValueError):
        return False
    if not hmac.compare_digest(str(payload.get('h') or ''), _answer_hash(slug, answer_int)):
        return False
    cache_set(f'captcha:used:{nonce}', 1, CAPTCHA_MAX_AGE)
    return True
#=========================================
# CONTACT MAIL
#=========================================
def contact_target(store) -> str:
    """Destino de los mensajes: email de contacto elegido o el de la cuenta."""
    customization   =   getattr(store, 'customization', None)
    chosen          =   (getattr(customization, 'contact_email', '') or '').strip()
    return chosen or (store.user.user.email or '')

def send_contact_message(store, *, name : str, email : str, message : str) -> bool:
    """
    Encola el mensaje del visitante al dueño (el SMTP corre en Celery: el
    request público no espera el envío). False sin destino.
    """
    if not contact_target(store):
        return False
    from AdminApp.domains.users.tasks import send_contact_email
    send_contact_email.delay(store.pk, name, email, message)
    return True


def deliver_contact_message(store, *, name : str, email : str, message : str) -> bool:
    """Envío real (lo corre la task de Celery). False sin destino o SMTP caído."""
    target          =   contact_target(store)
    if not target:
        return False
    shop            =   getattr(store.customization, 'display_name', '') or store.user.business_name or store.slug
    body            =   (
        f'Recibiste un mensaje desde el formulario de contacto de tu web ({store.slug}).\n\n'
        f'Nombre: {name}\n'
        f'Email: {email}\n\n'
        f'Mensaje:\n{message}\n\n'
        f'---\nPodés responderle directamente a {email} (el botón Responder ya apunta a su correo).'
    )
    try:
        EmailMessage(
            subject     =   f'{CONTACT_SUBJECT_PREFIX} — {shop}',
            body        =   body,
            from_email  =   settings.DEFAULT_FROM_EMAIL,
            to          =   [target],
            reply_to    =   [email],
        ).send(fail_silently = False)
    except Exception:
        #SMTP caído o inalcanzable: se loguea y el visitante recibe un error
        #genérico en vez de un 500 (o un request colgado sin EMAIL_TIMEOUT).
        logger.exception('No se pudo enviar el mensaje de contacto de %s', store.slug)
        return False
    return True
