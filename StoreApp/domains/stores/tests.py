"""
Tests de seguridad del dominio stores.

El claim del slug exige correo verificado (anti-abuso del plan de prueba).
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.models import Store, StoreCustomization
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

STORES_URL = '/api/stores/'


def _make_user(verified):
    province    =   Province.objects.create(name_province = 'Mendoza')
    zipcode     =   ZipCode.objects.create(zipcode = '5500')
    city        =   City.objects.create(name_city = 'Mendoza', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = 'duenio', email = 'duenio@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   '27123456',
        province        =   province,
        city            =   city,
        email_verified  =   verified,
    )
    return user, profile


class StoreClaimVerificationTests(TestCase):

    def _claim(self, user):
        client  =   APIClient()
        client.force_authenticate(user = user)
        return client.post(STORES_URL, {'slug': 'mi-tienda', 'is_published': False}, format = 'json')

    def test_claim_blocked_without_verified_email(self):
        user, _     =   _make_user(verified = False)
        response    =   self._claim(user)
        self.assertEqual(response.status_code, 403)

    def test_claim_allowed_with_verified_email(self):
        user, _     =   _make_user(verified = True)
        response    =   self._claim(user)
        self.assertEqual(response.status_code, 201)


class StoreCatalogToggleTests(TestCase):
    """
    Catálogo opcional (customization.show_catalog): apagado, el endpoint
    público del catálogo devuelve 404 y la web queda como vidriera — sin
    borrar productos ni bloquear la gestión del panel.
    """

    def _make_store(self, show_catalog):
        _, profile      =   _make_user(verified = True)
        plan            =   SuscriptionPlan.objects.create(name = 'Plan test')
        benefit         =   Benefit.objects.create(code = 'has_public_link', label = 'Link público', kind = Benefit.FLAG)
        PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True)
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        StoreCustomization.objects.create(store = store, show_catalog = show_catalog)

    def test_public_catalog_ok_when_enabled(self):
        self._make_store(show_catalog = True)
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/')
        self.assertEqual(response.status_code, 200)

    def test_public_catalog_404_when_disabled(self):
        self._make_store(show_catalog = False)
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/')
        self.assertEqual(response.status_code, 404)

    def test_public_store_still_ok_when_catalog_disabled(self):
        #Solo se apaga la página Catálogo: la web pública sigue respondiendo.
        self._make_store(show_catalog = False)
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['customization']['show_catalog'])


class StoreListMineTests(TestCase):
    """
    El listado /stores/ de un staff trae todas las webs (panel admin); con
    ?mine=1 trae solo la suya, para que el panel de usuario no tome la web
    de otro cliente como propia (y todo PATCH diera 404).
    """

    def _setup(self):
        _, owner_profile    =   _make_user(verified = True)
        Store.objects.create(user = owner_profile, slug = 'cliente')
        admin               =   User.objects.create_user(username = 'admin', email = 'admin@gmail.com', password = 'Xq7#mP2vL9bT', is_staff = True)
        client              =   APIClient()
        client.force_authenticate(user = admin)
        return client

    def test_staff_list_returns_all_stores(self):
        client      =   self._setup()
        response    =   client.get(STORES_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results'] if isinstance(response.data, dict) else response.data), 1)

    def test_staff_list_mine_excludes_other_users_stores(self):
        client      =   self._setup()
        response    =   client.get(STORES_URL, {'mine': 1})
        self.assertEqual(response.status_code, 200)
        rows        =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 0)
