import hashlib
import random
import time

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage
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
CAPTCHA_MAX_AGE         =   600      # el challenge vence a los 10 minutos
CAPTCHA_MIN_SECONDS     =   3        # envíos instantáneos = bot
CONTACT_SUBJECT_PREFIX  =   '[Web] Mensaje de contacto'
#=========================================
# CAPTCHA
#=========================================
def _answer_hash(slug : str, answer : int) -> str:
    raw =   f'{slug}:{answer}:{settings.SECRET_KEY}'
    return hashlib.sha256(raw.encode()).hexdigest()

def issue_captcha(slug : str) -> dict:
    """Genera el challenge: {challenge_id (firmado), question}."""
    a, b        =   random.randint(1, 9), random.randint(1, 9)
    payload     =   {'s': slug, 'h': _answer_hash(slug, a + b), 't': time.time()}
    return {
        'challenge_id'  :   signing.dumps(payload, salt = CAPTCHA_SALT),
        'question'      :   f'¿Cuánto es {a} + {b}?',
    }

def verify_captcha(slug : str, challenge_id : str, answer : str) -> bool:
    """Valida firma, vencimiento, tiempo mínimo y respuesta."""
    try:
        payload =   signing.loads(challenge_id, salt = CAPTCHA_SALT, max_age = CAPTCHA_MAX_AGE)
    except signing.BadSignature:
        return False
    if payload.get('s') != slug:
        return False
    if time.time() - float(payload.get('t') or 0) < CAPTCHA_MIN_SECONDS:
        return False
    try:
        answer_int  =   int(str(answer).strip())
    except (TypeError, ValueError):
        return False
    return payload.get('h') == _answer_hash(slug, answer_int)
#=========================================
# CONTACT MAIL
#=========================================
def contact_target(store) -> str:
    """Destino de los mensajes: email de contacto elegido o el de la cuenta."""
    customization   =   getattr(store, 'customization', None)
    chosen          =   (getattr(customization, 'contact_email', '') or '').strip()
    return chosen or (store.user.user.email or '')

def send_contact_message(store, *, name : str, email : str, message : str) -> bool:
    """Envía el mensaje del visitante al dueño de la tienda. False sin destino."""
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
    EmailMessage(
        subject     =   f'{CONTACT_SUBJECT_PREFIX} — {shop}',
        body        =   body,
        from_email  =   settings.DEFAULT_FROM_EMAIL,
        to          =   [target],
        reply_to    =   [email],
    ).send(fail_silently = False)
    return True
