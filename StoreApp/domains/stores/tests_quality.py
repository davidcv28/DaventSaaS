"""
Tests del endpoint GET /api/stores/<slug>/web-quality/ (checklist
"Calidad de tu web" del dashboard): score 0-100, checks accionables,
permiso dueño/staff.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.stores.models import Store, StoreCustomization
from StoreApp.domains.stores.services.web_quality import web_quality_report


def _make_user(username, *, address = '', phone = None):
    #phone_hash es unique: el celular por defecto se deriva del username.
    phone       =   phone or f'1122{abs(hash(username)) % 10**8:08d}'
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'{abs(hash(username)) % 10000:04d}')
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'27{abs(hash(username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        address         =   address,
        phone           =   phone,
        email_verified  =   True,
    )
    return user, profile


def _grant(profile):
    """Plan + suscripción vigente (el checklist no mira beneficios, pero la
    tienda real siempre tiene plan; se crea por fidelidad del fixture)."""
    plan    =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username}')
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )


def _make_store(username = 'duenio', slug = 'mi-tienda', **custom_kwargs):
    user, profile  =   _make_user(username)
    _grant(profile)
    store           =   Store.objects.create(user = profile, slug = slug)
    customization   =   StoreCustomization.objects.create(store = store, **custom_kwargs)
    return user, profile, store, customization


def _add_products(store, count, *, with_photo = True, desc_len = 140, active = True):
    for i in range(count):
        Product.objects.create(
            store       =   store,
            name        =   f'Producto {i + 1}',
            price       =   1000 + i,
            description =   'x' * desc_len,
            image_key   =   f'stores/{store.pk}/products/{i}.webp' if with_photo else '',
            is_active   =   active,
        )


class WebQualityTests(TestCase):

    def _get(self, user, slug):
        client  =   APIClient()
        client.force_authenticate(user = user)
        return client.get(f'/api/stores/{slug}/web-quality/')

    def test_empty_store_scores_low_and_lists_failed_checks(self):
        user, _, store, _   =   _make_store()
        response            =   self._get(user, store.slug)
        self.assertEqual(response.status_code, 200)
        data                =   response.json()
        self.assertIn('score', data)
        self.assertIn('checks', data)
        self.assertLess(data['score'], 100)
        #Los pesos son explícitos y suman 100.
        self.assertEqual(sum(c['weight'] for c in data['checks']), 100)
        self.assertEqual(data['score'], sum(c['weight'] for c in data['checks'] if c['ok']))
        #Sin productos fallan los 3 checks de catálogo.
        failed  =   {c['id'] for c in data['checks'] if not c['ok']}
        self.assertTrue({'products_min', 'products_photo', 'products_desc'} <= failed)
        #Cada check trae la pestaña destino del dashboard.
        for check in data['checks']:
            self.assertIn(check['tab'], {'photos', 'catalogs', 'company', 'design', 'settings', 'store'})

    def test_without_logo_fails_logo_check(self):
        user, _, store, customization   =   _make_store()
        customization.logo_key  =   ''
        customization.save(update_fields = ['logo_key'])
        data                    =   self._get(user, store.slug).json()
        logo    =   next(c for c in data['checks'] if c['id'] == 'logo')
        self.assertFalse(logo['ok'])
        self.assertEqual(logo['weight'], 10)
        self.assertEqual(logo['tab'], 'photos')
        #El resto del score sigue la misma regla.
        self.assertEqual(data['score'], sum(c['weight'] for c in data['checks'] if c['ok']))

    def test_complete_store_scores_100(self):
        user, profile, store, customization   =   _make_store(
            logo_key        =   'stores/x/logo.webp',
            cover_key       =   'stores/x/cover.webp',
            about_text      =   'y' * 250,
            hours           =   [{'label': 'Lun a vie', 'value': '9 a 18 h'}],
            whatsapp        =   '1122334455',
            instagram       =   '@mitienda',
            template        =   'mercado',
            site_theme      =   {'style': {'id': 'mercado'}},
            show_location   =   True,
        )
        profile.address =   'Av. Siempre Viva 742'
        profile.save(update_fields = ['address'])
        _add_products(store, 8)
        response    =   self._get(user, store.slug)
        self.assertEqual(response.status_code, 200)
        data        =   response.json()
        self.assertEqual(data['score'], 100)
        self.assertTrue(all(c['ok'] for c in data['checks']))

    def test_foreign_store_returns_403(self):
        _, _, store, _     =   _make_store(username = 'duenio', slug = 'tienda-ajena')
        intruso, _         =   _make_user('intruso')
        response           =   self._get(intruso, store.slug)
        self.assertEqual(response.status_code, 403)

    def test_unknown_slug_returns_404(self):
        user, _, _, _       =   _make_store(username = 'duenio2', slug = 'otra-tienda')
        response            =   self._get(user, 'no-existe')
        self.assertEqual(response.status_code, 404)

    def test_staff_can_read_any_store(self):
        _, _, store, _      =   _make_store(username = 'duenio3', slug = 'tienda-staff')
        admin               =   User.objects.create_user(username = 'adminwq', password = 'Xq7#mP2vL9bT', is_staff = True)
        response            =   self._get(admin, store.slug)
        self.assertEqual(response.status_code, 200)

    def test_report_directly_matches_endpoint_contract(self):
        #El servicio puro devuelve el mismo contrato que la vista.
        _, _, store, _      =   _make_store(username = 'duenio4', slug = 'tienda-servicio')
        report              =   web_quality_report(
            Store.objects.select_related('customization', 'user__city', 'user__province').get(pk = store.pk)
        )
        self.assertEqual(set(report.keys()), {'score', 'checks'})
        for check in report['checks']:
            self.assertEqual(set(check.keys()), {'id', 'weight', 'ok', 'label', 'action', 'tab'})
