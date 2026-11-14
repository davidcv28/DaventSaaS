"""
Tests del dominio pos (PLAN_POS).

Cubre: código de vinculación del dueño (auth, beneficio has_pos_app,
rotación), canje del código (happy path, vencido, usado, inválido,
throttle por código), licencia Ed25519 (claims, active/denied, device
revocado, token inválido, last_seen_at) y catálogo filtrado por
tier + rubro de la tienda.
"""
import base64
from datetime import timedelta
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.design.models import DesignCategory, DesignPattern, DesignStyle
from StoreApp.domains.pos.models import PosApp, PosDevice, PosPairingCode
from StoreApp.domains.pos.services import PAIR_CODE_ALPHABET
from StoreApp.domains.stores.models import Store, StoreCustomization
from SuscriptionApp.domains.benefits.models import (
    Benefit,
    PlanBenefit,
    PlanPresentation,
)

PAIR_CODE_URL   =   '/api/pos/pair-code/'
PAIR_URL        =   '/api/pos/pair/'
LICENSE_URL     =   '/api/pos/license/'
APPS_URL        =   '/api/pos/apps/'

#Clave Ed25519 efímera de la suite: la licencia se firma con la privada
#(vía override_settings) y se verifica con esta pública.
_TEST_PRIVATE_KEY   =   Ed25519PrivateKey.generate()
_TEST_PUBLIC_KEY    =   _TEST_PRIVATE_KEY.public_key()
_TEST_KEY_B64       =   base64.b64encode(
    _TEST_PRIVATE_KEY.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
).decode()


def _grant(profile, *codes, plan_name = 'Plan ecommerce', plan_slug = 'ecommerce'):
    """Plan + presentación + suscripción vigente con los flags pedidos."""
    plan        =   SuscriptionPlan.objects.filter(name = plan_name).first()
    if plan is None:
        plan    =   SuscriptionPlan.objects.create(name = plan_name)
    PlanPresentation.objects.update_or_create(plan = plan, defaults = {'slug': plan_slug})
    for code in codes:
        benefit =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': Benefit.FLAG})[0]
        PlanBenefit.objects.update_or_create(plan = plan, benefit = benefit, defaults = {'enabled': True, 'value': None})
    suscription =   getattr(profile, 'suscription', None)
    if suscription is None:
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )
    else:
        suscription.plan_suscription    =   plan
        suscription.status              =   Suscription.STATUS_ACTIVE
        suscription.end_date            =   timezone.now() + timedelta(days = 30)
        suscription.save()
    #plan_benefits_of cachea por PK — el set nuevo tiene que verse ya.
    cache.delete(f'planben:{profile.pk}')


def _make_owner(username = 'duenio', slug = 'mi-tienda', codes = ('has_pos_app',), **kwargs):
    """Usuario + perfil + tienda + customization (con has_pos_app salvo codes vacío)."""
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(user = user, email_verified = True)
    if codes:
        _grant(profile, *codes, plan_name = kwargs.pop('plan_name', 'Plan ecommerce'), plan_slug = kwargs.pop('plan_slug', 'ecommerce'))
    cache.delete(f'planben:{profile.pk}')
    store       =   Store.objects.create(user = profile, slug = slug)
    StoreCustomization.objects.create(store = store)
    return user, profile, store


def _authed(user):
    client  =   APIClient()
    client.force_authenticate(user = user)
    return client


def _pair(device_name = 'Caja 1'):
    """Genera un código y lo canjea: devuelve (device, device_token)."""
    user, _, store  =   _make_owner()
    response        =   _authed(user).post(PAIR_CODE_URL)
    code            =   response.json()['code']
    response        =   APIClient().post(PAIR_URL, {'code': code, 'device_name': device_name}, format = 'json')
    token           =   response.json()['device_token']
    return PosDevice.objects.get(store = store), token


def _decode_license(token):
    """Verifica firma EdDSA + claims — lo mismo que hace la app offline."""
    return jwt.decode(token, _TEST_PUBLIC_KEY, algorithms = ['EdDSA'])


@override_settings(POS_LICENSE_PRIVATE_KEY_B64 = _TEST_KEY_B64)
class PosPairCodeTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_requires_auth(self):
        self.assertIn(APIClient().post(PAIR_CODE_URL).status_code, (401, 403))

    def test_owner_without_store_gets_404(self):
        user    =   User.objects.create_user(username = 'sinweb', email = 'sinweb@gmail.com', password = 'Xq7#mP2vL9bT')
        UserProfile.objects.create(user = user, email_verified = True)
        self.assertEqual(_authed(user).post(PAIR_CODE_URL).status_code, 404)

    def test_without_benefit_gets_403(self):
        user, _, _  =   _make_owner(codes = ())
        self.assertEqual(_authed(user).post(PAIR_CODE_URL).status_code, 403)

    def test_creates_code(self):
        user, _, store  =   _make_owner()
        response        =   _authed(user).post(PAIR_CODE_URL)
        self.assertEqual(response.status_code, 201)
        data            =   response.json()
        code            =   data['code']
        self.assertEqual(len(code), 8)
        self.assertTrue(all(char in PAIR_CODE_ALPHABET for char in code))
        row             =   PosPairingCode.objects.get(store = store, code = code)
        self.assertIsNone(row.used_at)
        self.assertEqual(row.created_by, user)
        ttl             =   row.expires_at - timezone.now()
        self.assertTrue(timedelta(minutes = 9) < ttl <= timedelta(minutes = 10))

    def test_regenerating_revokes_previous_code(self):
        user, _, store  =   _make_owner()
        client          =   _authed(user)
        first           =   client.post(PAIR_CODE_URL).json()['code']
        second          =   client.post(PAIR_CODE_URL).json()['code']
        self.assertNotEqual(first, second)
        self.assertIsNotNone(PosPairingCode.objects.get(code = first).used_at)
        self.assertIsNone(PosPairingCode.objects.get(code = second).used_at)
        #El código anulado ya no se puede canjear.
        response        =   APIClient().post(PAIR_URL, {'code': first, 'device_name': 'Caja'}, format = 'json')
        self.assertEqual(response.status_code, 400)


@override_settings(POS_LICENSE_PRIVATE_KEY_B64 = _TEST_KEY_B64)
class PosPairTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user, _, self.store    =   _make_owner()
        self.code                   =   _authed(self.user).post(PAIR_CODE_URL).json()['code']

    def test_happy_path(self):
        response    =   APIClient().post(PAIR_URL, {'code': self.code, 'device_name': 'Caja 1'}, format = 'json')
        self.assertEqual(response.status_code, 201)
        token       =   response.json()['device_token']
        payload     =   jwt.decode(token, settings.POS_DEVICE_TOKEN_KEY, algorithms = ['HS256'])
        device      =   PosDevice.objects.get(store = self.store)
        self.assertEqual(payload['typ'], 'pos_device')
        self.assertEqual(payload['store_id'], self.store.pk)
        self.assertEqual(payload['device_id'], str(device.device_id))
        self.assertEqual(device.name, 'Caja 1')
        self.assertIsNone(device.revoked_at)
        self.assertIsNotNone(PosPairingCode.objects.get(code = self.code).used_at)

    def test_code_is_case_insensitive(self):
        response    =   APIClient().post(PAIR_URL, {'code': self.code.lower(), 'device_name': 'Caja'}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_expired_code_rejected(self):
        row             =   PosPairingCode.objects.get(code = self.code)
        row.expires_at  =   timezone.now() - timedelta(minutes = 1)
        row.save(update_fields = ['expires_at'])
        response        =   APIClient().post(PAIR_URL, {'code': self.code, 'device_name': 'Caja'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PosDevice.objects.count(), 0)

    def test_used_code_cannot_be_redeemed_twice(self):
        client      =   APIClient()
        self.assertEqual(client.post(PAIR_URL, {'code': self.code, 'device_name': 'Caja 1'}, format = 'json').status_code, 201)
        response    =   client.post(PAIR_URL, {'code': self.code, 'device_name': 'Caja 2'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PosDevice.objects.count(), 1)

    def test_unknown_code_rejected(self):
        response    =   APIClient().post(PAIR_URL, {'code': 'ZZZZZZZZ', 'device_name': 'Caja'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_payload_rejected(self):
        client      =   APIClient()
        self.assertEqual(client.post(PAIR_URL, {}, format = 'json').status_code, 400)
        self.assertEqual(client.post(PAIR_URL, {'code': '123', 'device_name': 'Caja'}, format = 'json').status_code, 400)

    def test_throttled_per_code(self):
        client      =   APIClient()
        #5/min por código: el sexto intento vuelve 429 aunque el código ya
        #esté quemado (el throttle corre antes que la validación).
        statuses    =   [
            client.post(PAIR_URL, {'code': self.code, 'device_name': 'Caja'}, format = 'json').status_code
            for _ in range(6)
        ]
        self.assertIn(429, statuses)


@override_settings(POS_LICENSE_PRIVATE_KEY_B64 = _TEST_KEY_B64)
class PosLicenseTests(TestCase):

    def setUp(self):
        cache.clear()
        self.device, self.token =   _pair()

    def _license(self, token = None):
        return APIClient().post(LICENSE_URL, HTTP_AUTHORIZATION = f'Bearer {token or self.token}')

    def test_active_license_claims(self):
        response    =   self._license()
        self.assertEqual(response.status_code, 200)
        claims      =   _decode_license(response.json()['license'])
        self.assertEqual(claims['iss'], 'davent')
        self.assertEqual(claims['store_id'], self.device.store_id)
        self.assertEqual(claims['device_id'], str(self.device.device_id))
        self.assertEqual(claims['plan'], 'ecommerce')
        self.assertEqual(claims['status'], 'active')
        self.assertIsNone(claims['denied_reason'])
        self.assertIsNone(claims['grace_until'])
        self.assertEqual(claims['exp'] - claims['iat'], 45 * 24 * 3600)

    def test_updates_last_seen(self):
        self.assertIsNone(self.device.last_seen_at)
        self._license()
        self.device.refresh_from_db()
        self.assertIsNotNone(self.device.last_seen_at)

    def test_denied_without_subscription(self):
        #Sin suscripción: la licencia sale firmada con status denied —
        #la app entra en aviso, nunca en bloqueo silencioso.
        Suscription.objects.filter(user = self.device.store.user).delete()
        cache.delete(f'planben:{self.device.store.user_id}')
        response    =   self._license()
        claims      =   _decode_license(response.json()['license'])
        self.assertEqual(claims['status'], 'denied')
        self.assertEqual(claims['denied_reason'], 'plan_expired')
        self.assertIsNotNone(claims['grace_until'])

    def test_denied_expired_subscription(self):
        suscription             =   self.device.store.user.suscription
        suscription.end_date    =   timezone.now() - timedelta(days = 1)
        suscription.auto_renew  =   False
        suscription.save()
        claims      =   _decode_license(self._license().json()['license'])
        self.assertEqual(claims['status'], 'denied')
        self.assertEqual(claims['denied_reason'], 'plan_expired')

    def test_denied_plan_without_pos_benefit(self):
        #Plan vigente pero sin has_pos_app (downgrade) → plan_changed.
        PlanBenefit.objects.filter(benefit__code = 'has_pos_app').update(enabled = False)
        cache.delete(f'planben:{self.device.store.user_id}')
        claims      =   _decode_license(self._license().json()['license'])
        self.assertEqual(claims['status'], 'denied')
        self.assertEqual(claims['denied_reason'], 'plan_changed')

    def test_revoked_device_rejected(self):
        self.device.revoked_at  =   timezone.now()
        self.device.save(update_fields = ['revoked_at'])
        self.assertEqual(self._license().status_code, 403)

    def test_invalid_token_rejected(self):
        self.assertEqual(self._license('firma.trucha.jwt').status_code, 401)
        #Token HS256 válido pero firmado con otra clave.
        forged  =   jwt.encode({'typ': 'pos_device', 'store_id': 1, 'device_id': 'x'}, 'otra-clave', algorithm = 'HS256')
        self.assertEqual(self._license(forged).status_code, 401)

    def test_no_authorization_header_rejected(self):
        self.assertEqual(APIClient().post(LICENSE_URL).status_code, 401)


@override_settings(POS_LICENSE_PRIVATE_KEY_B64 = _TEST_KEY_B64)
class PosAppsTests(TestCase):

    def setUp(self):
        cache.clear()
        self.mostrador  =   PosApp.objects.get(slug = 'mostrador')
        self.retail     =   DesignCategory.objects.get_or_create(slug = 'retail', defaults = {'nombre': 'Retail'})[0]
        self.indumentaria   =   DesignCategory.objects.get_or_create(slug = 'indumentaria', defaults = {'nombre': 'Indumentaria'})[0]

    def _pattern(self, categoria, slug):
        return DesignPattern.objects.create(slug = slug, nombre = slug, categoria = categoria)

    def test_requires_auth(self):
        self.assertIn(APIClient().get(APPS_URL).status_code, (401, 403))

    def _apps(self, client, rubro = None):
        url     =   APPS_URL if rubro is None else f'{APPS_URL}?rubro={rubro}'
        return client.get(url).json()

    def test_ecommerce_plan_with_retail_design_sees_mostrador(self):
        pattern             =   self._pattern(self.retail, 'pos-retail-a')
        user, _, store      =   _make_owner()
        store.customization.template    =   pattern.slug
        store.customization.save()
        data                =   self._apps(_authed(user))
        slugs               =   [app['slug'] for app in data['apps']]
        self.assertIn('mostrador', slugs)
        self.assertEqual(data['rubro'], 'retail')
        app                 =   next(a for a in data['apps'] if a['slug'] == 'mostrador')
        self.assertEqual(app['tier_min'], 'ecommerce')
        self.assertEqual(app['rubros'], ['retail'])
        self.assertIn('preview_url', app)

    def test_rubros_options_in_response(self):
        #El selector de la card sale del mismo response: 'general'
        #primero, después las categorías activas.
        user, _, _      =   _make_owner()
        data            =   self._apps(_authed(user))
        slugs           =   [r['slug'] for r in data['rubros']]
        self.assertEqual(slugs[0], 'general')
        self.assertIn('retail', slugs)
        self.assertIn('indumentaria', slugs)

    def test_rubro_param_overrides_derived(self):
        #Tienda indumentaria que elige 'retail' en el selector ve las
        #apps de retail (exploración, no asignación).
        pattern             =   self._pattern(self.indumentaria, 'sastreria-x')
        user, _, store      =   _make_owner()
        store.customization.template    =   pattern.slug
        store.customization.save()
        data                =   self._apps(_authed(user), rubro = 'retail')
        self.assertEqual(data['rubro'], 'retail')
        self.assertIn('mostrador', [app['slug'] for app in data['apps']])

    def test_rubro_param_filters(self):
        #Tienda retail que elige 'indumentaria' deja de ver mostrador.
        pattern             =   self._pattern(self.retail, 'pos-retail-c')
        user, _, store      =   _make_owner()
        store.customization.template    =   pattern.slug
        store.customization.save()
        data                =   self._apps(_authed(user), rubro = 'indumentaria')
        self.assertEqual(data['rubro'], 'indumentaria')
        self.assertNotIn('mostrador', [app['slug'] for app in data['apps']])

    def test_lower_plan_does_not_see_ecommerce_app(self):
        user, _, store      =   _make_owner(plan_name = 'Plan basico', plan_slug = 'basico')
        pattern             =   self._pattern(self.retail, 'pos-retail-b')
        store.customization.template    =   pattern.slug
        store.customization.save()
        self.assertEqual(self._apps(_authed(user))['apps'], [])

    def test_other_rubro_does_not_see_retail_app(self):
        pattern             =   self._pattern(self.indumentaria, 'sastreria-x2')
        user, _, store      =   _make_owner()
        store.customization.template    =   pattern.slug
        store.customization.save()
        self.assertNotIn('mostrador', [app['slug'] for app in self._apps(_authed(user))['apps']])

    def test_store_without_design_sees_catalog(self):
        #Rubro 'general' (sin diseño elegido): la app sigue visible — no
        #se penaliza la indecisión (PLAN_POS §1).
        user, _, _      =   _make_owner()
        data            =   self._apps(_authed(user))
        self.assertEqual(data['rubro'], 'general')
        self.assertIn('mostrador', [app['slug'] for app in data['apps']])

    def test_style_rubro_counts(self):
        #Sin patrón propio en catálogo pero con estilo elegido del rubro
        #retail (site_theme.style.id = slug de DesignStyle).
        style   =   DesignStyle.objects.create(slug = 'mercado-x', nombre = 'Mercado X', categoria = self.retail)
        user, _, store  =   _make_owner()
        store.customization.site_theme  =   {'style': {'id': style.slug}}
        store.customization.save()
        self.assertIn('mostrador', [app['slug'] for app in self._apps(_authed(user))['apps']])

    def test_app_with_general_rubro_visible_for_any_store(self):
        PosApp.objects.create(slug = 'generica', nombre = 'Genérica', rubros = ['general'], tier_min = 'ecommerce')
        pattern             =   self._pattern(self.indumentaria, 'sastreria-y')
        user, _, store      =   _make_owner()
        store.customization.template    =   pattern.slug
        store.customization.save()
        slugs               =   [app['slug'] for app in self._apps(_authed(user))['apps']]
        self.assertIn('generica', slugs)
        self.assertNotIn('mostrador', slugs)

    def test_inactive_app_hidden(self):
        self.mostrador.is_active    =   False
        self.mostrador.save()
        user, _, _      =   _make_owner()
        self.assertEqual(self._apps(_authed(user))['apps'], [])


@override_settings(POS_LICENSE_PRIVATE_KEY_B64 = _TEST_KEY_B64)
class PosDownloadTests(TestCase):

    URL =   '/api/pos/download/mostrador/'

    def setUp(self):
        cache.clear()
        self.mostrador  =   PosApp.objects.get(slug = 'mostrador')
        self.retail     =   DesignCategory.objects.get_or_create(slug = 'retail', defaults = {'nombre': 'Retail'})[0]

    def _retail_owner(self, **kwargs):
        pattern     =   DesignPattern.objects.create(slug = f'pat-{kwargs.get("slug", "a")}', nombre = 'p', categoria = self.retail)
        user, _, store  =   _make_owner(**kwargs)
        store.customization.template    =   pattern.slug
        store.customization.save()
        return user

    def test_requires_auth(self):
        self.assertIn(APIClient().get(self.URL).status_code, (401, 403))

    def test_without_benefit_gets_403(self):
        user    =   self._retail_owner(codes = ())
        self.assertEqual(_authed(user).get(self.URL).status_code, 403)

    def test_happy_path_returns_signed_url(self):
        self.mostrador.download_key =   'pos/apps/mostrador/POS-Setup.exe'
        self.mostrador.save(update_fields = ['download_key'])
        user    =   self._retail_owner()
        response    =   _authed(user).get(self.URL)
        self.assertEqual(response.status_code, 200)
        url     =   response.json()['url']
        self.assertIn(self.mostrador.download_key, url)

    def test_app_without_installer_gets_404(self):
        self.mostrador.download_key =   ''
        self.mostrador.save(update_fields = ['download_key'])
        user    =   self._retail_owner()
        self.assertEqual(_authed(user).get(self.URL).status_code, 404)

    def test_app_outside_catalog_gets_404(self):
        #Con instalador publicado pero sin rubro compatible: misma
        #visibilidad que el catálogo — 404, no se filtra que la key existe.
        self.mostrador.download_key =   'pos/apps/mostrador/POS-Setup.exe'
        self.mostrador.save(update_fields = ['download_key'])
        indumentaria    =   DesignCategory.objects.get_or_create(slug = 'indumentaria', defaults = {'nombre': 'Indumentaria'})[0]
        pattern         =   DesignPattern.objects.create(slug = 'pat-ind', nombre = 'p', categoria = indumentaria)
        user, _, store  =   _make_owner()
        store.customization.template    =   pattern.slug
        store.customization.save()
        self.assertEqual(_authed(user).get(self.URL).status_code, 404)

    def test_rubro_param_unlocks_download(self):
        #La tienda indumentaria que eligió 'retail' en el selector puede
        #bajar la app de retail — lo que la card muestra, la card baja.
        self.mostrador.download_key =   'pos/apps/mostrador/POS-Setup.exe'
        self.mostrador.save(update_fields = ['download_key'])
        indumentaria    =   DesignCategory.objects.get_or_create(slug = 'indumentaria', defaults = {'nombre': 'Indumentaria'})[0]
        pattern         =   DesignPattern.objects.create(slug = 'pat-ind2', nombre = 'p', categoria = indumentaria)
        user, _, store  =   _make_owner()
        store.customization.template    =   pattern.slug
        store.customization.save()
        response    =   _authed(user).get(f'{self.URL}?rubro=retail')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mostrador.download_key, response.json()['url'])
