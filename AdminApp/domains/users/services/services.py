import logging
import re
import secrets
from datetime import timedelta
from urllib.parse import quote

from decouple import config
from AdminApp.domains.users.models import UserProfile, TERMS_VERSION
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.html import escape
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

logger          =   logging.getLogger(__name__)
#Vacío en .env != ausente: un valor vacío también cae al default de dev.
FRONTEND_URL    =   config('FRONTEND_URL', default = '') or 'http://localhost:5173'
BACKEND_URL     =   config('BACKEND_URL', default = '') or 'http://127.0.0.1:8000'
#=================================
# USER MODEL QUERYS
#=================================

#USER UPDATE QUERY
def UpdateUserQuery(user: User, validated_data : dict) -> User:
    email       =   validated_data['email'].strip()
    #Si cambia el correo hay que verificarlo de nuevo: la verificación anterior
    #valía para la dirección vieja.
    if email != user.email:
        profile     =   getattr(user, 'profile', None)
        if profile is not None and profile.email_verified:
            profile.email_verified    =   False
            profile.email_verified_at =   None
            profile.save(update_fields = ['email_verified', 'email_verified_at'])
    user.email  =   email
    user.save()
    return user

#USER PASSWORD UPDATE
def UpdatePasswordUserQuery(user : User, validated_data : dict) -> User:
    new_password = validated_data['new_password']
    user.set_password(new_password)
    user.save()
    #Igual que el reset: cualquier refresh emitido antes del cambio queda en
    #blacklist — una sesión robada no sobrevive al cambio de contraseña.
    for token in OutstandingToken.objects.filter(user = user):
        BlacklistedToken.objects.get_or_create(token = token)
    return user

#PROFILE UPDATE QUERY
def UpdateProfileQuery(profile : UserProfile, validated_data : dict) -> UserProfile:
    #Si cambia el celular hay que verificarlo de nuevo: la verificación anterior
    #valía para el número viejo (misma regla que el cambio de correo).
    if validated_data.get('phone') != profile.phone:
        profile.phone_verified    =   False
        profile.phone_verified_at =   None
    for field, value in validated_data.items():
        setattr(profile, field, value)
    profile.save()
    return profile



#=================================
# USER REGISTER QUERYS
#=================================

def RegisterUserQuery(validated_data : dict) -> User:
    with transaction.atomic():
        data                =   validated_data.copy()
        username            =   data.pop('username')
        email               =   data.pop('email')
        password            =   data.pop('password')
        accept_terms        =   data.pop('accept_terms', False)
        #USER REGISTER
        new_user = User.objects.create_user(
            username        =   username,
            email           =   email,
            password        =   password  
        )
        profile = UserProfile.objects.create(
            user            =   new_user,
            #Sellamos la aceptación de TyC: fecha y versión vigente al momento del alta
            terms_accepted      =   bool(accept_terms),
            terms_accepted_at   =   timezone.now() if accept_terms else None,
            terms_version       =   TERMS_VERSION if accept_terms else None,
            **data
        )
        #PLAN DE PRUEBA: toda cuenta nueva arranca con el plan trial (is_trial),
        #vigente SuscriptionPlan.TRIAL_DAYS días. Al vencer pierde el acceso y no
        #se puede reactivar: el plan no es seleccionable en ningún flujo.
        trial_plan  =   SuscriptionPlan.objects.filter(is_trial = True).first()
        if trial_plan:
            now =   timezone.now()
            Suscription.objects.create(
                user                =   profile,
                plan_suscription    =   trial_plan,
                status              =   Suscription.STATUS_ACTIVE,
                start_date          =   now,
                end_date            =   now + timedelta(days = SuscriptionPlan.TRIAL_DAYS),
            )
        #VERIFICACIÓN DE EMAIL: se agenda post-commit — si la transacción
        #rollbackea el alta no existió y el mail no debe salir igual.
        transaction.on_commit(lambda : SendVerificationEmailQuery(new_user))
        return new_user
#=================================
# ACCOUNT MAIL / TOKEN HELPERS
#=================================
class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token firmado para verificar el correo. El hash incluye email_verified:
    una vez usado (o al re-verificar tras un cambio de correo) el link viejo
    se inutiliza solo. El vencimiento lo fija settings.PASSWORD_RESET_TIMEOUT.
    """
    key_salt    =   'AdminApp.domains.users.email_verification'
    def _make_hash_value(self, user, timestamp):
        profile     =   getattr(user, 'profile', None)
        verified    =   getattr(profile, 'email_verified', False)
        return f'{user.pk}{user.password}{user.last_login}{timestamp}{verified}'
email_verification_token    =   EmailVerificationTokenGenerator()

def _uid_token(user : User, generator) -> tuple:
    return urlsafe_base64_encode(force_bytes(user.pk)), generator.make_token(user)

def _display_name(user : User) -> str:
    profile     =   getattr(user, 'profile', None)
    name        =   f'{getattr(profile, "first_name", "") or ""} {getattr(profile, "last_name", "") or ""}'.strip()
    return name or getattr(profile, 'business_name', '') or user.username

def _mail_html(title : str, intro : str, button_label : str, link : str, note : str) -> str:
    #Misma presentación de marca que el correo de facturas (índigo DAVENT).
    return f"""<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;">
        <tr>
          <td style="background:#4f46e5;padding:24px 32px;">
            <span style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:.08em;">DAVENT</span><br />
            <span style="color:#c7d2fe;font-size:12px;">Plataforma de catálogos digitales</span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h1 style="margin:0 0 8px;font-size:20px;line-height:1.3;">{title}</h1>
            <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#475569;">{intro}</p>
            <p style="margin:0 0 24px;text-align:center;">
              <a href="{link}" style="display:inline-block;background:#4f46e5;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;padding:12px 28px;border-radius:10px;">{button_label}</a>
            </p>
            <p style="margin:0;font-size:12.5px;line-height:1.6;color:#64748b;">{note}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:18px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11.5px;line-height:1.6;color:#94a3b8;">
            Si el botón no abre, copiá este enlace en tu navegador:<br />
            <span style="word-break:break-all;">{link}</span><br /><br />
            Este correo se generó automáticamente; no respondas a esta dirección.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

def _send_branded_mail(user : User, *, subject : str, body : str, html : str) -> None:
    """Envío tolerante: un fallo de correo se loguea y no rompe el flujo."""
    try:
        mail        =   EmailMultiAlternatives(
            subject     =   subject,
            body        =   body,
            from_email  =   settings.DEFAULT_FROM_EMAIL,
            to          =   [user.email.strip()],
        )
        mail.attach_alternative(html, 'text/html')
        mail.send(fail_silently = False)
    except Exception:
        logger.exception('No se pudo enviar el correo "%s" al usuario %s', subject, user.pk)
#=================================
# PASSWORD RESET QUERYS
#=================================
def SendPasswordResetEmailQuery(user : User) -> None:
    if not (user.email or '').strip():
        return
    uid, token      =   _uid_token(user, default_token_generator)
    link            =   f'{FRONTEND_URL}/reset-password?uid={uid}&token={token}'
    hours           =   settings.PASSWORD_RESET_TIMEOUT // 3600
    name            =   escape(_display_name(user))
    _send_branded_mail(
        user,
        subject     =   'Restablecé tu contraseña — DAVENT',
        body        =   (
            f'Hola {_display_name(user)},\n\n'
            f'Recibimos un pedido para restablecer la contraseña de tu cuenta DAVENT.\n\n'
            f'Abrí este enlace para elegir una contraseña nueva: {link}\n\n'
            f'El enlace vence en {hours} horas. Si no pediste el cambio, ignorá este correo: tu clave no se modifica.'
        ),
        html        =   _mail_html(
            title       =   'Restablecé tu contraseña',
            intro       =   f'Hola {name}, recibimos un pedido para cambiar la contraseña de tu cuenta. Elegí una clave nueva desde el botón.',
            button_label=   'Elegir nueva contraseña',
            link        =   link,
            note        =   f'El enlace vence en {hours} horas y al usarse cierra todas tus sesiones abiertas. Si no pediste el cambio, ignorá este correo: tu contraseña no se modifica.',
        ),
    )

#REQUEST PASSWORD RESET (siempre "éxito" genérico: no revela si el correo existe)
def RequestPasswordResetQuery(email : str) -> None:
    user    =   User.objects.filter(email__iexact = (email or '').strip()).first()
    if user:
        SendPasswordResetEmailQuery(user)

#CONFIRM PASSWORD RESET (setea la clave y cierra TODAS las sesiones del usuario)
def ConfirmPasswordResetQuery(user : User, new_password : str) -> User:
    user.set_password(new_password)
    user.save()
    #Cualquier refresh token emitido antes del cambio queda en blacklist: el
    #robo de sesión que motivó el reseteo se corta en todos los dispositivos.
    for token in OutstandingToken.objects.filter(user = user):
        BlacklistedToken.objects.get_or_create(token = token)
    return user
#=================================
# EMAIL VERIFICATION QUERYS
#=================================
def SendVerificationEmailQuery(user : User) -> None:
    profile     =   getattr(user, 'profile', None)
    if not (user.email or '').strip() or (profile and profile.email_verified):
        return
    uid, token      =   _uid_token(user, email_verification_token)
    link            =   f'{BACKEND_URL}/api/verify-email/?uid={uid}&token={token}'
    name            =   escape(_display_name(user))
    _send_branded_mail(
        user,
        subject     =   'Verificá tu correo — DAVENT',
        body        =   (
            f'Hola {_display_name(user)},\n\n'
            f'Gracias por registrarte en DAVENT. Para crear tu web pública necesitamos confirmar que este correo es tuyo.\n\n'
            f'Verificá tu cuenta acá: {link}\n\n'
            f'Si no creaste esta cuenta, ignorá este correo.'
        ),
        html        =   _mail_html(
            title       =   'Verificá tu correo electrónico',
            intro       =   f'Hola {name}, gracias por registrarte en DAVENT. Confirmá que este correo es tuyo para poder crear tu web pública.',
            button_label=   'Verificar mi correo',
            link        =   link,
            note        =   'Hasta verificarlo podés usar tu panel, pero no crear tu web pública. Si no creaste esta cuenta, ignorá este correo.',
        ),
    )

#VERIFY EMAIL (marca el correo del perfil; idempotente si ya estaba verificado)
def VerifyEmailQuery(uid_b64 : str, token : str) -> bool:
    try:
        uid     =   force_str(urlsafe_base64_decode(uid_b64))
        user    =   User.objects.get(pk = uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return False
    profile     =   getattr(user, 'profile', None)
    if profile and profile.email_verified:
        #El link ya se usó (el token incluye el flag y queda viejo): no es error.
        return True
    if not email_verification_token.check_token(user, token):
        return False
    if profile:
        profile.email_verified    =   True
        profile.email_verified_at =   timezone.now()
        profile.save(update_fields = ['email_verified', 'email_verified_at'])
    return True
#=================================
# PHONE VERIFICATION QUERYS (WhatsApp entrante — costo $0)
#=================================
#El usuario le escribe un código al número business de DAVENT por WhatsApp:
#la conversación la inicia él (service message → gratis en la Cloud API de
#Meta, sin SMS ni tarjetas de por medio). El webhook /api/webhooks/whatsapp/
#recibe el mensaje y confirma que el 'from' matchea profile.phone.
#WHATSAPP_VERIFY_NUMBER: número business en formato E.164 sin '+' (wa.me).
#Vacío = feature apagada: el endpoint de inicio responde 503.
WHATSAPP_VERIFY_NUMBER  =   config('WHATSAPP_VERIFY_NUMBER', default = '')
#Handshake del webhook (GET ?hub.verify_token) y firma HMAC de los POST
#entrantes (X-Hub-Signature-256). El secret vacío salta la firma SOLO en dev —
#en prod es obligatorio, sin él cualquiera forja "mensajes entrantes".
WHATSAPP_WEBHOOK_TOKEN  =   config('WHATSAPP_WEBHOOK_TOKEN', default = '')
WHATSAPP_APP_SECRET     =   config('WHATSAPP_APP_SECRET', default = '')
PHONE_CODE_TTL          =   600  #El código de verificación vive 10 minutos.
#Sin 0/O ni 1/I: el usuario copia el código a mano si el link no abre.
_PHONE_CODE_ALPHABET    =   'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
_PHONE_CODE_KEY         =   'phone_verify:{}'
_PHONE_CODE_RE          =   re.compile(r'DAVENT[^0-9A-Z]*([0-9A-Z]{6})')

def StartPhoneVerificationQuery(profile : UserProfile) -> tuple:
    """Genera el código de un solo uso y devuelve (code, link wa.me)."""
    code        =   ''.join(secrets.choice(_PHONE_CODE_ALPHABET) for _ in range(6))
    cache.set(_PHONE_CODE_KEY.format(code), profile.user_id, PHONE_CODE_TTL)
    text        =   f'DAVENT {code}'
    link        =   f'https://wa.me/{WHATSAPP_VERIFY_NUMBER}?text={quote(text)}'
    return code, link

def _national_phone(raw : str) -> str:
    #Normaliza a número nacional argentino: el perfil guarda +549... y Meta
    #reporta el 'from' como 549... — y un 54... sin el 9 debe matchear igual.
    digits  =   re.sub(r'\D', '', raw or '')
    if digits.startswith('54'):
        digits  =   digits[2:]
    if digits.startswith('9') and len(digits) > 10:
        digits  =   digits[1:]
    return digits

def ConfirmPhoneVerificationQuery(wa_from : str, text : str) -> bool:
    """
    Confirma el código recibido por el webhook: tiene que existir en cache
    (un solo uso, TTL) y el 'from' de WhatsApp tiene que ser el celular del
    perfil — verificar es probar posesión DEL número registrado, no de otro.
    """
    match   =   _PHONE_CODE_RE.search((text or '').upper())
    if not match:
        return False
    key     =   _PHONE_CODE_KEY.format(match.group(1))
    user_id =   cache.get(key)
    if not user_id:
        return False
    profile =   UserProfile.objects.filter(user_id = user_id).first()
    if not profile or not profile.phone:
        return False
    if _national_phone(profile.phone) != _national_phone(wa_from):
        return False
    profile.phone_verified    =   True
    profile.phone_verified_at =   timezone.now()
    profile.save(update_fields = ['phone_verified', 'phone_verified_at'])
    cache.delete(key)
    return True