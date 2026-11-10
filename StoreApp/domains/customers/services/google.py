"""
Login social Google de los COMPRADORES (por tienda).

El frontend renderiza el botón oficial de Google Identity Services con el
client_id que expone GET /api/customer-auth/google-config/<slug>/ y nos
manda el `credential` (ID token). Acá se verifica SERVER-SIDE contra el
endpoint tokeninfo de Google — jamás se confía en el email/nombre que
llega del cliente.

Audiencia (aud) esperada, en orden:
1. Si la tienda configuró su propio client (StoreOAuthConfig.
   google_client_id + enabled) → ese client_id (BYO).
2. Si `enabled` está activo sin client propio → el client central DAVENT
   (env GOOGLE_CLIENT_ID — la misma var del login social de usuarios).

Sin `enabled` no hay login social en esa tienda (503).
"""
import logging
import time

import requests
from django.db import IntegrityError, transaction
from django.utils import timezone

from StoreApp.domains.customers.models import Customer
from StoreApp.domains.customers.services.customers import (
    ensure_membership,
    normalize_email,
)
from StoreApp.domains.customers.services.mails import GOOGLE_CLIENT_ID

logger              =   logging.getLogger(__name__)
_GOOGLE_TOKENINFO   =   'https://oauth2.googleapis.com/tokeninfo'
_GOOGLE_ISSUERS     =   ('accounts.google.com', 'https://accounts.google.com')
_HTTP_TIMEOUT       =   10


class GoogleAuthError(Exception):
    """
    Falla de verificación del ID token de Google.
    code: 'invalid' (token trucho/ajeno/vencido), 'no_email' (la cuenta
    de Google no comparte correo — sin email no hay cuenta de comprador).
    """
    def __init__(self, code = 'invalid'):
        super().__init__(code)
        self.code   =   code


def store_google_client_id(store):
    """
    Client ID esperado para el `aud` del id_token de ESTA tienda:
    el propio si el dueño configuró BYO, si no el central DAVENT.
    Devuelve '' si el login social está apagado o no hay client usable.
    """
    oauth   =   getattr(store, 'oauth_config', None)
    if oauth is None or not oauth.enabled:
        return ''
    if oauth.has_own_client:
        return oauth.google_client_id.strip()
    return GOOGLE_CLIENT_ID


def google_login_enabled(store):
    return bool(store_google_client_id(store))


def verify_google_credential(credential, expected_client_id):
    """
    Consulta tokeninfo (Google valida firma/issuer/vencimiento) y exige:
    aud == client_id esperado de la tienda, iss de Google,
    email_verified = true y exp vigente. Devuelve los claims útiles.
    """
    credential   =   (credential or '').strip()
    if not credential or not expected_client_id:
        raise GoogleAuthError()
    try:
        resp    =   requests.get(
            _GOOGLE_TOKENINFO,
            params  =   {'id_token': credential},
            timeout =   _HTTP_TIMEOUT,
        )
        data    =   resp.json() if resp.ok else {}
    except (requests.RequestException, ValueError):
        logger.exception('Falló la consulta de tokeninfo de Google (customers)')
        raise GoogleAuthError()
    if not data:
        raise GoogleAuthError()
    #Audiencia: un token emitido para OTRA app Google no sirve acá.
    if data.get('aud') != expected_client_id:
        raise GoogleAuthError()
    if data.get('iss') not in _GOOGLE_ISSUERS:
        raise GoogleAuthError()
    #Vencimiento: tokeninfo ya rechaza expirados, doble check defensivo.
    try:
        if int(data.get('exp') or 0) <= int(time.time()):
            raise GoogleAuthError()
    except (TypeError, ValueError):
        raise GoogleAuthError()
    if not data.get('email'):
        raise GoogleAuthError('no_email')
    if str(data.get('email_verified')).lower() != 'true':
        raise GoogleAuthError()
    return {
        'sub'        :   data.get('sub'),
        'email'      :   data['email'].strip().lower(),
        'first_name' :   (data.get('given_name') or '')[:150],
        'last_name'  :   (data.get('family_name') or '')[:150],
        'provider'   :   'google',
    }


def google_customer_login(info, store):
    """
    Find-or-create del Customer por email VERIFICADO del provider y
    ensure de la membresía en `store`. Devuelve (customer, is_new).

    Alta nueva: password inutilizable (el login es solo social; si quiere
    clave después la pide por password-reset), email_verified=True — el
    provider ya lo verificó, NO sale mail de verificación.
    Cuenta existente: auto-link por email (Google garantiza la
    titularidad) y se completa verificación/nombres si faltaban.
    """
    email   =   normalize_email(info.get('email'))
    if not email:
        raise GoogleAuthError()
    customer    =   Customer.objects.filter(email = email).first()
    is_new      =   customer is None
    if is_new:
        try:
            with transaction.atomic():
                customer    =   Customer(email = email)
                customer.set_unusable_password()
                customer.first_name  =   info.get('first_name') or ''
                customer.last_name   =   info.get('last_name') or ''
                customer.email_verified      =   True
                customer.email_verified_at   =   timezone.now()
                customer.save()
                ensure_membership(customer, store)
        except IntegrityError:
            #Carrera de dos altas con el mismo correo: gana la primera.
            customer    =   Customer.objects.filter(email = email).first()
            if customer is None:
                raise
            is_new  =   False
    else:
        ensure_membership(customer, store)
        update_fields   =   []
        if not customer.email_verified:
            customer.email_verified      =   True
            customer.email_verified_at   =   timezone.now()
            update_fields   +=  ['email_verified', 'email_verified_at']
        if not customer.first_name and info.get('first_name'):
            customer.first_name  =   info['first_name']
            update_fields.append('first_name')
        if not customer.last_name and info.get('last_name'):
            customer.last_name   =   info['last_name']
            update_fields.append('last_name')
        if update_fields:
            customer.save(update_fields = update_fields)
    return customer, is_new
