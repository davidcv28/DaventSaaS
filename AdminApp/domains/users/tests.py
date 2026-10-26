"""
Tests de seguridad del dominio users.

Cubren los flujos que no pueden romperse antes del lanzamiento:
- Anti-enumeración del reset de contraseña
- Policy de contraseñas en registro, cambio y reset
- Invalidación de sesiones (blacklist de refresh) tras cambiar la clave
- Verificación de email (token firmado, marcado, reset al cambiar correo)
"""
from unittest.mock import patch, Mock

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.users.services.services import email_verification_token

STRONG_PASSWORD = 'Xq7#mP2vL9bT'
NEW_PASSWORD    = 'Kp4$wN8rT3sD'

REGISTER_URL        = '/api/register/'
RESET_URL           = '/api/password-reset/'
RESET_CONFIRM_URL   = '/api/password-reset/confirm/'
VERIFY_URL          = '/api/verify-email/'
REFRESH_URL         = '/api/token/refresh/'
PASSWORD_UPDATE_URL = '/api/password_update/'
USER_UPDATE_URL     = '/api/user/me/'
GOOGLE_AUTH_URL     = '/api/auth/google/'


def _location():
    province    =   Province.objects.get_or_create(name_province = 'Buenos Aires')[0]
    zipcode     =   ZipCode.objects.get_or_create(zipcode = '1702')[0]
    city        =   City.objects.get_or_create(name_city = 'Ciudadela', province = province, zipcode = zipcode)[0]
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
        #Alta minimal: los datos fiscales se piden recién al pagar un plan.
        return {
            'username'          :   'nuevo.cliente',
            'email'             :   'nuevo@gmail.com',
            'password'          :   password,
            'confirm_password'  :   password,
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

    def test_profile_update_resets_verification_on_phone_change(self):
        """Cambiar el celular resetea phone_verified (misma regla que el correo)."""
        user, profile   =   _make_user()
        profile.phone           =   '+5491122334455'
        profile.phone_verified  =   True
        profile.save(update_fields = ['phone', 'phone_verified'])
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


class SessionCookieTests(TestCase):
    """
    Sesión web: el refresh viaja en cookie httpOnly scopeada a /api/token/
    y el refresh por cookie exige CSRF de doble-submit. El flag "mantener
    sesión" define si las cookies son persistentes o de sesión del browser.
    """
    LOGIN_URL   =   '/api/token/'
    LOGOUT_URL  =   '/api/token/logout/'

    def setUp(self):
        #El throttle del login corre sobre el cache locmem compartido de
        #toda la suite: sin limpiarlo, los logins de otros tests consumen
        #el cupo por IP y el endpoint respondería 429.
        cache.clear()

    def _login(self, remember = None):
        payload     =   {'username': 'cliente', 'password': STRONG_PASSWORD}
        if remember is not None:
            payload['remember'] =   remember
        return self.client.post(self.LOGIN_URL, payload, format = 'json')

    def test_login_sets_http_only_refresh_and_csrf_cookies(self):
        _make_user()
        response        =   self._login()
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        #El refresh jamás viaja en el body: solo cookie httpOnly (anti-XSS).
        self.assertNotIn('refresh', response.json())
        refresh         =   response.cookies.get('davent_refresh')
        self.assertIsNotNone(refresh)
        self.assertTrue(refresh['httponly'])
        self.assertEqual(refresh['path'], '/api/token/')
        self.assertIsNotNone(response.cookies.get('davent_csrf'))

    def test_remember_true_makes_cookies_persistent(self):
        _make_user()
        response        =   self._login(remember = True)
        refresh         =   response.cookies['davent_refresh']
        self.assertTrue(int(refresh['max-age'] or 0) > 0)
        self.assertEqual(response.cookies['davent_remember'].value, '1')

    def test_remember_string_false_stays_session_cookie(self):
        #Regresión de seguridad: bool('false') era True — un POST form-encoded
        #con remember='false' convertía la sesión efímera en persistente.
        _make_user()
        response        =   self._login(remember = 'false')
        refresh         =   response.cookies['davent_refresh']
        self.assertFalse(refresh['max-age'])
        self.assertIsNone(response.cookies.get('davent_remember'))

    def test_login_failure_sets_no_cookies(self):
        _make_user()
        response        =   self.client.post(self.LOGIN_URL, {'username': 'cliente', 'password': 'clave-mala'}, format = 'json')
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(response.cookies.get('davent_refresh'))

    def test_cookie_refresh_requires_csrf(self):
        #Sin X-CSRFToken el POST por cookie se rechaza (doble-submit).
        _make_user()
        self._login()
        response        =   self.client.post(REFRESH_URL)
        self.assertEqual(response.status_code, 403)

    def test_cookie_refresh_with_csrf_returns_access(self):
        _make_user()
        login           =   self._login()
        csrf            =   login.cookies['davent_csrf'].value
        response        =   self.client.post(REFRESH_URL, HTTP_X_CSRFTOKEN = csrf)
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())

    def test_logout_blacklists_refresh_cookie(self):
        _make_user()
        login           =   self._login()
        csrf            =   login.cookies['davent_csrf'].value
        stale           =   login.cookies['davent_refresh'].value
        out             =   self.client.post(self.LOGOUT_URL, HTTP_X_CSRFTOKEN = csrf)
        self.assertEqual(out.status_code, 200)
        #El refresh que viajaba en la cookie quedó en blacklist (replay: 401).
        refresh         =   APIClient().post(REFRESH_URL, {'refresh': stale}, format = 'json')
        self.assertEqual(refresh.status_code, 401)

    def test_logout_without_cookie_is_idempotent(self):
        response        =   self.client.post(self.LOGOUT_URL)
        self.assertEqual(response.status_code, 200)


class RegisterSecurityTests(TestCase):
    """
    Anti multi-cuenta del alta: solo anónimos, unicidad case-insensitive
    de email/username y trial automático de un día.
    """

    def setUp(self):
        #Throttle 'register' 10/h sobre cache compartido: reset por test.
        cache.clear()

    def _payload(self, **overrides):
        #Alta minimal: sin datos fiscales — el ancla anti-abuso es el celular.
        payload         =   {
            'username'          :   'nuevo.cliente',
            'email'             :   'nuevo@gmail.com',
            'password'          :   STRONG_PASSWORD,
            'confirm_password'  :   STRONG_PASSWORD,
            'phone'             :   '+5491122334455',
            'accept_terms'      :   True,
        }
        payload.update(overrides)
        return payload

    def test_register_rejects_authenticated_user(self):
        user, _         =   _make_user()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(REGISTER_URL, self._payload(), format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_register_rejects_case_variant_email(self):
        #Regresión: la unicidad era case-sensitive — NUEVO@GMAIL.COM abría
        #una segunda cuenta con el mismo correo (bypass anti multi-cuenta).
        self.client.post(REGISTER_URL, self._payload(phone = '+5491100000001'), format = 'json')
        response        =   self.client.post(REGISTER_URL, self._payload(
            email = 'NUEVO@GMAIL.COM', phone = '+5491100000002'), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_register_rejects_case_variant_username(self):
        self.client.post(REGISTER_URL, self._payload(phone = '+5491100000001'), format = 'json')
        response        =   self.client.post(REGISTER_URL, self._payload(
            username = 'NUEVO.CLIENTE', phone = '+5491100000002'), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_register_grants_one_day_trial(self):
        trial           =   SuscriptionPlan.objects.create(name = 'Plan de prueba', price = 0, is_trial = True)
        response        =   self.client.post(REGISTER_URL, self._payload(), format = 'json')
        self.assertEqual(response.status_code, 201)
        suscription     =   Suscription.objects.get(user__user__username = 'nuevo.cliente')
        self.assertEqual(suscription.plan_suscription, trial)
        self.assertTrue(suscription.grants_access())
        self.assertLess((suscription.end_date - suscription.start_date).days, 2)


class DeferredBillingDataTests(TestCase):
    """
    El alta ya no pide datos fiscales: el perfil nace sin ellos y se
    completan por PATCH (form de facturación) antes de poder pagar.
    """

    PROFILE_URL =   '/api/profile/me/'

    def setUp(self):
        cache.clear()

    def _minimal_payload(self, **overrides):
        payload =   {
            'username'          :   'nuevo.cliente',
            'email'             :   'nuevo@gmail.com',
            'password'          :   STRONG_PASSWORD,
            'confirm_password'  :   STRONG_PASSWORD,
            'phone'             :   '+5491122334455',
            'accept_terms'      :   True,
        }
        payload.update(overrides)
        return payload

    def _bare_user(self, username = 'cliente', email = 'cliente@gmail.com', phone = '+5491100000000'):
        user        =   User.objects.create_user(username = username, email = email, password = STRONG_PASSWORD)
        profile     =   UserProfile.objects.create(user = user, phone = phone)
        return user, profile

    def test_register_minimal_creates_profile_without_billing_data(self):
        response        =   self.client.post(REGISTER_URL, self._minimal_payload(), format = 'json')
        self.assertEqual(response.status_code, 201)
        profile         =   UserProfile.objects.get(user__username = 'nuevo.cliente')
        self.assertIsNone(profile.document)
        self.assertIsNone(profile.first_name)
        self.assertIsNone(profile.last_name)
        self.assertIsNone(profile.province_id)
        self.assertIsNone(profile.city_id)
        #Los defaults no-fiscales siguen sellados: condición CF y TyC.
        self.assertEqual(profile.tax_condition, 'CF')
        self.assertTrue(profile.terms_accepted)

    def test_register_still_requires_phone_and_terms(self):
        #El celular queda: es el ancla anti-abuso multi-cuenta, no un dato fiscal.
        response        =   self.client.post(REGISTER_URL, self._minimal_payload(phone = ''), format = 'json')
        self.assertEqual(response.status_code, 400)
        response        =   self.client.post(REGISTER_URL, self._minimal_payload(accept_terms = False), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_profile_patch_fills_billing_data(self):
        user, _         =   self._bare_user()
        province, city  =   _location()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(self.PROFILE_URL, {
            'first_name'    :   'Ana',
            'last_name'     :   'Perez',
            'tax_condition' :   'CF',
            'document'      :   '28123456',
            'province'      :   province.pk,
            'city'          :   city.pk,
            'address'       :   'Calle 123',
        }, format = 'json')
        self.assertEqual(response.status_code, 200, response.json())
        profile         =   UserProfile.objects.get(user = user)
        self.assertEqual(profile.document, '28123456')
        self.assertEqual(profile.type_document, 'DNI')
        self.assertEqual(profile.city_id, city.pk)

    def test_profile_patch_derives_cuit_and_requires_business_name(self):
        #RI/MO exigen CUIT válido + razón social (regla fiscal del emisor).
        user, _         =   self._bare_user()
        province, city  =   _location()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(self.PROFILE_URL, {
            'first_name'    :   'Ana',
            'last_name'     :   'Perez',
            'tax_condition' :   'RI',
            'document'      :   '28123456',
            'province'      :   province.pk,
            'city'          :   city.pk,
        }, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('business_name', response.json())
        #CUIT válido + razón social -> type_document se deriva a CUIT.
        response        =   client.put(self.PROFILE_URL, {
            'first_name'    :   'Ana',
            'last_name'     :   'Perez',
            'tax_condition' :   'RI',
            'business_name' :   'Estudio Norte',
            'document'      :   '20234567897',
            'province'      :   province.pk,
            'city'          :   city.pk,
        }, format = 'json')
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(UserProfile.objects.get(user = user).type_document, 'CUIT')

    def test_profile_patch_rejects_half_location(self):
        #Provincia sin ciudad (o al revés) no sirve para facturar.
        user, _         =   self._bare_user()
        province, city  =   _location()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(self.PROFILE_URL, {'province': province.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)
        response        =   client.put(self.PROFILE_URL, {'city': city.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_profile_patch_allows_partial_non_fiscal(self):
        #Un PATCH que no toca datos fiscales no exige nada de ellos.
        user, _         =   self._bare_user()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(self.PROFILE_URL, {'phone': '+5491198877665'}, format = 'json')
        self.assertEqual(response.status_code, 200, response.json())
        profile         =   UserProfile.objects.get(user = user)
        self.assertEqual(profile.phone, '+5491198877665')
        self.assertIsNone(profile.document)

    def test_document_uniqueness_still_enforced_on_patch(self):
        #El documento sigue siendo único cuando se carga (anti multi-cuenta).
        _make_user()
        user, _         =   self._bare_user(username = 'otro', email = 'otro@gmail.com', phone = '+5491100000001')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(self.PROFILE_URL, {'document': '30111222'}, format = 'json')
        self.assertEqual(response.status_code, 400)


class EmailVerificationTokenTests(TestCase):
    """El link de verificación no debe romperse con el primer login."""

    def test_verification_token_survives_first_login(self):
        #Regresión: el hash incluía last_login — loguearse después del alta
        #(antes de abrir el mail) invalidaba el link de verificación.
        user, profile   =   _make_user(verified = False)
        token           =   email_verification_token.make_token(user)
        user.last_login =   timezone.now()
        user.save(update_fields = ['last_login'])
        uid             =   urlsafe_base64_encode(force_bytes(user.pk))
        response        =   self.client.get(VERIFY_URL, {'uid': uid, 'token': token})
        self.assertEqual(response.status_code, 302)
        self.assertIn('status=ok', response['Location'])
        profile.refresh_from_db()
        self.assertTrue(profile.email_verified)


class EmailUniquenessTests(TestCase):
    """La unicidad del correo es case-insensitive también en el update."""

    def test_user_update_rejects_case_variant_email(self):
        _make_user()
        user2, _        =   _make_user(username = 'otro', email = 'otro@gmail.com', document = '30999888')
        client          =   APIClient()
        client.force_authenticate(user = user2)
        response        =   client.put(USER_UPDATE_URL, {'email': 'CLIENTE@GMAIL.COM'}, format = 'json')
        self.assertEqual(response.status_code, 400)


class SocialAuthTests(TestCase):
    """
    Login social (Google): la credencial del provider se verifica server-side
    (mockeada) y el find-or-create emite la misma sesión JWT + cookies del
    login por contraseña.
    """

    VIEWS_MODULE    =   'AdminApp.domains.users.views.auth_views'
    SOCIAL_MODULE   =   'AdminApp.domains.users.services.social'
    CLIENT_ID       =   'google-client-id'

    def setUp(self):
        cache.clear()

    # ---------- respuestas mockeadas del provider ----------
    def _tokeninfo(self, **over):
        #tokeninfo de Google: solo devuelve claims si el ID token es válido.
        data    =   {
            'aud'           :   self.CLIENT_ID,
            'iss'           :   'https://accounts.google.com',
            'sub'           :   'g-123',
            'email'         :   'social@gmail.com',
            'email_verified':   'true',
            'given_name'    :   'Sofía',
            'family_name'   :   'Pereyra',
        }
        data.update(over)
        resp        =   Mock()
        resp.ok     =   True
        resp.json   =   lambda: data
        return resp

    # ---------- helpers de env + post ----------
    def _post_google(self, payload = None, tokeninfo = None, client_id = None):
        env =   self.CLIENT_ID if client_id is None else client_id
        with patch(f'{self.VIEWS_MODULE}.GOOGLE_CLIENT_ID', env), \
             patch(f'{self.SOCIAL_MODULE}.GOOGLE_CLIENT_ID', env), \
             patch(f'{self.SOCIAL_MODULE}.requests.get', return_value = tokeninfo or self._tokeninfo()):
            return APIClient().post(GOOGLE_AUTH_URL, payload if payload is not None else {'credential': 'id-token'}, format = 'json')
    def test_google_creates_account_with_trial_and_verified_email(self):
        trial       =   SuscriptionPlan.objects.create(name = 'Plan de prueba', price = 0, is_trial = True)
        response    =   self._post_google()
        self.assertEqual(response.status_code, 200)
        data        =   response.json()
        self.assertTrue(data['is_new'])
        self.assertTrue(data['requires_phone'])
        self.assertIn('access', data)
        self.assertIn('davent_refresh', response.cookies)
        user        =   User.objects.get(email = 'social@gmail.com')
        self.assertFalse(user.has_usable_password())
        profile     =   user.profile
        self.assertTrue(profile.email_verified)
        self.assertIsNotNone(profile.email_verified_at)
        self.assertEqual(profile.first_name, 'Sofía')
        self.assertEqual(profile.last_name, 'Pereyra')
        self.assertIsNone(profile.phone)
        self.assertTrue(profile.terms_accepted)
        suscription =   Suscription.objects.get(user = profile)
        self.assertEqual(suscription.plan_suscription, trial)
        self.assertTrue(suscription.grants_access())

    def test_google_links_existing_user_by_email(self):
        #Auto-link: el provider ya verificó el correo — si la cuenta lo tenía
        #pendiente queda verificado al entrar.
        user, profile   =   _make_user(email = 'social@gmail.com', verified = False)
        profile.phone   =   '+5491100000009'
        profile.save(update_fields = ['phone'])
        response        =   self._post_google()
        self.assertEqual(response.status_code, 200)
        data            =   response.json()
        self.assertFalse(data['is_new'])
        self.assertFalse(data['requires_phone'])
        profile.refresh_from_db()
        self.assertTrue(profile.email_verified)

    def test_google_rejects_token_from_other_app(self):
        #aud != nuestro client_id: un token emitido para otra app no sirve.
        response    =   self._post_google(tokeninfo = self._tokeninfo(aud = 'otra-app'))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email = 'social@gmail.com').exists())

    def test_google_rejects_unverified_email(self):
        response    =   self._post_google(tokeninfo = self._tokeninfo(email_verified = 'false'))
        self.assertEqual(response.status_code, 400)

    def test_google_rejects_missing_credential(self):
        response    =   self._post_google(payload = {})
        self.assertEqual(response.status_code, 400)

    def test_google_503_without_client_id(self):
        response    =   self._post_google(client_id = '')
        self.assertEqual(response.status_code, 503)
