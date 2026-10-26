#=================================
# SOCIAL LOGIN (Google — token exchange a sesión DAVENT)
#=================================
#El frontend abre el consent del provider (botón oficial de Google Identity
#Services) y nos manda la credencial. Acá la validamos SERVER-SIDE contra el
#provider — jamás se confía en el email o el nombre que llega del cliente —
#y resolvemos el find-or-create de la cuenta.
#Env var: GOOGLE_CLIENT_ID — si no está definida se usa el client ID del
#proyecto (es público por diseño: viaja en el bundle del frontend); seteada
#vacía explícitamente apaga la feature (endpoint 503 y botón oculto). Se lee
#en cada import para que los tests la patcheen.
import logging
import re
from datetime import timedelta

import requests
from decouple import config
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.utils import timezone

from AdminApp.domains.users.models import UserProfile, TERMS_VERSION
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan

logger                  =   logging.getLogger(__name__)
_DEFAULT_GOOGLE_ID      =   '10828662216-ff1ocahbbaj7ul6qpv3p5c3so3jk25p7.apps.googleusercontent.com'
GOOGLE_CLIENT_ID        =   config('GOOGLE_CLIENT_ID', default = _DEFAULT_GOOGLE_ID)
_GOOGLE_TOKENINFO       =   'https://oauth2.googleapis.com/tokeninfo'
_HTTP_TIMEOUT           =   10


class SocialAuthError(Exception):
    """
    Falla de verificación social. code:
      'invalid'  — el provider rechazó la credencial (token trucho, de otra
                   app o vencido). El usuario solo ve "intentá de nuevo".
      'no_email' — la cuenta del provider no comparte email. Sin email no hay
                   cuenta DAVENT posible: se pide que la vincule o que se
                   registre con el formulario.
    """
    def __init__(self, code = 'invalid'):
        super().__init__(code)
        self.code   =   code


def VerifyGoogleCredentialQuery(credential : str) -> dict:
    """
    El ID token de Google se consulta en tokeninfo: Google valida firma e
    issuer server-side y devuelve los claims. Nosotros exigimos aud = nuestro
    client_id (un token de OTRA app Google no sirve) y email_verified = true.
    """
    if not (credential or '').strip():
        raise SocialAuthError()
    try:
        resp    =   requests.get(_GOOGLE_TOKENINFO, params = {'id_token': credential}, timeout = _HTTP_TIMEOUT)
        data    =   resp.json() if resp.ok else {}
    except (requests.RequestException, ValueError):
        logger.exception('Falló la consulta de tokeninfo de Google')
        raise SocialAuthError()
    if not data or data.get('aud') != GOOGLE_CLIENT_ID:
        raise SocialAuthError()
    if str(data.get('email_verified')).lower() != 'true' or not data.get('email'):
        raise SocialAuthError('no_email' if not data.get('email') else 'invalid')
    return {
        'sub'        :   data.get('sub'),
        'email'      :   data['email'],
        'first_name' :   data.get('given_name') or '',
        'last_name'  :   data.get('family_name') or '',
        'provider'   :   'google',
    }


def _social_username(email : str) -> str:
    #El username sale del local-part del correo, saneado a la convención del
    #formulario (minúsculas, letras/números/punto/guión/_) y deduplicado con
    #sufijo incremental si ya existe.
    base        =   re.sub(r'[^a-z0-9._-]', '', (email.split('@')[0] or 'usuario').lower()) or 'usuario'
    base        =   base[:25]
    candidate   =   base
    counter     =   2
    while User.objects.filter(username__iexact = candidate).exists():
        candidate   =   f'{base}{counter}'
        counter     +=  1
    return candidate


def SocialLoginQuery(info : dict) -> tuple:
    """
    Find-or-create por email VERIFICADO del provider. Devuelve (user, is_new).

    Alta nueva (is_new): password inutilizable (el login es solo social; si
    quiere clave después la setea por password-reset), email_verified=True —
    el provider ya lo verificó, por eso NO sale el mail de verificación —,
    TyC sellados (consentimiento explícito bajo los botones) y plan trial,
    mismas garantías que RegisterUserQuery.

    Cuenta existente con ese email: se loguea directo (auto-link — Google
    garantiza la titularidad del correo) y se completa email_verified
    /nombres si faltaban.
    """
    email   =   (info.get('email') or '').strip().lower()
    if not email:
        raise SocialAuthError()
    user    =   User.objects.filter(email__iexact = email).first()
    is_new  =   user is None
    if is_new:
        try:
            with transaction.atomic():
                user    =   User(username = _social_username(email), email = email)
                user.set_unusable_password()
                user.save()
                now     =   timezone.now()
                UserProfile.objects.create(
                    user                =   user,
                    first_name          =   (info.get('first_name') or '')[:150] or None,
                    last_name           =   (info.get('last_name') or '')[:150] or None,
                    email_verified      =   True,
                    email_verified_at   =   now,
                    terms_accepted      =   True,
                    terms_accepted_at   =   now,
                    terms_version       =   TERMS_VERSION,
                )
                trial_plan  =   SuscriptionPlan.objects.filter(is_trial = True).first()
                if trial_plan:
                    Suscription.objects.create(
                        user                =   user.profile,
                        plan_suscription    =   trial_plan,
                        status              =   Suscription.STATUS_ACTIVE,
                        start_date          =   now,
                        end_date            =   now + timedelta(days = SuscriptionPlan.TRIAL_DAYS),
                    )
        except IntegrityError:
            #Carrera de dos altas con el mismo correo: gana la primera y la
            #segunda entra como login de la cuenta ya creada.
            user    =   User.objects.filter(email__iexact = email).first()
            if user is None:
                raise
            is_new  =   False
    #El alta social no pide celular (el provider no lo da): profile queda con
    #phone=None y el claim de la web lo exige aparte — el ancla anti-abuso se
    #conserva sin bloquear el ingreso al panel.
    profile, _  =   UserProfile.objects.get_or_create(user = user)
    update_fields   =   []
    if not profile.email_verified:
        profile.email_verified      =   True
        profile.email_verified_at   =   timezone.now()
        update_fields   +=  ['email_verified', 'email_verified_at']
    if not profile.first_name and info.get('first_name'):
        profile.first_name  =   info['first_name'][:150] or None
        update_fields.append('first_name')
    if not profile.last_name and info.get('last_name'):
        profile.last_name   =   info['last_name'][:150] or None
        update_fields.append('last_name')
    if update_fields:
        profile.save(update_fields = update_fields)
    return user, is_new
