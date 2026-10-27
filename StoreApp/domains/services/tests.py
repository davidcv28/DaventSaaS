"""
Tests de seguridad del dominio services.

Página "Servicios" de la web pública: flag has_services_site (Estándar+),
cupo max_site_templates del plan sobre site_templates y aislamiento por
tienda en los endpoints del dueño.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.services.models import StoreService
from StoreApp.domains.services.services import SERVICES_MAX
from StoreApp.domains.stores.models import Store
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

STORES_URL    = '/api/stores/'
SERVICES_URL  = '/api/services/'


def _make_user(username, verified = True):
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'55{abs(hash(username)) % 100:02d}')
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'29{abs(hash(username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   verified,
        phone           =   f'1122{abs(hash(username)) % 10**8:08d}',
    )
    return user, profile


def _grant(profile, **benefits):
    """Plan + suscripción vigente de 30 días con los beneficios pedidos.

    bool -> flag habilitado/deshabilitado; int|None -> limit con ese
    valor (None = ilimitado)."""
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username} {profile.pk}')
    for code, value in benefits.items():
        kind        =   Benefit.FLAG if isinstance(value, bool) else Benefit.LIMIT
        benefit     =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': kind})[0]
        PlanBenefit.objects.create(
            plan        =   plan,
            benefit     =   benefit,
            enabled     =   value if kind == Benefit.FLAG else True,
            value       =   None if kind == Benefit.FLAG else value,
        )
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    return plan


class ServiceEntitlementTests(TestCase):
    """Los servicios del dueño se gestionan solo con has_services_site."""

    def _client(self, services = True, with_plan = True):
        _, profile      =   _make_user('duenio')
        if with_plan:
            _grant(
                profile,
                has_public_link     =   True,
                has_customization   =   True,
                has_services_site   =   services,
                max_site_templates  =   2,
            )
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client, store

    def test_list_forbidden_without_flag(self):
        client, _       =   self._client(services = False)
        self.assertEqual(client.get(SERVICES_URL).status_code, 403)

    def test_create_forbidden_without_flag(self):
        client, _       =   self._client(services = False)
        response        =   client.post(SERVICES_URL, {'name': 'Planchado'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_update_forbidden_without_flag(self):
        client, store   =   self._client(services = False)
        item            =   StoreService.objects.create(store = store, name = 'Planchado')
        response        =   client.patch(f'{SERVICES_URL}{item.id}/', {'name': 'Otro'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_order_forbidden_without_flag(self):
        client, _       =   self._client(services = False)
        response        =   client.patch(f'{SERVICES_URL}order/', {'order': []}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_forbidden_without_subscription(self):
        client, _       =   self._client(with_plan = False)
        self.assertEqual(client.get(SERVICES_URL).status_code, 403)

    def test_unauthenticated_is_rejected(self):
        self.assertEqual(APIClient().get(SERVICES_URL).status_code, 401)

    def test_crud_ok_with_flag(self):
        client, _       =   self._client()
        created         =   client.post(SERVICES_URL, {'name': 'Planchado', 'price': '5000'}, format = 'json')
        self.assertEqual(created.status_code, 201)
        item            =   created.data['item']
        self.assertEqual(item['position'], 1)
        updated         =   client.patch(f"{SERVICES_URL}{item['id']}/", {'price': '6000', 'duration': '≈ 1 h'}, format = 'json')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['item']['price'], '6000.00')
        deleted         =   client.delete(f"{SERVICES_URL}{item['id']}/")
        self.assertEqual(deleted.status_code, 200)


class ServiceIsolationTests(TestCase):
    """Una tienda no alcanza los servicios de otra (404, no 403)."""

    def test_foreign_service_not_reachable(self):
        _, owner        =   _make_user('duenio')
        _, intruder     =   _make_user('intruso')
        _grant(owner, has_public_link = True, has_services_site = True, max_site_templates = 2)
        _grant(intruder, has_public_link = True, has_services_site = True, max_site_templates = 2)
        store           =   Store.objects.create(user = owner, slug = 'tienda-uno')
        Store.objects.create(user = intruder, slug = 'tienda-dos')
        item            =   StoreService.objects.create(store = store, name = 'Ruedo')
        client          =   APIClient()
        client.force_authenticate(user = intruder.user)
        self.assertEqual(client.patch(f'{SERVICES_URL}{item.id}/', {'name': 'Otro'}, format = 'json').status_code, 404)
        self.assertEqual(client.delete(f'{SERVICES_URL}{item.id}/').status_code, 404)
        #El listado del intruso no incluye el servicio ajeno.
        self.assertEqual(client.get(SERVICES_URL).data, [])


class ServiceValidationTests(TestCase):

    def _client(self):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True, has_customization = True, has_services_site = True, max_site_templates = 2)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client, store

    def test_duplicate_name_iexact_is_400(self):
        client, store   =   self._client()
        StoreService.objects.create(store = store, name = 'Planchado')
        response        =   client.post(SERVICES_URL, {'name': '  PLANCHADO '}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_negative_price_is_400(self):
        client, _       =   self._client()
        response        =   client.post(SERVICES_URL, {'name': 'X', 'price': '-5'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_price_null_means_a_convenir(self):
        client, _       =   self._client()
        response        =   client.post(SERVICES_URL, {'name': 'A convenir', 'price': None}, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data['item']['price'])

    def test_icon_outside_catalog_falls_back(self):
        client, _       =   self._client()
        response        =   client.post(SERVICES_URL, {'name': 'Servicio X', 'icon': 'skull'}, format = 'json')
        self.assertEqual(response.data['item']['icon'], 'wrench')

    def test_services_cap_is_enforced(self):
        client, store   =   self._client()
        for i in range(SERVICES_MAX):
            StoreService.objects.create(store = store, name = f'Servicio {i}', position = i)
        response        =   client.post(SERVICES_URL, {'name': 'De mas'}, format = 'json')
        self.assertEqual(response.status_code, 403)
        self.assertIn(str(SERVICES_MAX), response.data['detail'])

    def test_order_reorders_and_ignores_foreign_ids(self):
        client, store   =   self._client()
        _, other        =   _make_user('otro')
        other_store     =   Store.objects.create(user = other, slug = 'otra')
        foreign         =   StoreService.objects.create(store = other_store, name = 'Ajeno')
        a               =   StoreService.objects.create(store = store, name = 'A', position = 0)
        b               =   StoreService.objects.create(store = store, name = 'B', position = 1)
        c               =   StoreService.objects.create(store = store, name = 'C', position = 2)
        response        =   client.patch(f'{SERVICES_URL}order/', {'order': [c.id, foreign.id, a.id]}, format = 'json')
        self.assertEqual(response.status_code, 200)
        positions       =   {s.id: s.position for s in StoreService.objects.filter(store = store)}
        self.assertEqual(positions[c.id], 0)
        self.assertEqual(positions[a.id], 1)
        #B (no mencionado) conserva su orden relativo al final.
        self.assertEqual(positions[b.id], 2)
        foreign.refresh_from_db()
        self.assertEqual(foreign.position, 0)


class SiteTemplatesTests(TestCase):
    """
    site_templates: whitelist cerrada, cupo max_site_templates y flag
    has_services_site forzados server-side; show_catalog se deriva y el
    payload público viaja efectivo (lo guardado ∩ el plan vigente).
    """

    def _client(self, services = True, max_templates = 2):
        _, profile      =   _make_user('duenio')
        plan            =   _grant(
            profile,
            has_public_link     =   True,
            has_customization   =   True,
            has_services_site   =   services,
            max_site_templates  =   max_templates,
        )
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client, store, plan

    def _patch(self, client, templates):
        return client.patch(f'{STORES_URL}customization/', {'site_templates': templates}, format = 'json')

    def test_services_page_rejected_without_flag(self):
        client, _, _    =   self._client(services = False)
        response        =   self._patch(client, ['landing', 'services'])
        self.assertEqual(response.status_code, 400)
        self.assertIn('site_templates', response.data)

    def test_three_pages_rejected_over_plan_limit(self):
        client, _, _    =   self._client(max_templates = 2)
        response        =   self._patch(client, ['landing', 'services', 'catalog'])
        self.assertEqual(response.status_code, 400)
        self.assertIn('site_templates', response.data)

    def test_three_pages_ok_with_unlimited_plan(self):
        client, _, _    =   self._client(max_templates = None)
        response        =   self._patch(client, ['catalog', 'services', 'landing'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['site_templates'], ['landing', 'services', 'catalog'])

    def test_empty_list_rejected(self):
        client, _, _    =   self._client()
        self.assertEqual(self._patch(client, []).status_code, 400)
        self.assertEqual(self._patch(client, ['bogus']).status_code, 400)

    def test_unknown_and_repeated_keys_are_filtered(self):
        client, _, _    =   self._client(max_templates = None)
        response        =   self._patch(client, ['services', 'bogus', 'services', 'landing'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['site_templates'], ['landing', 'services'])

    def test_show_catalog_is_derived(self):
        client, _, _    =   self._client()
        response        =   self._patch(client, ['landing', 'services'])
        self.assertFalse(response.data['customization']['show_catalog'])
        response        =   self._patch(client, ['landing', 'catalog'])
        self.assertTrue(response.data['customization']['show_catalog'])

    def test_site_mode_is_exposed_derived(self):
        client, _, _    =   self._client()
        response        =   self._patch(client, ['landing', 'catalog'])
        self.assertEqual(response.data['customization']['site_mode'], 'both')
        response        =   self._patch(client, ['landing', 'services'])
        self.assertEqual(response.data['customization']['site_mode'], 'marketing')
        response        =   self._patch(client, ['services', 'catalog'])
        self.assertEqual(response.data['customization']['site_mode'], 'catalog')

    def test_public_payload_is_effective(self):
        client, store, plan =   self._client(max_templates = None)
        self._patch(client, ['landing', 'services', 'catalog'])
        public          =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(public.data['customization']['site_templates'], ['landing', 'services', 'catalog'])
        #Baja del flag: 'services' sale del set efectivo aunque siga guardado.
        PlanBenefit.objects.filter(plan = plan, benefit__code = 'has_services_site').delete()
        public          =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(public.data['customization']['site_templates'], ['landing', 'catalog'])
        self.assertEqual(public.data['customization']['site_mode'], 'both')

    def test_public_catalog_404_when_outside_effective_templates(self):
        #show_catalog quedó en True pero 'catalog' no entra en el cupo
        #efectivo (baja de plan con 3 páginas guardadas -> tope 1).
        client, store, plan =   self._client(max_templates = None)
        self._patch(client, ['landing', 'services', 'catalog'])
        #save() y no update(): post_save del PlanBenefit bustea el cache
        #de beneficios (planben:<id>); un .update() serviría el set viejo.
        limit                   =   PlanBenefit.objects.get(plan = plan, benefit__code = 'max_site_templates')
        limit.value             =   1
        limit.save(update_fields = ['value'])
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/')
        self.assertEqual(response.status_code, 404)

    def test_service_items_in_public_payload_only_when_enabled(self):
        client, store, plan =   self._client()
        StoreService.objects.create(store = store, name = 'Ruedo', price = 12000, is_active = True)
        StoreService.objects.create(store = store, name = 'Apagado', is_active = False)
        #Página apagada: el payload público no viaja servicios.
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(response.data['service_items'], [])
        #Página encendida: solo los activos y con el payload mínimo.
        self._patch(client, ['landing', 'services'])
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        items           =   response.data['service_items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Ruedo')
        self.assertNotIn('is_active', items[0])
        #Sin el flag del plan la página se apaga aunque quede guardada.
        PlanBenefit.objects.filter(plan = plan, benefit__code = 'has_services_site').delete()
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(response.data['service_items'], [])

    def test_public_store_404_without_public_link(self):
        _, profile      =   _make_user('sinplan')
        _grant(profile, has_public_link = False, has_services_site = True)
        Store.objects.create(user = profile, slug = 'sin-web')
        self.assertEqual(APIClient().get(f'{STORES_URL}public/sin-web/').status_code, 404)


class ServicePageConfigTests(TestCase):
    """La config de la página Servicios se sanea en el serializer."""

    def _client(self):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True, has_customization = True, has_services_site = True, max_site_templates = 2)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client

    def test_service_steps_are_sanitized(self):
        client          =   self._client()
        response        =   client.patch(f'{STORES_URL}customization/', {
            'service_steps': [
                {'icon': 'skull', 'title': 'Pedís', 'text': 'Coordinamos por WhatsApp'},
                {'icon': 'truck', 'title': 'Solo titulo'},
                'basura',
            ],
        }, format = 'json')
        steps           =   response.data['customization']['service_steps']
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['icon'], 'check')  # skull fuera del catálogo -> default
        self.assertEqual(steps[0]['title'], 'Pedís')

    def test_service_days_and_slots_are_deduped(self):
        client          =   self._client()
        response        =   client.patch(f'{STORES_URL}customization/', {
            'service_days': ['Lunes', '  lunes ', '', 'Martes'],
            'service_slots': 'no-es-lista',
        }, format = 'json')
        self.assertEqual(response.status_code, 400)
        response        =   client.patch(f'{STORES_URL}customization/', {
            'service_days': ['Lunes', '  lunes ', '', 'Martes'],
        }, format = 'json')
        self.assertEqual(response.data['customization']['service_days'], ['Lunes', 'Martes'])


class ServiceNoTransactionsTests(TestCase):
    """
    Regla dura del producto: la web nunca persiste pedidos, reservas ni
    pagos — la selección del visitante viaja en un mensaje de WhatsApp.
    El dominio solo tiene StoreService (ítems de la página) y no existe
    ningún endpoint de booking/order/checkout bajo /api/services/.
    """

    def test_services_app_has_no_transaction_models(self):
        from django.apps import apps
        models      =   {m.__name__.lower() for m in apps.get_app_config('services').get_models()}
        self.assertEqual(models, {'storeservice'})
        forbidden =   ('order', 'booking', 'reservation', 'payment', 'invoice', 'cart', 'checkout')
        self.assertFalse(any(word in name for name in models for word in forbidden))

    def test_no_booking_endpoint_under_services(self):
        client      =   APIClient()
        for path in ('/api/services/book/', '/api/services/order/1/', '/api/services/pay/'):
            self.assertIn(client.post(path, {}, format = 'json').status_code, (401, 404))

