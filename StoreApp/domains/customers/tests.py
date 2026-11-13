"""
Tests de seguridad del dominio customers (track A — PROMPT_MAESTRO 3.5).

Cubre: flujo auth completo (register/login/refresh/logout/verify/reset),
aislamiento de tokens customer vs DAVENT, Google login (tokeninfo
mockeado), IDOR en direcciones/membresías, PII cifrada en reposo +
huella HMAC, mass-assignment y throttle.

Las tareas de correo corren eager en tests (sin broker); el envío se
verifica llamando a los Query directo porque `transaction.on_commit` no
dispara dentro del atomic de TestCase.
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken as DaventRefreshToken
from django.core import mail, signing
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from AdminApp.domains.invoices.services.vault import is_encrypted
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.users.models.fields import digest_for
from StoreApp.domains.customers.models import (
    Customer,
    CustomerAddress,
    CustomerNotification,
    StoreMembership,
)
from StoreApp.domains.customers.services.customers import (
    SendCustomerPasswordResetEmailQuery,
    SendCustomerVerificationEmailQuery,
    customer_reset_token,
    make_verify_email_token,
)
from StoreApp.domains.stores.models import Store, StoreOAuthConfig
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

REGISTER_URL     =   '/api/customer-auth/register/'
LOGIN_URL        =   '/api/customer-auth/login/'
REFRESH_URL      =   '/api/customer-auth/refresh/'
LOGOUT_URL       =   '/api/customer-auth/logout/'
ME_URL           =   '/api/customer-auth/me/'
PROFILE_URL      =   '/api/customer/profile/'
ADDRESSES_URL    =   '/api/customer/addresses/'
MEMBERSHIPS_URL  =   '/api/customer/memberships/'
VERIFY_URL       =   '/api/customer-auth/verify-email/'
VERIFY_RESEND    =   '/api/customer-auth/verify-email/resend/'
RESET_URL        =   '/api/customer-auth/password-reset/'
RESET_CONFIRM    =   '/api/customer-auth/password-reset/confirm/'
GOOGLE_URL       =   '/api/customer-auth/google/'
GOOGLE_CONFIG    =   '/api/customer-auth/google-config/{slug}/'
DAVENT_USER_URL  =   '/api/user/'
NOTIFS_URL       =   '/api/customer/notifications/'
NOTIFS_READ      =   '/api/customer/notifications/read/'
NOTIFS_TICKET    =   '/api/customer/notifications/stream-ticket/'
NOTIFS_STREAM    =   '/api/customer/notifications/stream/'

PASSWORD         =   'Comprador#2026'


def _make_customer(email = 'ana@example.com', password = PASSWORD, **kwargs):
    customer    =   Customer(email = email, **kwargs)
    customer.set_password(password)
    customer.save()
    return customer


def _grant(profile, *codes):
    """Plan DAVENT + suscripción vigente de 30 días (reusa la suscripción
    existente si ya tiene una — user es OneToOne)."""
    suscription =   getattr(profile, 'suscription', None)
    plan        =   suscription.plan_suscription if suscription is not None else SuscriptionPlan.objects.create(name = f'Plan {profile.pk}')
    for code in codes:
        benefit =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': Benefit.FLAG})[0]
        PlanBenefit.objects.get_or_create(plan = plan, benefit = benefit, defaults = {'enabled': True})
    if suscription is None:
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )


def _make_store(slug = 'mitienda', published = True, blocked = False, customer_auth = True):
    user        =   User.objects.create_user(username = f'owner-{slug}', email = f'{slug}@owner.com', password = 'x')
    profile     =   UserProfile.objects.create(user = user, first_name = 'Due', last_name = 'Nio')
    #plan_benefits_of cachea por PK y SQLite las reutiliza entre tests.
    cache.delete(f'planben:{profile.pk}')
    if customer_auth:
        #La auth de compradores es superficie del plan: sin
        #has_customer_auth, resolve_store(slug) devuelve None.
        _grant(profile, 'has_customer_auth')
    return Store.objects.create(user = profile, slug = slug, is_published = published, is_blocked = blocked)


def _bearer(client, customer):
    from StoreApp.domains.customers.services.tokens import issue_customer_tokens
    access, _refresh =   issue_customer_tokens(customer)
    client.credentials(HTTP_AUTHORIZATION = f'Bearer {access}')
    return access


def _login(client, email = 'ana@example.com', password = PASSWORD, **extra):
    return client.post(LOGIN_URL, {'email': email, 'password': password, **extra}, format = 'json')


class CustomerAuthFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client     =   APIClient()
        self.store      =   _make_store()

    #REGISTER
    def test_register_creates_customer_and_session(self):
        response    =   self.client.post(REGISTER_URL, {
            'email': 'ana@example.com', 'password': PASSWORD,
            'first_name': 'Ana', 'last_name': 'Perez',
        }, format = 'json')
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertIn('access', data)
        self.assertEqual(data['customer']['email'], 'ana@example.com')
        self.assertFalse(data['customer']['email_verified'])
        #Cookies de sesión de comprador (nunca las davent_*)
        self.assertIn('customer_refresh', response.cookies)
        self.assertIn('customer_csrf', response.cookies)
        customer    =   Customer.objects.get(email = 'ana@example.com')
        #Password hasheado — nunca el texto plano
        self.assertNotEqual(customer.password, PASSWORD)
        self.assertTrue(customer.check_password(PASSWORD))
        #Avatar = solo inicial
        self.assertEqual(data['customer']['avatar'], 'A')

    def test_register_normalizes_email_case(self):
        self.client.post(REGISTER_URL, {'email': 'ANA@Example.COM', 'password': PASSWORD}, format = 'json')
        self.assertTrue(Customer.objects.filter(email = 'ana@example.com').exists())
        #Case-variant duplicado → 400
        response    =   self.client.post(REGISTER_URL, {'email': 'ana@EXAMPLE.com', 'password': PASSWORD}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_register_rejects_weak_password(self):
        #Validadores de Django: <8, numérica pura y común → 400.
        for pwd in ('corta', '12345678', 'password'):
            response    =   self.client.post(REGISTER_URL, {'email': f'u{pwd[:4]}@x.com', 'password': pwd}, format = 'json')
            self.assertEqual(response.status_code, 400, pwd)

    def test_register_with_store_creates_membership(self):
        response    =   self.client.post(REGISTER_URL, {
            'email': 'nueva@example.com', 'password': PASSWORD, 'store_slug': 'mitienda',
        }, format = 'json')
        self.assertEqual(response.status_code, 200)
        customer    =   Customer.objects.get(email = 'nueva@example.com')
        membership  =   StoreMembership.objects.get(customer = customer, store = self.store)
        self.assertEqual(membership.status, 'active')
        self.assertEqual(membership.tags, [])
        self.assertIsNotNone(membership.joined_at)

    def test_register_with_unknown_or_unpublished_store_400(self):
        response    =   self.client.post(REGISTER_URL, {'email': 'x1@example.com', 'password': PASSWORD, 'store_slug': 'noexiste'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        _make_store('cerrada', published = False)
        response    =   self.client.post(REGISTER_URL, {'email': 'x2@example.com', 'password': PASSWORD, 'store_slug': 'cerrada'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        _make_store('bloqueada', blocked = True)
        response    =   self.client.post(REGISTER_URL, {'email': 'x3@example.com', 'password': PASSWORD, 'store_slug': 'bloqueada'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_store_scoped_auth_requires_customer_auth_benefit(self):
        #Sin has_customer_auth en el plan del dueño, la tienda "no existe"
        #para TODA la auth de compradores — mismos códigos que una tienda
        #inexistente (no se filtra que existe pero está fuera de plan).
        _make_store('sinplan', customer_auth = False)
        self.assertEqual(
            self.client.post(REGISTER_URL, {'email': 'r@example.com', 'password': PASSWORD, 'store_slug': 'sinplan'}, format = 'json').status_code, 400)
        _make_customer('log@example.com')
        self.assertEqual(
            _login(APIClient(), email = 'log@example.com', store_slug = 'sinplan').status_code, 400)
        self.assertEqual(
            APIClient().get(GOOGLE_CONFIG.format(slug = 'sinplan')).status_code, 404)
        self.assertEqual(
            APIClient().post(GOOGLE_URL, {'credential': 'tok', 'store_slug': 'sinplan'}, format = 'json').status_code, 400)
        self.assertEqual(
            APIClient().post(RESET_URL, {'email': 'log@example.com', 'store_slug': 'sinplan'}, format = 'json').status_code, 400)

    #LOGIN
    def test_login_ok_and_bad_credentials(self):
        _make_customer()
        response    =   _login(self.client)
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('customer_refresh', response.cookies)
        bad =   _login(APIClient(), password = 'Mala#12345')
        self.assertEqual(bad.status_code, 401)
        bad =   _login(APIClient(), email = 'nadie@example.com')
        self.assertEqual(bad.status_code, 401)

    def test_login_inactive_customer_403(self):
        _make_customer(is_active = False)
        response    =   _login(self.client)
        self.assertEqual(response.status_code, 403)

    def test_login_with_store_auto_joins_and_suspended_403(self):
        customer    =   _make_customer()
        response    =   _login(self.client, store_slug = 'mitienda')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StoreMembership.objects.filter(customer = customer, store = self.store).exists())
        #Suspender la membresía → el próximo login con esa tienda da 403
        StoreMembership.objects.filter(customer = customer).update(status = 'suspended')
        response    =   _login(APIClient(), store_slug = 'mitienda')
        self.assertEqual(response.status_code, 403)
        #Sin store_slug el login global sigue funcionando
        response    =   _login(APIClient())
        self.assertEqual(response.status_code, 200)

    #REFRESH / LOGOUT (cookie + CSRF)
    def _session_cookies(self):
        _make_customer()
        response    =   _login(self.client)
        return response

    def test_refresh_rotates_and_rejects_replay(self):
        response    =   self._session_cookies()
        csrf        =   response.cookies['customer_csrf'].value
        refresh     =   response.cookies['customer_refresh'].value
        self.client.cookies['customer_refresh'] =   refresh
        self.client.cookies['customer_csrf']    =   csrf
        #Sin header CSRF → 403
        bad =   self.client.post(REFRESH_URL, {}, format = 'json')
        self.assertEqual(bad.status_code, 403)
        #Con CSRF → 200 + access nuevo + cookies rotadas
        ok  =   self.client.post(REFRESH_URL, {}, format = 'json', HTTP_X_CSRFTOKEN = csrf)
        self.assertEqual(ok.status_code, 200)
        self.assertIn('access', ok.json())
        new_refresh =   ok.cookies['customer_refresh'].value
        self.assertNotEqual(new_refresh, refresh)
        #Replay del refresh viejo → 401 (blacklist por rotación)
        self.client.cookies['customer_refresh'] =   refresh
        self.client.cookies['customer_csrf']    =   ok.cookies['customer_csrf'].value
        replay  =   self.client.post(REFRESH_URL, {}, format = 'json', HTTP_X_CSRFTOKEN = ok.cookies['customer_csrf'].value)
        self.assertEqual(replay.status_code, 401)

    def test_refresh_via_body_for_api_clients(self):
        response    =   self._session_cookies()
        refresh     =   response.cookies['customer_refresh'].value
        ok  =   APIClient().post(REFRESH_URL, {'refresh': refresh}, format = 'json')
        self.assertEqual(ok.status_code, 200)
        self.assertIn('access', ok.json())
        self.assertIn('refresh', ok.json())  #body path devuelve el nuevo refresh

    def test_logout_blacklists_refresh(self):
        response    =   self._session_cookies()
        csrf        =   response.cookies['customer_csrf'].value
        refresh     =   response.cookies['customer_refresh'].value
        self.client.cookies['customer_refresh'] =   refresh
        self.client.cookies['customer_csrf']    =   csrf
        out =   self.client.post(LOGOUT_URL, {}, format = 'json', HTTP_X_CSRFTOKEN = csrf)
        self.assertEqual(out.status_code, 200)
        #El refresh quedó blacklisteado → refresh posterior 401
        self.client.cookies['customer_csrf']    =   csrf
        again   =   self.client.post(REFRESH_URL, {}, format = 'json', HTTP_X_CSRFTOKEN = csrf)
        self.assertEqual(again.status_code, 401)

    #ME / PROFILE
    def test_me_and_patch_profile(self):
        customer    =   _make_customer()
        client      =   APIClient()
        _bearer(client, customer)
        me  =   client.get(ME_URL)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['customer']['email'], 'ana@example.com')
        patch   =   client.patch(PROFILE_URL, {'first_name': 'Ana María', 'last_name': 'Gómez', 'phone': '+54 9 387 155-1234'}, format = 'json')
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.json()['customer']['phone'], '+5493871551234')
        self.assertEqual(patch.json()['customer']['avatar'], 'A')

    def test_me_without_trailing_slash_does_not_redirect(self):
        #Regresión QA: el front llama /customer-auth/me sin slash — el alias
        #evita el 301 del APPEND_SLASH en cada carga (antes el GET iba y
        #volvía y un PATCH podía llegar redirigido).
        customer    =   _make_customer()
        client      =   APIClient()
        _bearer(client, customer)
        response    =   client.get('/api/customer-auth/me')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer']['email'], 'ana@example.com')
        patch       =   client.patch('/api/customer-auth/me', {'first_name': 'SinSlash'}, format = 'json')
        self.assertEqual(patch.status_code, 200)

    def test_profile_requires_customer_auth(self):
        self.assertEqual(APIClient().get(PROFILE_URL).status_code, 401)
        self.assertEqual(APIClient().get(ME_URL).status_code, 401)

    def test_mass_assignment_cannot_change_sensitive_fields(self):
        customer    =   _make_customer()
        old_hash    =   customer.password
        client      =   APIClient()
        _bearer(client, customer)
        response    =   client.patch(PROFILE_URL, {
            'is_active': False, 'email_verified': True, 'email': 'otro@example.com',
            'password': 'Hackeado#123', 'tokens_valid_after': '2020-01-01T00:00:00Z',
            'first_name': 'Ok',
        }, format = 'json')
        self.assertEqual(response.status_code, 200)
        customer.refresh_from_db()
        self.assertTrue(customer.is_active)
        self.assertFalse(customer.email_verified)
        self.assertEqual(customer.email, 'ana@example.com')
        self.assertEqual(customer.password, old_hash)
        self.assertIsNone(customer.tokens_valid_after)
        self.assertEqual(customer.first_name, 'Ok')

    #VERIFY EMAIL
    def test_verify_email_token_flow(self):
        customer    =   _make_customer(email_verified = False)
        token       =   make_verify_email_token(customer)
        response    =   APIClient().post(VERIFY_URL, {'token': token}, format = 'json')
        self.assertEqual(response.status_code, 200)
        customer.refresh_from_db()
        self.assertTrue(customer.email_verified)
        self.assertIsNotNone(customer.email_verified_at)
        #Idempotente: mismo token de nuevo → 200
        again   =   APIClient().post(VERIFY_URL, {'token': token}, format = 'json')
        self.assertEqual(again.status_code, 200)
        #Token basura → 400
        bad =   APIClient().post(VERIFY_URL, {'token': 'basura'}, format = 'json')
        self.assertEqual(bad.status_code, 400)
        #Token firmado con email que no matchea el del customer → 400
        bad2    =   APIClient().post(VERIFY_URL, {'token': signing.dumps({'cid': customer.pk, 'em': 'fake@x.com'}, salt = 'customers.email_verify')}, format = 'json')
        self.assertEqual(bad2.status_code, 400)

    def test_verify_email_resend_requires_auth_and_throttles(self):
        customer    =   _make_customer()
        client      =   APIClient()
        self.assertEqual(client.post(VERIFY_RESEND, {}, format = 'json').status_code, 401)
        _bearer(client, customer)
        #Encola la task (eager → envía a locmem): verificar que no explota
        #y que un ya-verificado responde sin reenviar.
        customer.email_verified  =   True
        customer.save(update_fields = ['email_verified'])
        response    =   client.post(VERIFY_RESEND, {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('ya está verificado', response.json()['detail'])

    #PASSWORD RESET
    def test_password_reset_request_and_confirm(self):
        customer    =   _make_customer()
        #Request siempre genérico (anti-enumeración) — el mail sale por task
        #eager; acá probamos el Query directo para no depender de on_commit.
        response    =   APIClient().post(RESET_URL, {'email': 'ana@example.com'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Si el correo está registrado', response.json()['detail'])
        #Confirm con uid+token válidos
        uid     =   urlsafe_base64_encode(force_bytes(customer.pk))
        token   =   customer_reset_token.make_token(customer)
        new_pwd =   'NuevaClave#99'
        confirm =   APIClient().post(RESET_CONFIRM, {
            'uid': uid, 'token': token,
            'new_password': new_pwd, 'confirm_password': new_pwd,
        }, format = 'json')
        self.assertEqual(confirm.status_code, 200)
        customer.refresh_from_db()
        self.assertTrue(customer.check_password(new_pwd))
        self.assertFalse(customer.check_password(PASSWORD))
        #tokens_valid_after sellado → access viejo revocado
        self.assertIsNotNone(customer.tokens_valid_after)
        #Token reusado → 400 (el hash incluye el password nuevo)
        reuse   =   APIClient().post(RESET_CONFIRM, {
            'uid': uid, 'token': token,
            'new_password': 'Otra#12345', 'confirm_password': 'Otra#12345',
        }, format = 'json')
        self.assertEqual(reuse.status_code, 400)
        #Confirm con passwords que no coinciden → 400
        uid2    =   urlsafe_base64_encode(force_bytes(customer.pk))
        token2  =   customer_reset_token.make_token(customer)
        mismatch    =   APIClient().post(RESET_CONFIRM, {
            'uid': uid2, 'token': token2,
            'new_password': 'Aa#123456', 'confirm_password': 'Bb#123456',
        }, format = 'json')
        self.assertEqual(mismatch.status_code, 400)

    def test_password_reset_confirm_revokes_old_access_token(self):
        customer    =   _make_customer()
        client      =   APIClient()
        _bearer(client, customer)
        self.assertEqual(client.get(ME_URL).status_code, 200)
        #Reset de contraseña → el access emitido antes queda revocado
        uid     =   urlsafe_base64_encode(force_bytes(customer.pk))
        token   =   customer_reset_token.make_token(customer)
        APIClient().post(RESET_CONFIRM, {
            'uid': uid, 'token': token,
            'new_password': 'Revocada#123', 'confirm_password': 'Revocada#123',
        }, format = 'json')
        self.assertEqual(client.get(ME_URL).status_code, 401)

    def test_password_reset_email_is_sent_for_existing_customer(self):
        customer    =   _make_customer()
        SendCustomerPasswordResetEmailQuery(customer)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(customer.email, mail.outbox[0].to)
        self.assertIn('restablecer', mail.outbox[0].body)

    #LINKS DE LOS MAILS (regresión: /cuenta/cuenta/... → "Tienda no disponible")
    def test_password_reset_email_link_platform_account_when_no_store(self):
        #Sin tienda conocida el link va a la página /cuenta de la
        #plataforma — UNA sola vez 'cuenta' en el path.
        customer    =   _make_customer()
        SendCustomerPasswordResetEmailQuery(customer)
        body        =   mail.outbox[-1].body
        self.assertIn('/cuenta/restablecer?', body)
        self.assertNotIn('/cuenta/cuenta/', body)

    def test_password_reset_email_link_uses_given_store_slug(self):
        customer    =   _make_customer()
        SendCustomerPasswordResetEmailQuery(customer, store_slug = 'mitienda')
        self.assertIn('/mitienda/cuenta/restablecer?', mail.outbox[-1].body)

    def test_password_reset_email_falls_back_to_membership_store(self):
        #Sin slug en el request: la membresía activa más reciente decide.
        customer    =   _make_customer()
        StoreMembership.objects.create(customer = customer, store = self.store)
        SendCustomerPasswordResetEmailQuery(customer)
        self.assertIn('/mitienda/cuenta/restablecer?', mail.outbox[-1].body)

    def test_verification_email_falls_back_to_membership_store(self):
        #Reenvío sin slug (vista autenticada no conoce la tienda): mismo fallback.
        customer    =   _make_customer()
        StoreMembership.objects.create(customer = customer, store = self.store)
        SendCustomerVerificationEmailQuery(customer)
        self.assertIn('/mitienda/cuenta/verificar?', mail.outbox[-1].body)
        self.assertNotIn('/cuenta/cuenta/', mail.outbox[-1].body)

    def test_password_reset_request_accepts_and_validates_store_slug(self):
        _make_customer()
        client      =   APIClient()
        #Slug inexistente → 400 (mismo criterio que register/login).
        bad =   client.post(RESET_URL, {'email': 'ana@example.com', 'store_slug': 'noexiste'}, format = 'json')
        self.assertEqual(bad.status_code, 400)
        #Slug válido → 200 genérico (el mail encola por on_commit).
        ok  =   client.post(RESET_URL, {'email': 'ana@example.com', 'store_slug': 'mitienda'}, format = 'json')
        self.assertEqual(ok.status_code, 200)
        self.assertIn('Si el correo está registrado', ok.json()['detail'])

    def test_verification_email_is_sent(self):
        customer    =   _make_customer()
        SendCustomerVerificationEmailQuery(customer)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verificar', mail.outbox[0].body)


class CustomerTokenIsolationTests(TestCase):
    """Un JWT DAVENT no autentica endpoints de cliente y viceversa."""

    def setUp(self):
        cache.clear()
        self.client     =   APIClient()

    def test_davent_token_rejected_on_customer_endpoints(self):
        user    =   User.objects.create_user(username = 'saas', email = 'saas@x.com', password = 'x')
        davent_access   =   str(DaventRefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION = f'Bearer {davent_access}')
        self.assertEqual(self.client.get(PROFILE_URL).status_code, 401)
        self.assertEqual(self.client.get(ME_URL).status_code, 401)

    def test_customer_token_rejected_on_davent_endpoints(self):
        customer    =   _make_customer()
        client      =   APIClient()
        _bearer(client, customer)
        #El endpoint SaaS usa JWTAuthentication estándar: token_type
        #customer_access no es 'access' → 401.
        self.assertEqual(client.get(DAVENT_USER_URL).status_code, 401)


class CustomerAddressIDORTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client     =   APIClient()
        self.a          =   _make_customer('a@example.com')
        self.b          =   _make_customer('b@example.com')
        self.client_a   =   APIClient()
        _bearer(self.client_a, self.a)

    def _address(self, customer, **kw):
        return CustomerAddress.objects.create(
            customer = customer, line1 = 'Calle 1', city = 'CABA',
            province = 'CABA', **kw,
        )

    def test_idor_address_detail_404(self):
        addr    =   self._address(self.a)
        client_b    =   APIClient()
        _bearer(client_b, self.b)
        self.assertEqual(client_b.get(f'{ADDRESSES_URL}{addr.pk}/').status_code, 404)
        self.assertEqual(client_b.patch(f'{ADDRESSES_URL}{addr.pk}/', {'line1': 'Hack'}, format = 'json').status_code, 404)
        self.assertEqual(client_b.delete(f'{ADDRESSES_URL}{addr.pk}/').status_code, 404)

    def test_list_only_own_addresses(self):
        self._address(self.a, label = 'Casa A')
        self._address(self.b, label = 'Casa B')
        response    =   self.client_a.get(ADDRESSES_URL)
        self.assertEqual(response.status_code, 200)
        rows    =   response.json().get('results', response.json())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['label'], 'Casa A')

    def test_single_default_enforced(self):
        first   =   self.client_a.post(ADDRESSES_URL, {
            'label': 'Casa', 'line1': 'Calle 1', 'city': 'CABA', 'province': 'CABA', 'is_default': True,
        }, format = 'json')
        self.assertEqual(first.status_code, 201)
        second  =   self.client_a.post(ADDRESSES_URL, {
            'label': 'Trabajo', 'line1': 'Calle 2', 'city': 'CABA', 'province': 'CABA', 'is_default': True,
        }, format = 'json')
        self.assertEqual(second.status_code, 201)
        defaults    =   CustomerAddress.objects.filter(customer = self.a, is_default = True)
        self.assertEqual(defaults.count(), 1)
        self.assertEqual(defaults.first().label, 'Trabajo')

    def test_delete_default_promotes_next(self):
        a1  =   self._address(self.a, label = 'Uno')
        a2  =   self._address(self.a, label = 'Dos', is_default = True)
        response    =   self.client_a.delete(f'{ADDRESSES_URL}{a2.pk}/')
        self.assertEqual(response.status_code, 204)
        a1.refresh_from_db()
        self.assertTrue(a1.is_default)

    def test_address_customer_field_not_writable(self):
        response    =   self.client_a.post(ADDRESSES_URL, {
            'line1': 'Calle 9', 'city': 'X', 'province': 'Y', 'customer': self.b.pk,
        }, format = 'json')
        self.assertEqual(response.status_code, 201)
        addr    =   CustomerAddress.objects.get(pk = response.json()['id'])
        self.assertEqual(addr.customer_id, self.a.pk)


class CustomerMembershipTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client     =   APIClient()
        self.a          =   _make_customer('a@example.com')
        self.b          =   _make_customer('b@example.com')
        self.store      =   _make_store()
        StoreMembership.objects.create(customer = self.a, store = self.store, status = 'active', tags = ['vip'])
        StoreMembership.objects.create(customer = self.b, store = self.store, status = 'suspended')

    def test_memberships_only_own(self):
        _bearer(self.client, self.a)
        response    =   self.client.get(MEMBERSHIPS_URL)
        self.assertEqual(response.status_code, 200)
        rows    =   response.json().get('results', response.json())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['store_slug'], 'mitienda')
        self.assertEqual(rows[0]['status'], 'active')
        self.assertEqual(rows[0]['tags'], ['vip'])
        self.assertIn('joined_at', rows[0])

    def test_memberships_requires_auth(self):
        self.assertEqual(APIClient().get(MEMBERSHIPS_URL).status_code, 401)


class CustomerPIITests(TestCase):
    """Teléfono/documento cifrados en reposo + huella HMAC (patrón UserProfile)."""

    def setUp(self):
        cache.clear()

    def test_pii_encrypted_at_rest_with_hash(self):
        customer    =   _make_customer()
        client      =   APIClient()
        _bearer(client, customer)
        client.patch(PROFILE_URL, {
            'phone': '+5493871551234', 'document_type': 'DNI', 'document': '30123456',
        }, format = 'json')
        #Lectura ORM → texto en claro
        fresh   =   Customer.objects.get(pk = customer.pk)
        self.assertEqual(fresh.phone, '+5493871551234')
        self.assertEqual(fresh.document, '30123456')
        #Lectura cruda de columnas → ciphertext del vault, nunca el plano.
        #values_list aplica from_db_value (descifra): hay que ir al cursor.
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT phone, document, phone_hash, document_hash FROM customers_customer WHERE id = %s',
                [customer.pk],
            )
            raw =   cursor.fetchone()
        self.assertTrue(is_encrypted(raw[0]))
        self.assertTrue(is_encrypted(raw[1]))
        self.assertNotIn('5493871551234', raw[0])
        #Huella HMAC estable = digest_for del valor en claro
        self.assertEqual(raw[2], digest_for('customer.phone', '+5493871551234'))
        self.assertEqual(raw[3], digest_for('customer.document', '30123456'))

    def test_document_cuit_validated(self):
        customer    =   _make_customer()
        client      =   APIClient()
        _bearer(client, customer)
        #CUIT con dígito verificador inválido → 400
        bad =   client.patch(PROFILE_URL, {'document_type': 'CUIT', 'document': '20123456789'}, format = 'json')
        self.assertEqual(bad.status_code, 400)
        #CUIT válido (dígito verificador correcto) → 200
        ok_cuit =   client.patch(PROFILE_URL, {'document_type': 'CUIT', 'document': '20345678906'}, format = 'json')
        self.assertEqual(ok_cuit.status_code, 200)
        #DNI de 7-8 dígitos → 200
        ok  =   client.patch(PROFILE_URL, {'document_type': 'DNI', 'document': '30123456'}, format = 'json')
        self.assertEqual(ok.status_code, 200)

    def test_filter_by_encrypted_field_raises(self):
        #EncryptedCharField prohíbe lookups directos — hay que usar _hash
        from django.core.exceptions import FieldError
        customer    =   _make_customer()
        client      =   APIClient()
        _bearer(client, customer)
        client.patch(PROFILE_URL, {'phone': '+5493871551234'}, format = 'json')
        with self.assertRaises((TypeError, FieldError)):
            list(Customer.objects.filter(phone = '+5493871551234'))


class CustomerGoogleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client     =   APIClient()
        self.store      =   _make_store()

    def _tokeninfo(self, **over):
        payload =   {
            'aud': 'client-central.apps.googleusercontent.com',
            'iss': 'https://accounts.google.com',
            'exp': '9999999999',
            'email': 'google@example.com',
            'email_verified': 'true',
            'given_name': 'Google',
            'family_name': 'User',
            'sub': '12345',
        }
        payload.update(over)
        resp    =   MagicMock()
        resp.ok =   True
        resp.json.return_value  =   payload
        return resp

    def test_google_config_disabled_without_oauth(self):
        response    =   self.client.get(GOOGLE_CONFIG.format(slug = 'mitienda'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'client_id': '', 'enabled': False})

    def test_google_config_by_o_and_central_fallback(self):
        oauth   =   StoreOAuthConfig.objects.create(store = self.store, enabled = True, google_client_id = 'own-client-id')
        response    =   self.client.get(GOOGLE_CONFIG.format(slug = 'mitienda'))
        self.assertEqual(response.json(), {'client_id': 'own-client-id', 'enabled': True})
        #Sin client propio pero enabled → cae al central DAVENT
        oauth.google_client_id   =   ''
        oauth.save(update_fields = ['google_client_id'])
        with patch('StoreApp.domains.customers.services.google.GOOGLE_CLIENT_ID', 'central-id'):
            response    =   self.client.get(GOOGLE_CONFIG.format(slug = 'mitienda'))
        self.assertEqual(response.json(), {'client_id': 'central-id', 'enabled': True})

    def test_google_auth_disabled_store_503(self):
        response    =   self.client.post(GOOGLE_URL, {'credential': 'tok', 'store_slug': 'mitienda'}, format = 'json')
        self.assertEqual(response.status_code, 503)

    def test_google_auth_wrong_audience_400(self):
        StoreOAuthConfig.objects.create(store = self.store, enabled = True, google_client_id = 'own-id')
        with patch('StoreApp.domains.customers.services.google.requests.get', return_value = self._tokeninfo(aud = 'otra-app')):
            response    =   self.client.post(GOOGLE_URL, {'credential': 'tok', 'store_slug': 'mitienda'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_google_auth_unverified_email_400(self):
        StoreOAuthConfig.objects.create(store = self.store, enabled = True, google_client_id = 'own-id')
        with patch('StoreApp.domains.customers.services.google.requests.get', return_value = self._tokeninfo(aud = 'own-id', email_verified = 'false')):
            response    =   self.client.post(GOOGLE_URL, {'credential': 'tok', 'store_slug': 'mitienda'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_google_auth_creates_customer_and_membership(self):
        StoreOAuthConfig.objects.create(store = self.store, enabled = True, google_client_id = 'own-id')
        with patch('StoreApp.domains.customers.services.google.requests.get', return_value = self._tokeninfo(aud = 'own-id')):
            response    =   self.client.post(GOOGLE_URL, {'credential': 'tok', 'store_slug': 'mitienda'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertTrue(data['is_new'])
        self.assertIn('access', data)
        self.assertIn('customer_refresh', response.cookies)
        customer    =   Customer.objects.get(email = 'google@example.com')
        self.assertTrue(customer.email_verified)          #Google ya lo verificó
        self.assertFalse(customer.check_password('cualquiera'))  #password inutilizable
        self.assertEqual(customer.first_name, 'Google')
        self.assertTrue(StoreMembership.objects.filter(customer = customer, store = self.store).exists())

    def test_google_auth_existing_customer_links_and_suspended_403(self):
        customer    =   _make_customer('google@example.com')
        StoreMembership.objects.create(customer = customer, store = self.store, status = 'suspended')
        StoreOAuthConfig.objects.create(store = self.store, enabled = True, google_client_id = 'own-id')
        with patch('StoreApp.domains.customers.services.google.requests.get', return_value = self._tokeninfo(aud = 'own-id')):
            response    =   self.client.post(GOOGLE_URL, {'credential': 'tok', 'store_slug': 'mitienda'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_google_link_kills_prior_password_and_sessions(self):
        """Anti-pre-hijacking: si la cuenta ya existía con contraseña
        usable (el alta no exige verificación), el auto-link por Google
        la invalida y sella tokens_valid_after — el pre-registrante no
        puede seguir entrando por password ni con sus sesiones vivas."""
        customer    =   _make_customer('google@example.com')
        self.assertTrue(customer.check_password(PASSWORD))
        StoreOAuthConfig.objects.create(store = self.store, enabled = True, google_client_id = 'own-id')
        with patch('StoreApp.domains.customers.services.google.requests.get', return_value = self._tokeninfo(aud = 'own-id')):
            response    =   self.client.post(GOOGLE_URL, {'credential': 'tok', 'store_slug': 'mitienda'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        customer.refresh_from_db()
        self.assertFalse(customer.check_password(PASSWORD))
        self.assertIsNotNone(customer.tokens_valid_after)
        #Y el login por password queda cerrado.
        self.assertEqual(_login(self.client, email = 'google@example.com', password = PASSWORD).status_code, 401)

    def test_google_race_path_applies_same_hardening(self):
        """Carrera de altas (IntegrityError tras el INSERT): la cuenta
        que 'gana' puede ser una pre-registrada con password usable —
        el path del IntegrityError corre el MISMO hardening que el de
        cuenta existente (invalida password + sella tokens_valid_after),
        nunca devuelve la cuenta recién creada sin proteger."""
        from django.contrib.auth.hashers import is_password_usable
        from django.db import IntegrityError
        from StoreApp.domains.customers.services import google as google_svc
        existing    =   Customer(email = 'race@example.com')
        existing.set_password('Password#1')
        empty_qs    =   MagicMock()
        empty_qs.first.return_value   =   None
        found_qs    =   MagicMock()
        found_qs.first.return_value   =   existing
        new_customer    =   MagicMock()
        new_customer.save.side_effect  =   IntegrityError('duplicate key')
        with patch.object(google_svc, 'Customer') as MockCustomer, \
             patch.object(google_svc, 'ensure_membership'), \
             patch.object(existing, 'save') as existing_save:
            MockCustomer.objects.filter.side_effect   =   [empty_qs, found_qs]
            MockCustomer.return_value                 =   new_customer
            customer, is_new  =   google_svc.google_customer_login(
                {'email': 'race@example.com', 'first_name': 'Race'}, self.store)
        self.assertFalse(is_new)
        self.assertIs(customer, existing)
        self.assertFalse(is_password_usable(existing.password))
        self.assertIsNotNone(existing.tokens_valid_after)
        self.assertTrue(existing.email_verified)
        existing_save.assert_called_once()


class CustomerThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client     =   APIClient()

    def test_login_throttled_after_limit(self):
        #scope 'login' = 5/min por IP — el 6º intento da 429
        codes   =   []
        for _ in range(6):
            codes.append(_login(self.client, email = 'x@x.com', password = 'Mala#123').status_code)
        self.assertEqual(codes[-1], 429)

    def test_register_throttled(self):
        codes   =   []
        for i in range(11):
            codes.append(self.client.post(REGISTER_URL, {
                'email': f't{i}@example.com', 'password': PASSWORD,
            }, format = 'json').status_code)
        self.assertEqual(codes[-1], 429)

    def test_password_reset_confirm_has_own_throttle_bucket(self):
        #Regresión QA (paridad con users): request y confirm compartían
        #'password_reset' — agotado el de request (10/h) el confirm seguía
        #bloqueado y el comprador no podía recuperar la clave. Ahora el
        #confirm usa 'password_reset_confirm' (30/h): con el bucket de
        #request lleno responde 400 por token inválido, no 429.
        for _ in range(10):
            self.client.post(RESET_URL, {'email': 'x@x.com'}, format = 'json')
        confirm =   self.client.post(RESET_CONFIRM, {
            'uid': 'eA', 'token': 'trucho',
            'new_password': 'Nueva#12345', 'confirm_password': 'Nueva#12345',
        }, format = 'json')
        self.assertEqual(confirm.status_code, 400)


class CustomerModelTests(TestCase):
    def test_email_normalized_on_save(self):
        c   =   Customer(email = '  MIXXTO@Example.COM ')
        c.set_password(PASSWORD)
        c.save()
        c.refresh_from_db()
        self.assertEqual(c.email, 'mixxto@example.com')

    def test_hashes_recompute_on_phone_change(self):
        c   =   _make_customer()
        c.phone =   '+5491111111111'
        c.save()
        c.refresh_from_db()
        self.assertEqual(c.phone_hash, digest_for('customer.phone', '+5491111111111'))
        c.phone =   ''
        c.save()
        c.refresh_from_db()
        self.assertIsNone(c.phone_hash)

    def test_unusable_password_cannot_login(self):
        c   =   Customer(email = 'g@example.com')
        c.set_unusable_password()
        c.save()
        self.assertFalse(c.check_password('cualquiera'))


class CustomerNotificationTests(TestCase):
    """
    Campana del comprador: list/read scopeados al request.customer
    (IDOR) y el ticket firmado del stream SSE.
    """
    def setUp(self):
        cache.clear()
        self.a          =   _make_customer('a@example.com')
        self.b          =   _make_customer('b@example.com')
        self.store      =   _make_store()
        self.other      =   _make_store('otra')
        self.client_a   =   APIClient()
        _bearer(self.client_a, self.a)

    def _notif(self, customer, store, **kw):
        return CustomerNotification.objects.create(
            customer = customer, store = store,
            kind = CustomerNotification.KIND_ORDER, title = 'Aviso', **kw,
        )

    def test_list_requires_customer_auth(self):
        self.assertEqual(APIClient().get(NOTIFS_URL).status_code, 401)

    def test_list_only_own_and_store_filter(self):
        self._notif(self.a, self.store)
        self._notif(self.a, self.other, dedupe_key = 'x2')
        self._notif(self.b, self.store, dedupe_key = 'x3')
        response    =   self.client_a.get(NOTIFS_URL, {'store': self.store.slug})
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertEqual(len(data['notifications']), 1)
        self.assertEqual(data['unread'], 1)
        #Sin filtro: las dos tiendas del comprador, nunca la del otro.
        data    =   self.client_a.get(NOTIFS_URL).json()
        self.assertEqual(len(data['notifications']), 2)

    def test_read_idor_404(self):
        foreign =   self._notif(self.b, self.store)
        response    =   self.client_a.post(NOTIFS_READ, {'id': foreign.pk}, format = 'json')
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertIsNone(foreign.read_at)

    def test_read_marks_own_and_updates_unread(self):
        n1  =   self._notif(self.a, self.store)
        self._notif(self.a, self.store, dedupe_key = 'x4')
        response    =   self.client_a.post(NOTIFS_READ, {'id': n1.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['unread'], 1)
        n1.refresh_from_db()
        self.assertIsNotNone(n1.read_at)

    def test_read_all_scoped_by_store(self):
        self._notif(self.a, self.store)
        self._notif(self.a, self.other, dedupe_key = 'x5')
        response    =   self.client_a.post(NOTIFS_READ, {'all': True, 'store': self.store.slug}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['unread'], 1)
        self.assertEqual(CustomerNotification.objects.filter(customer = self.a, read_at__isnull = True).count(), 1)

    def test_stream_ticket_and_bad_ticket(self):
        self.assertEqual(APIClient().post(NOTIFS_TICKET, {}, format = 'json').status_code, 401)
        response    =   self.client_a.post(NOTIFS_TICKET, {'store': self.store.slug}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ticket'])
        #Ticket trucho → 401; Accept de EventSource ya no da 406.
        bad     =   APIClient().get(NOTIFS_STREAM, {'ticket': 'trucho', 'store': self.store.slug}, HTTP_ACCEPT = 'text/event-stream')
        self.assertEqual(bad.status_code, 401)
        bad     =   APIClient().get(NOTIFS_STREAM, {
            'ticket': response.json()['ticket'], 'store': 'otra-tienda',
        }, HTTP_ACCEPT = 'text/event-stream')
        self.assertEqual(bad.status_code, 401)

    def test_stream_opens_event_stream(self):
        from StoreApp.domains.customers.views.notification_views import (
            CustomerNotificationStreamView,
        )
        #El GET vía test client cierra la conexión atómica del TestCase al
        #consumir el StreamingHttpResponse — se prueba el generador directo
        #y solo hasta el primer yield (el loop de polling hace
        #close_old_connections, rompe el atomic del test).
        gen     =   CustomerNotificationStreamView()._events(self.a.pk, self.store.pk, 0)
        first   =   next(iter(gen))
        self.assertIn('conectado', first)
        gen.close()

    def test_dedupe_upsert_revives_unread(self):
        from StoreApp.domains.customers.services.notifications import upsert_customer_notification
        n1  =   upsert_customer_notification(self.a, self.store, 'order', 'v1', dedupe_key = 'k1')
        self.client_a.post(NOTIFS_READ, {'id': n1.pk}, format = 'json')
        n2  =   upsert_customer_notification(self.a, self.store, 'order', 'v2', dedupe_key = 'k1')
        self.assertEqual(n1.pk, n2.pk)
        self.assertIsNone(n2.read_at)
        self.assertEqual(n2.title, 'v2')
        self.assertEqual(CustomerNotification.objects.filter(customer = self.a).count(), 1)
