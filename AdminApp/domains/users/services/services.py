import logging
from datetime import timedelta

from decouple import config
from AdminApp.domains.users.models import UserProfile, TERMS_VERSION
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import escape
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

logger          =   logging.getLogger(__name__)
#Vacío en .env != ausente: un valor vacío también cae al default de dev.
FRONTEND_URL    =   config('FRONTEND_URL', default = '') or 'http://localhost:5173'
#=================================
# USER MODEL QUERYS
#=================================

#USER UPDATE QUERY
def UpdateUserQuery(user: User, validated_data : dict) -> User:
    user.email = validated_data['email'].strip()
    user.save()
    return user

#USER PASSWORD UPDATE
def UpdatePasswordUserQuery(user : User, validated_data : dict) -> User:
    new_password = validated_data['new_password']
    user.set_password(new_password)
    user.save()
    return user



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
        return new_user
#=================================
# ACCOUNT MAIL / TOKEN HELPERS
#=================================
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
