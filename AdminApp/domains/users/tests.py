"""
Tests de seguridad del dominio users.

Cubren los flujos que no pueden romperse antes del lanzamiento:
- Anti-enumeración del reset de contraseña
- Policy de contraseñas en registro, cambio y reset
- Invalidación de sesiones (blacklist de refresh) tras cambiar la clave
- Verificación de email (token firmado, marcado, reset al cambiar correo)
- Verificación de celular por WhatsApp (código único, firma HMAC del webhook)
"""
import hashlib
import hmac
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.users.services.services import email_verification_token, StartPhoneVerificationQuery

STRONG_PASSWORD = 'Xq7#mP2vL9bT'
NEW_PASSWORD    = 'Kp4$wN8rT3sD'

REGISTER_URL        = '/api/register/'
RESET_URL           = '/api/password-reset/'
RESET_CONFIRM_URL   = '/api/password-reset/confirm/'
VERIFY_URL          = '/api/verify-email/'
REFRESH_URL         = '/api/token/refresh/'
PASSWORD_UPDATE_URL = '/api/password_update/'
USER_UPDATE_URL     = '/api/user/me/'
VERIFY_PHONE_URL    = '/api/verify-phone/'
WHATSAPP_HOOK_URL   = '/api/webhooks/whatsapp/'


def _location():
    province    =   Province.objects.create(name_province = 'Buenos Aires')
    zipcode     =   ZipCode.objects.create(zipcode = '1702')
    city        =   City.objects.create(name_city = 'Ciudadela', province = province, zipcode = zipcode)
    return province, city


def _make_user(username = 'cliente', email = 'cliente@gmail.com', verified = True, document = '30111222'):
    province, city  =   _location()
    user            =   User.objects.create_user(username = username, email = email, password = STRONG_PASSWORD)
    profile         =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   document,
        province        =   province,
        city            =   city,
        email_verified  =   verified,
    )
    return user, profile


def _refresh_for(user):
    return str(RefreshToken.for_user(user))


class PasswordResetTests(TestCase):
    """Anti-enumeración + invalidación de sesiones del flujo de reset."""

    def test_request_returns_same_response_for_existing_and_missing_email(self):
        _make_user()
        existing        =   self.client.post(RESET_URL, {'email': 'cliente@gmail.com'}, format = 'json')
        missing         =   self.client.post(RESET_URL, {'email': 'nadie@gmail.com'}, format = 'json')
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(existing.json(), missing.json())

    def test_confirm_rejects_invalid_token(self):
        user, _         =   _make_user()
        uid             =   urlsafe_base64_encode(force_bytes(user.pk))
        response        =   self.client.post(RESET_CONFIRM_URL, {
            'uid'               :   uid,
            'token'             :   'token-trucho',
            'new_password'      :   NEW_PASSWORD,
            'confirm_password'  :   NEW_PASSWORD,
        }, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_confirm_rejects_weak_password(self):
        user, _         =   _make_user()
        uid             =   urlsafe_base64_encode(force_bytes(user.pk))
        response        =   self.client.post(RESET_CONFIRM_URL, {
            'uid'               :   uid,
            'token'             :   default_token_generator.make_token(user),
            'new_password'      :   '12345678',
            'confirm_password'  :   '12345678',
        }, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_confirm_invalidates_all_refresh_sessions(self):
        user, _         =   _make_user()
        stale_refresh   =   _refresh_for(user)
        uid             =   urlsafe_base64_encode(force_bytes(user.pk))
        confirm         =   self.client.post(RESET_CONFIRM_URL, {
            'uid'               :   uid,
            'token'             :   default_token_generator.make_token(user),
            'new_password'      :   NEW_PASSWORD,
            'confirm_password'  :   NEW_PASSWORD,
        }, format = 'json')
        self.assertEqual(confirm.status_code, 200)
        #El refresh emitido antes del reset ya no sirve para renovar el access.
        refresh         =   self.client.post(REFRESH_URL, {'refresh': stale_refresh}, format = 'json')
        self.assertEqual(refresh.status_code, 401)
        #La clave vieja tampoco sirve para loguearse de nuevo.
        login           =   self.client.post('/api/token/', {'username': 'cliente', 'password': STRONG_PASSWORD}, format = 'json')
        self.assertEqual(login.status_code, 401)


class PasswordPolicyTests(TestCase):
    """AUTH_PASSWORD_VALIDATORS aplicada en alta y cambio de clave."""

    def _payload(self, password):
        province, city  =   _location()
        return {
            'username'          :   'nuevo.cliente',
            'email'             :   'nuevo@gmail.com',
            'password'          :   password,
            'confirm_password'  :   password,
            'first_name'        :   'Ana',
            'last_name'         :   'Perez',
            'tax_condition'     :   'CF',
            'type_document'     :   'DNI',
            'document'          :   '28123456',
            'province'          :   province.pk,
            'city'              :   city.pk,
            'address'           :   'Calle 123',
            'phone'             :   '+5491122334455',
            'accept_terms'      :   True,
        }

    def test_register_rejects_weak_password(self):
        response        =   self.client.post(REGISTER_URL, self._payload('12345678'), format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username = 'nuevo.cliente').exists())

    def test_register_accepts_strong_password(self):
        response        =   self.client.post(REGISTER_URL, self._payload(STRONG_PASSWORD), format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username = 'nuevo.cliente').exists())

    def test_password_change_rejects_weak_password(self):
        user, _         =   _make_user()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(PASSWORD_UPDATE_URL, {
            'old_password'    :   STRONG_PASSWORD,
            'new_password'    :   '12345678',
            'confirm_password':   '12345678',
        }, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_password_change_invalidates_other_sessions(self):
        user, _         =   _make_user()
        stale_refresh   =   _refresh_for(user)
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(PASSWORD_UPDATE_URL, {
            'old_password'    :   STRONG_PASSWORD,
            'new_password'    :   NEW_PASSWORD,
            'confirm_password':   NEW_PASSWORD,
        }, format = 'json')
        self.assertEqual(response.status_code, 200)
        refresh         =   APIClient().post(REFRESH_URL, {'refresh': stale_refresh}, format = 'json')
        self.assertEqual(refresh.status_code, 401)


class EmailVerificationTests(TestCase):
    """Token firmado, marcado del perfil y reset al cambiar el correo."""

    def test_verify_email_marks_profile_and_redirects(self):
        user, profile   =   _make_user(verified = False)
        uid             =   urlsafe_base64_encode(force_bytes(user.pk))
        token           =   email_verification_token.make_token(user)
        response        =   self.client.get(VERIFY_URL, {'uid': uid, 'token': token})
        self.assertEqual(response.status_code, 302)
        self.assertIn('status=ok', response['Location'])
        profile.refresh_from_db()
        self.assertTrue(profile.email_verified)

    def test_verify_email_rejects_bad_token(self):
        user, profile   =   _make_user(verified = False)
        uid             =   urlsafe_base64_encode(force_bytes(user.pk))
        response        =   self.client.get(VERIFY_URL, {'uid': uid, 'token': 'trucho'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('status=error', response['Location'])
        profile.refresh_from_db()
        self.assertFalse(profile.email_verified)

    def test_email_change_resets_verification(self):
        user, profile   =   _make_user(verified = True)
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(USER_UPDATE_URL, {'email': 'otro@gmail.com'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertFalse(profile.email_verified)

    def test_user_update_no_server_error(self):
        """Regresión: el mixin compartido explotaba con KeyError (500)."""
        user, _         =   _make_user()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(USER_UPDATE_URL, {'email': 'cambiado@gmail.com'}, format = 'json')
        self.assertNotEqual(response.status_code, 500)


class PhoneVerificationTests(TestCase):
    """Código de un solo uso + webhook de Meta con firma HMAC fail-closed."""

    VIEWS_MODULE    =   'AdminApp.domains.users.views.auth_views'
    PHONE           =   '+5491122334455'    #formato del perfil (con + y 9)
    PHONE_WA        =   '5491122334455'     #formato del 'from' de WhatsApp

    def _user_with_phone(self):
        user, profile       =   _make_user()
        profile.phone       =   self.PHONE
        profile.save(update_fields = ['phone'])
        return user, profile

    def _webhook_payload(self, wa_from, text):
        return {
            'object': 'whatsapp_business_account',
            'entry': [{'changes': [{'field': 'messages', 'value': {
                'messages': [{'from': wa_from, 'id': 'wamid.x', 'type': 'text', 'text': {'body': text}}],
            }}]}],
        }

    def test_start_requires_auth(self):
        response    =   APIClient().post(VERIFY_PHONE_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 401)

    def test_start_returns_code_and_whatsapp_link(self):
        user, _         =   self._user_with_phone()
        client          =   APIClient()
        client.force_authenticate(user = user)
        with patch(f'{self.VIEWS_MODULE}.WHATSAPP_VERIFY_NUMBER', '5491111111111'), \
             patch('AdminApp.domains.users.services.services.WHATSAPP_VERIFY_NUMBER', '5491111111111'):
            response    =   client.post(VERIFY_PHONE_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('wa.me/5491111111111', response.json()['whatsapp_url'])

    def test_start_without_phone_is_rejected(self):
        user, _         =   _make_user()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(VERIFY_PHONE_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_webhook_marks_phone_verified_on_matching_number(self):
        user, profile   =   self._user_with_phone()
        code, _         =   StartPhoneVerificationQuery(profile)
        response        =   self.client.post(
            WHATSAPP_HOOK_URL,
            data            =   json.dumps(self._webhook_payload(self.PHONE_WA, f'DAVENT {code}')),
            content_type    =   'application/json',
        )
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertTrue(profile.phone_verified)

    def test_webhook_rejects_mismatched_number(self):
        user, profile   =   self._user_with_phone()
        code, _         =   StartPhoneVerificationQuery(profile)
        #El código es válido pero llega desde OTRO celular: no se verifica.
        self.client.post(
            WHATSAPP_HOOK_URL,
            data            =   json.dumps(self._webhook_payload('549223334444', f'DAVENT {code}')),
            content_type    =   'application/json',
        )
        profile.refresh_from_db()
        self.assertFalse(profile.phone_verified)

    def test_webhook_enforces_signature_when_secret_set(self):
        secret          =   'app-secret-meta'
        user, profile   =   self._user_with_phone()
        code, _         =   StartPhoneVerificationQuery(profile)
        body            =   json.dumps(self._webhook_payload(self.PHONE_WA, f'DAVENT {code}')).encode()
        with patch(f'{self.VIEWS_MODULE}.WHATSAPP_APP_SECRET', secret):
            unsigned    =   self.client.post(WHATSAPP_HOOK_URL, data = body, content_type = 'application/json')
            forged      =   self.client.post(
                WHATSAPP_HOOK_URL, data = body, content_type = 'application/json',
                HTTP_X_HUB_SIGNATURE_256 = 'sha256=firma-trucha',
            )
            self.assertEqual(unsigned.status_code, 401)
            self.assertEqual(forged.status_code, 401)
            signature   =   'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            valid       =   self.client.post(
                WHATSAPP_HOOK_URL, data = body, content_type = 'application/json',
                HTTP_X_HUB_SIGNATURE_256 = signature,
            )
            self.assertEqual(valid.status_code, 200)
        profile.refresh_from_db()
        self.assertTrue(profile.phone_verified)

    def test_webhook_handshake_needs_verify_token(self):
        with patch(f'{self.VIEWS_MODULE}.WHATSAPP_WEBHOOK_TOKEN', 'token-secreto'):
            bad     =   self.client.get(WHATSAPP_HOOK_URL, {'hub.mode': 'subscribe', 'hub.verify_token': 'otro', 'hub.challenge': 'abc'})
            ok      =   self.client.get(WHATSAPP_HOOK_URL, {'hub.mode': 'subscribe', 'hub.verify_token': 'token-secreto', 'hub.challenge': 'abc'})
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.content, b'abc')

    def test_profile_update_resets_verification_on_phone_change(self):
        """Cambiar el celular invalida la verificación (igual que el correo)."""
        user, profile   =   self._user_with_phone()
        profile.phone_verified      =   True
        profile.save(update_fields = ['phone_verified'])
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put('/api/profile/me/', {
            'tax_condition' :   'CF',
            'business_name' :   None,
            'type_document' :   'DNI',
            'document'      :   profile.document,
            'first_name'    :   profile.first_name,
            'last_name'     :   profile.last_name,
            'province'      :   profile.province_id,
            'city'          :   profile.city_id,
            'address'       :   None,
            'phone'         :   '+5491199988877',
        }, format = 'json')
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertFalse(profile.phone_verified)
