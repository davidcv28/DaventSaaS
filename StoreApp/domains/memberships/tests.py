"""
Tests de seguridad del dominio memberships (PROMPT_MAESTRO 3.5).

Cobertura:
- Helpers de beneficios: vigente / vencido / cancelled / pending /
  past_due / sin membresía / customer=None.
- Owner: CRUD de planes (validaciones período/beneficios, mass-
  assignment de store), IDOR 404 en planes y suscripciones, destroy
  que desactiva si hay historial, activate idempotente, cancel corta
  beneficios al instante, expire.
- Customer: subscribe crea pending + membership + instrucciones,
  duplicado -> 409, membresía suspendida -> 403, método de pago inválido
  -> 400, plan ajeno -> 404, tarjeta digital (auth + pública por
  public_token no enumerable), exclusivos solo para miembros.
- Catálogo público: Product.is_exclusive invisible al anónimo (lista y
  reviews) y visible al miembro por el endpoint dedicado.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.customers.models import Customer, StoreMembership
from StoreApp.domains.customers.services.tokens import issue_customer_tokens
from StoreApp.domains.memberships.models import StorePlan, StoreSubscription
from StoreApp.domains.memberships.services.benefits import (
    active_subscription_of,
    expire_check,
    free_shipping_for,
    grant_period,
    has_exclusive_access,
    member_benefits,
    member_discount_percent,
)
from StoreApp.domains.stores.models import Store, StoreCustomization
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

PLANS_URL           =   '/api/store-plans/'
SUBSCRIPTIONS_URL   =   '/api/store-subscriptions/'
CUSTOMER_SUBS       =   '/api/customer/subscriptions/'
CUSTOMER_CARD       =   '/api/customer/subscriptions/{slug}/card/'
PUBLIC_CARD         =   '/api/membership-cards/{slug}/{token}/'
EXCLUSIVE_URL       =   '/api/customer/stores/{slug}/exclusive-products/'
PUBLIC_CATALOG      =   '/api/stores/public/{slug}/catalog/'
PUBLIC_REVIEWS      =   '/api/stores/public/{slug}/products/{pid}/reviews/'


def _make_user(username, verified = True):
    """auth.User + UserProfile mínimo (mismo patrón que catalog/tests)."""
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'6{abs(hash(username)) % 1000:03d}')
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Due',
        last_name       =   'Nio',
        document        =   f'27{abs(hash(username + username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   verified,
    )
    return user, profile


def _grant(profile, **benefits):
    """Plan DAVENT + suscripción vigente de 30 días (bool = flag)."""
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username}')
    for code, value in benefits.items():
        benefit     =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': Benefit.FLAG})[0]
        PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = value, value = None)
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    return plan


def _owner(username = 'duenio', slug = 'mi-tienda', with_plan = True, **benefits):
    user, profile   =   _make_user(username)
    if with_plan:
        _grant(profile, has_public_link = True, **benefits)
    store           =   Store.objects.create(user = profile, slug = slug)
    client          =   APIClient()
    client.force_authenticate(user = user)
    return client, store


def _customer(email = 'comprador@test.com', first_name = 'María', last_name = 'Pérez'):
    customer        =   Customer(email = email, first_name = first_name, last_name = last_name)
    customer.set_password('Clave#12345')
    customer.save()
    return customer


def _customer_client(customer):
    access, _refresh   =   issue_customer_tokens(customer)
    client              =   APIClient()
    client.credentials(HTTP_AUTHORIZATION = f'Bearer {access}')
    return client


def _membership(customer, store, status = 'active'):
    return StoreMembership.objects.create(customer = customer, store = store, status = status)


def _plan(store, **kwargs):
    defaults    =   dict(
        name                    =   'Plan socio',
        price                   =   Decimal('1500.00'),
        period                  =   StorePlan.PERIOD_MONTHLY,
        period_days             =   30,
        has_free_shipping       =   True,
        has_exclusive_access    =   True,
        has_digital_card        =   True,
        has_exclusive_discounts =   True,
        discount_percent        =   Decimal('10.00'),
    )
    defaults.update(kwargs)
    return StorePlan.objects.create(store = store, **defaults)


def _subscription(membership, plan, status = 'pending', **kwargs):
    defaults    =   dict(membership = membership, plan = plan, status = status)
    defaults.update(kwargs)
    return StoreSubscription.objects.create(**defaults)


def _active_subscription(membership, plan, days = 30):
    now     =   timezone.now()
    return _subscription(
        membership, plan, status = 'active',
        started_at = now, vigente_hasta = now + timedelta(days = days),
    )


class BenefitsHelpersTests(TestCase):
    """Contrato de services/benefits.py — tolerancia y regla de vigencia."""

    def setUp(self):
        cache.clear()
        _, profile       =   _make_user('duenio')
        self.store       =   Store.objects.create(user = profile, slug = 'tienda-x')
        self.customer    =   _customer()
        self.membership  =   _membership(self.customer, self.store)
        self.plan        =   _plan(self.store)

    def test_sin_membresia_devuelve_vacio(self):
        otro        =   _customer('otro@test.com')
        self.assertIsNone(active_subscription_of(otro, self.store))
        self.assertEqual(member_benefits(otro, self.store), set())
        self.assertEqual(member_discount_percent(otro, self.store), 0)
        self.assertFalse(free_shipping_for(otro, self.store))
        self.assertFalse(has_exclusive_access(otro, self.store))

    def test_customer_none_no_explota(self):
        self.assertIsNone(active_subscription_of(None, self.store))
        self.assertEqual(member_benefits(None, self.store), set())
        self.assertEqual(member_discount_percent(None, self.store), 0)
        self.assertFalse(free_shipping_for(None, self.store))
        self.assertFalse(has_exclusive_access(None, self.store))
        self.assertIsNone(active_subscription_of(self.customer, None))

    def test_pending_no_da_beneficios(self):
        _subscription(self.membership, self.plan, status = 'pending')
        self.assertIsNone(active_subscription_of(self.customer, self.store))
        self.assertEqual(member_benefits(self.customer, self.store), set())
        self.assertEqual(member_discount_percent(self.customer, self.store), 0)
        self.assertFalse(has_exclusive_access(self.customer, self.store))

    def test_activa_vigente_da_beneficios(self):
        sub     =   _active_subscription(self.membership, self.plan)
        self.assertEqual(active_subscription_of(self.customer, self.store).pk, sub.pk)
        self.assertEqual(
            member_benefits(self.customer, self.store),
            {'digital_card', 'free_shipping', 'exclusive_discounts', 'exclusive_access'},
        )
        self.assertEqual(member_discount_percent(self.customer, self.store), Decimal('10.00'))
        self.assertTrue(free_shipping_for(self.customer, self.store))
        self.assertTrue(has_exclusive_access(self.customer, self.store))

    def test_vencida_pierde_beneficios_al_leer(self):
        _active_subscription(self.membership, self.plan, days = -1)
        self.assertIsNone(active_subscription_of(self.customer, self.store))
        self.assertEqual(member_benefits(self.customer, self.store), set())

    def test_cancelled_pierde_beneficios_al_instante(self):
        #Semántica documentada: cancelled exige status='active' -> corta ya.
        _subscription(
            self.membership, self.plan, status = 'cancelled',
            started_at = timezone.now() - timedelta(days = 5),
            vigente_hasta = timezone.now() + timedelta(days = 25),
        )
        self.assertIsNone(active_subscription_of(self.customer, self.store))
        self.assertEqual(member_benefits(self.customer, self.store), set())

    def test_membresia_suspendida_no_da_beneficios(self):
        #Castigo del comercio: suspende la StoreMembership y la suscripción
        #'active' deja de otorgar TODO (benefits exige membership activa).
        _active_subscription(self.membership, self.plan)
        self.membership.status   =   'suspended'
        self.membership.save(update_fields = ['status'])
        self.assertIsNone(active_subscription_of(self.customer, self.store))
        self.assertEqual(member_benefits(self.customer, self.store), set())
        self.assertEqual(member_discount_percent(self.customer, self.store), 0)
        self.assertFalse(free_shipping_for(self.customer, self.store))
        self.assertFalse(has_exclusive_access(self.customer, self.store))

    def test_past_due_y_expired_sin_beneficios(self):
        now     =   timezone.now()
        for st in ('past_due', 'expired'):
            StoreSubscription.objects.all().delete()
            _subscription(
                self.membership, self.plan, status = st,
                started_at = now, vigente_hasta = now + timedelta(days = 10),
            )
            self.assertEqual(member_benefits(self.customer, self.store), set(), st)
            self.assertFalse(has_exclusive_access(self.customer, self.store), st)

    def test_plan_sin_flag_no_da_ese_beneficio(self):
        plan    =   _plan(self.store, has_free_shipping = False, has_exclusive_access = False,
                          has_digital_card = False, has_exclusive_discounts = False, discount_percent = Decimal('0'))
        _active_subscription(self.membership, plan)
        self.assertEqual(member_benefits(self.customer, self.store), set())
        self.assertEqual(member_discount_percent(self.customer, self.store), 0)

    def test_grant_period_activa_y_fija_fechas(self):
        sub     =   _subscription(self.membership, self.plan, status = 'pending')
        grant_period(sub)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'active')
        self.assertIsNotNone(sub.started_at)
        self.assertAlmostEqual(
            (sub.vigente_hasta - timezone.now()).days, 29, delta = 1,
        )

    def test_expire_check_marca_vencidas(self):
        vieja   =   _active_subscription(self.membership, self.plan, days = -2)
        nueva   =   _active_subscription(_membership(_customer('b@test.com'), self.store), self.plan, days = 10)
        #Dos activas a la vez es anomalía pero expire_check no debe tocar la vigente.
        updated =   expire_check()
        vieja.refresh_from_db()
        nueva.refresh_from_db()
        self.assertEqual(vieja.status, 'expired')
        self.assertEqual(nueva.status, 'active')
        self.assertGreaterEqual(updated, 1)


class OwnerPlanTests(TestCase):
    """CRUD /api/store-plans/ — scope a la tienda del dueño + validaciones."""

    def setUp(self):
        cache.clear()

    def test_anonymous_rejected(self):
        self.assertEqual(APIClient().get(PLANS_URL).status_code, 401)
        self.assertEqual(APIClient().post(PLANS_URL, {}, format = 'json').status_code, 401)

    def test_owner_without_store_404(self):
        user, _profile   =   _make_user('sin-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        self.assertEqual(client.get(PLANS_URL).status_code, 404)

    def test_create_and_list_plan(self):
        client, store    =   _owner('duenio-a', 'tienda-a')
        response        =   client.post(PLANS_URL, {
            'name': 'Club', 'price': '2000', 'period': 'monthly',
            'has_free_shipping': True, 'has_exclusive_access': True,
        }, format = 'json')
        self.assertEqual(response.status_code, 201, response.data)
        plan    =   StorePlan.objects.get(store = store)
        self.assertEqual(plan.period_days, 30)          #monthly fija 30
        self.assertEqual(str(plan.price), '2000.00')
        listed  =   client.get(PLANS_URL)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]['subscriptions_count'], 0)

    def test_period_days_canonical_for_monthly_yearly(self):
        client, store    =   _owner('duenio-b', 'tienda-b')
        #period_days=99 con period=monthly -> el servidor pisa a 30.
        response        =   client.post(PLANS_URL, {
            'name': 'Anual', 'price': '0', 'period': 'yearly', 'period_days': 99,
        }, format = 'json')
        self.assertEqual(response.status_code, 201, response.data)
        plan            =   StorePlan.objects.get(store = store)
        self.assertEqual(plan.period_days, 365)

    def test_custom_requires_period_days(self):
        client, _        =   _owner('duenio-c', 'tienda-c')
        response        =   client.post(PLANS_URL, {
            'name': 'Custom', 'price': '0', 'period': 'custom', 'period_days': 0,
        }, format = 'json')
        self.assertEqual(response.status_code, 400)
        response        =   client.post(PLANS_URL, {
            'name': 'Custom', 'price': '0', 'period': 'custom', 'period_days': 90,
        }, format = 'json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(StorePlan.objects.latest('id').period_days, 90)

    def test_exclusive_discounts_requires_percent(self):
        client, _        =   _owner('duenio-d', 'tienda-d')
        response        =   client.post(PLANS_URL, {
            'name': 'Sin %', 'price': '0', 'period': 'monthly',
            'has_exclusive_discounts': True, 'discount_percent': '0',
        }, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('discount_percent', response.data)
        #Con % válido pasa.
        response        =   client.post(PLANS_URL, {
            'name': 'Con %', 'price': '0', 'period': 'monthly',
            'has_exclusive_discounts': True, 'discount_percent': '15',
        }, format = 'json')
        self.assertEqual(response.status_code, 201, response.data)

    def test_discount_percent_out_of_range_400(self):
        client, _        =   _owner('duenio-e', 'tienda-e')
        response        =   client.post(PLANS_URL, {
            'name': 'Raro', 'price': '0', 'period': 'monthly',
            'has_exclusive_discounts': True, 'discount_percent': '150',
        }, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_store_field_not_writable_mass_assignment(self):
        client_a, store_a  =   _owner('duenio-f', 'tienda-f')
        _, store_b          =   _owner('duenio-g', 'tienda-g')
        response            =   client_a.post(PLANS_URL, {
            'name': 'Secuestro', 'price': '0', 'period': 'monthly', 'store': store_b.pk,
        }, format = 'json')
        self.assertEqual(response.status_code, 201, response.data)
        #El plan quedó en la tienda del autenticado, nunca en la ajena.
        self.assertEqual(StorePlan.objects.get(name = 'Secuestro').store_id, store_a.pk)

    def test_idor_plan_detail_update_destroy(self):
        client_a, store_a  =   _owner('duenio-h', 'tienda-h')
        client_b, _        =   _owner('duenio-i', 'tienda-i')
        plan                =   _plan(store_a)
        url                 =   f'{PLANS_URL}{plan.pk}/'
        self.assertEqual(client_b.get(url).status_code, 404)
        self.assertEqual(client_b.patch(url, {'name': 'Hackeo'}, format = 'json').status_code, 404)
        self.assertEqual(client_b.delete(url).status_code, 404)
        plan.refresh_from_db()
        self.assertEqual(plan.name, 'Plan socio')

    def test_destroy_without_subscriptions_deletes(self):
        client, store      =   _owner('duenio-j', 'tienda-j')
        plan                =   _plan(store)
        response            =   client.delete(f'{PLANS_URL}{plan.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StorePlan.objects.filter(pk = plan.pk).exists())

    def test_destroy_with_subscriptions_deactivates(self):
        client, store      =   _owner('duenio-k', 'tienda-k')
        plan                =   _plan(store)
        customer            =   _customer()
        membership          =   _membership(customer, store)
        _subscription(membership, plan, status = 'expired')
        response            =   client.delete(f'{PLANS_URL}{plan.pk}/')
        self.assertEqual(response.status_code, 200, response.data)
        plan.refresh_from_db()
        self.assertFalse(plan.is_active)
        self.assertTrue(StorePlan.objects.filter(pk = plan.pk).exists())


class OwnerSubscriptionTests(TestCase):
    """GET /api/store-subscriptions/ + activate/cancel/expire del dueño."""

    def setUp(self):
        cache.clear()
        self.client, self.store   =   _owner('duenio-s', 'tienda-s')
        self.plan                   =   _plan(self.store)
        self.customer               =   _customer()
        self.membership             =   _membership(self.customer, self.store)
        self.sub                    =   _subscription(self.membership, self.plan, status = 'pending')

    def test_list_scoped_and_status_filter(self):
        _, store_b  =   _owner('otro-duenio', 'tienda-t')
        _subscription(_membership(_customer('x@test.com'), store_b), _plan(store_b), status = 'pending')
        response    =   self.client.get(SUBSCRIPTIONS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['customer_email'], self.customer.email)
        self.assertEqual(response.data[0]['plan']['name'], 'Plan socio')
        #Filtro válido e inválido.
        response    =   self.client.get(SUBSCRIPTIONS_URL, {'status': 'pending'})
        self.assertEqual(len(response.data), 1)
        response    =   self.client.get(SUBSCRIPTIONS_URL, {'status': 'bogus'})
        self.assertEqual(response.status_code, 400)

    def test_idor_subscription_actions_404(self):
        client_b, _  =   _owner('intruso', 'tienda-u')
        for action in ('activate', 'cancel', 'expire'):
            response    =   client_b.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/{action}/')
            self.assertEqual(response.status_code, 404, action)
        response        =   client_b.get(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/')
        self.assertEqual(response.status_code, 404)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'pending')

    def test_activate_pending_grants_period_and_is_idempotent(self):
        response    =   self.client.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/activate/')
        self.assertEqual(response.status_code, 200, response.data)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'active')
        self.assertIsNotNone(self.sub.vigente_hasta)
        hasta_1     =   self.sub.vigente_hasta
        #Segundo activate: idempotente — no regenera fechas.
        response    =   self.client.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/activate/')
        self.assertEqual(response.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.vigente_hasta, hasta_1)
        #Y el beneficio aparece para el cliente.
        self.assertTrue(has_exclusive_access(self.customer, self.store))

    def test_cancel_cuts_benefits_immediately(self):
        self.client.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/activate/')
        self.assertTrue(member_benefits(self.customer, self.store))
        response    =   self.client.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/cancel/')
        self.assertEqual(response.status_code, 200, response.data)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'cancelled')
        #cancelled pierde beneficios YA aunque vigente_hasta siga futuro.
        self.assertEqual(member_benefits(self.customer, self.store), set())
        #Idempotente.
        response    =   self.client.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/cancel/')
        self.assertEqual(response.status_code, 200)

    def test_expire_forces_terminal_state(self):
        self.client.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/activate/')
        response    =   self.client.post(f'{SUBSCRIPTIONS_URL}{self.sub.pk}/expire/')
        self.assertEqual(response.status_code, 200, response.data)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'expired')
        self.assertEqual(member_benefits(self.customer, self.store), set())

    def test_expire_on_pending_is_400(self):
        sub2        =   _membership(_customer('p2@test.com'), self.store)
        pend        =   _subscription(sub2, self.plan, status = 'pending')
        response    =   self.client.post(f'{SUBSCRIPTIONS_URL}{pend.pk}/expire/')
        self.assertEqual(response.status_code, 400)


class CustomerSubscriptionTests(TestCase):
    """Endpoints /api/customer/* — JWT de comprador + tarjetas."""

    def setUp(self):
        cache.clear()
        self.client_owner, self.store   =   _owner('duenio-c', 'tienda-c')
        self.plan                        =   _plan(self.store)
        self.customer                    =   _customer()
        self.client                      =   _customer_client(self.customer)

    def test_anonymous_401(self):
        #CustomerJWTAuthentication devuelve 401 (WWW-Authenticate Bearer)
        #cuando falta el token, igual que los endpoints /api/customer/*.
        self.assertEqual(APIClient().get(CUSTOMER_SUBS).status_code, 401)
        self.assertEqual(APIClient().get(CUSTOMER_SUBS + 'tienda-c/').status_code, 401)
        self.assertEqual(APIClient().get(EXCLUSIVE_URL.format(slug = 'tienda-c')).status_code, 401)

    def test_get_store_plans_and_subscription(self):
        response    =   self.client.get(CUSTOMER_SUBS + 'tienda-c/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data['plans']), 1)
        self.assertEqual(response.data['plans'][0]['benefits'],
                         ['digital_card', 'exclusive_access', 'exclusive_discounts', 'free_shipping'])
        self.assertIsNone(response.data['subscription'])
        self.assertEqual(response.data['benefits'], [])

    def test_store_slug_unknown_404(self):
        self.assertEqual(self.client.get(CUSTOMER_SUBS + 'no-existe/').status_code, 404)

    def test_subscribe_creates_pending_membership_and_instructions(self):
        response    =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', {'plan_id': self.plan.pk, 'payment_method': 'transfer'}, format = 'json')
        self.assertEqual(response.status_code, 201, response.data)
        sub         =   StoreSubscription.objects.get()
        self.assertEqual(sub.status, 'pending')
        self.assertEqual(sub.payment_method, 'transfer')
        membership  =   StoreMembership.objects.get(customer = self.customer, store = self.store)
        self.assertEqual(membership.status, 'active')
        self.assertIn('payment', response.data)
        #Pending NO da beneficios.
        self.assertEqual(member_benefits(self.customer, self.store), set())

    def test_subscribe_duplicate_409_idempotent(self):
        payload =   {'plan_id': self.plan.pk}
        first   =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', payload, format = 'json')
        self.assertEqual(first.status_code, 201)
        second  =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', payload, format = 'json')
        self.assertEqual(second.status_code, 409)
        self.assertEqual(StoreSubscription.objects.count(), 1)

    def test_subscribe_foreign_or_inactive_plan_404(self):
        _, store_b      =   _owner('otro', 'tienda-otra')
        plan_b          =   _plan(store_b)
        response        =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', {'plan_id': plan_b.pk}, format = 'json')
        self.assertEqual(response.status_code, 404)
        plan_off        =   _plan(self.store, is_active = False)
        response        =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', {'plan_id': plan_off.pk}, format = 'json')
        self.assertEqual(response.status_code, 404)
        #plan_id basura -> 404, nunca 500.
        response        =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', {'plan_id': 'abc'}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_subscribe_invalid_payment_method_400(self):
        response    =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', {'plan_id': self.plan.pk, 'payment_method': 'crypto'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_subscribe_suspended_membership_403(self):
        _membership(self.customer, self.store, status = 'suspended')
        response    =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', {'plan_id': self.plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_subscribe_active_vigente_blocks_new_409(self):
        membership  =   _membership(self.customer, self.store)
        _active_subscription(membership, self.plan)
        response    =   self.client.post(CUSTOMER_SUBS + 'tienda-c/', {'plan_id': self.plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 409)

    def test_customer_subscriptions_list(self):
        membership  =   _membership(self.customer, self.store)
        _active_subscription(membership, self.plan)
        other       =   _customer('otra@test.com')
        _active_subscription(_membership(other, self.store), self.plan)
        response    =   self.client.get(CUSTOMER_SUBS)
        self.assertEqual(response.status_code, 200)
        #Paginado DRF: results[] — solo las mías.
        results     =   response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['store_slug'], 'tienda-c')
        self.assertTrue(results[0]['is_vigente'])

    def test_my_card_requires_vigente_and_digital_card(self):
        url         =   CUSTOMER_CARD.format(slug = 'tienda-c')
        #Sin suscripción -> 404.
        self.assertEqual(self.client.get(url).status_code, 404)
        membership  =   _membership(self.customer, self.store)
        #Plan sin digital_card -> 403.
        plan_plain  =   _plan(self.store, name = 'Básico', has_digital_card = False,
                              has_free_shipping = False, has_exclusive_access = False,
                              has_exclusive_discounts = False, discount_percent = Decimal('0'))
        _active_subscription(membership, plan_plain)
        self.assertEqual(self.client.get(url).status_code, 403)
        #Con digital_card -> 200 con payload mínimo.
        StoreSubscription.objects.all().delete()
        _active_subscription(membership, self.plan)
        response    =   self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['member_name'], 'María P.')
        self.assertEqual(response.data['plan_name'], 'Plan socio')
        self.assertEqual(response.data['store_slug'], 'tienda-c')
        self.assertNotIn('email', str(response.data).lower())

    def test_public_card_by_token_minimal_and_unguessable(self):
        membership  =   _membership(self.customer, self.store)
        sub         =   _active_subscription(membership, self.plan)
        url         =   PUBLIC_CARD.format(slug = 'tienda-c', token = sub.public_token)
        anon        =   APIClient()
        response    =   anon.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['member_name'], 'María P.')
        self.assertIn('digital_card', response.data['benefits'])
        #Token inventado -> 404 (no enumerable).
        self.assertEqual(anon.get(PUBLIC_CARD.format(slug = 'tienda-c', token = 'token-falso-123')).status_code, 404)
        #Token válido de OTRA tienda -> 404.
        self.assertEqual(anon.get(PUBLIC_CARD.format(slug = 'tienda-otra', token = sub.public_token)).status_code, 404)

    def test_public_card_404_when_expired_or_no_card_benefit(self):
        membership  =   _membership(self.customer, self.store)
        sub         =   _active_subscription(membership, self.plan, days = -1)
        anon        =   APIClient()
        self.assertEqual(anon.get(PUBLIC_CARD.format(slug = 'tienda-c', token = sub.public_token)).status_code, 404)
        #Vigente pero plan sin digital_card -> 404.
        StoreSubscription.objects.all().delete()
        plan_plain  =   _plan(self.store, name = 'Básico', has_digital_card = False,
                              has_free_shipping = False, has_exclusive_access = False,
                              has_exclusive_discounts = False, discount_percent = Decimal('0'))
        sub2        =   _active_subscription(membership, plan_plain)
        self.assertEqual(anon.get(PUBLIC_CARD.format(slug = 'tienda-c', token = sub2.public_token)).status_code, 404)


class ExclusiveCatalogTests(TestCase):
    """Enforcement de Product.is_exclusive en el catálogo público."""

    def setUp(self):
        cache.clear()
        self.client_owner, self.store   =   _owner('duenio-x', 'tienda-x', has_product_comments = True)
        StoreCustomization.objects.create(store = self.store, show_reviews = True, show_comments = True)
        self.normal     =   Product.objects.create(store = self.store, name = 'Normal', price = Decimal('10'), is_active = True)
        self.exclusive  =   Product.objects.create(store = self.store, name = 'Exclusivo', price = Decimal('20'), is_active = True, is_exclusive = True)
        self.customer   =   _customer()
        self.client     =   _customer_client(self.customer)
        self.anon       =   APIClient()

    def _catalog_ids(self, response):
        return {item['id'] for item in response.data['products']}

    def test_anonymous_catalog_hides_exclusive(self):
        response    =   self.anon.get(PUBLIC_CATALOG.format(slug = 'tienda-x'))
        self.assertEqual(response.status_code, 200, response.data)
        ids         =   self._catalog_ids(response)
        self.assertIn(self.normal.pk, ids)
        self.assertNotIn(self.exclusive.pk, ids)

    def test_exclusive_endpoint_requires_auth_and_access(self):
        url         =   EXCLUSIVE_URL.format(slug = 'tienda-x')
        self.assertEqual(self.anon.get(url).status_code, 401)
        #Customer sin membresía/acceso -> 404 (ni se revela que existe).
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_member_sees_exclusive_products(self):
        plan        =   _plan(self.store, has_exclusive_access = True,
                              has_free_shipping = False, has_digital_card = False,
                              has_exclusive_discounts = False, discount_percent = Decimal('0'))
        membership  =   _membership(self.customer, self.store)
        _active_subscription(membership, plan)
        response    =   self.client.get(EXCLUSIVE_URL.format(slug = 'tienda-x'))
        self.assertEqual(response.status_code, 200, response.data)
        ids         =   {item['id'] for item in response.data['products']}
        self.assertEqual(ids, {self.exclusive.pk})
        #El anónimo sigue sin verlo en la vidriera.
        self.assertNotIn(self.exclusive.pk, self._catalog_ids(self.anon.get(PUBLIC_CATALOG.format(slug = 'tienda-x'))))

    def test_member_without_access_gets_404(self):
        #Membresía activa pero plan SIN exclusive_access -> 404.
        plan        =   _plan(self.store, name = 'Solo tarjeta', has_exclusive_access = False,
                              has_free_shipping = False, has_digital_card = True,
                              has_exclusive_discounts = False, discount_percent = Decimal('0'))
        _active_subscription(_membership(self.customer, self.store), plan)
        self.assertEqual(self.client.get(EXCLUSIVE_URL.format(slug = 'tienda-x')).status_code, 404)

    def test_exclusive_product_reviews_404_for_anonymous(self):
        #Las reviews del exclusivo no se sirven: el endpoint es anónimo.
        self.assertEqual(
            self.anon.get(PUBLIC_REVIEWS.format(slug = 'tienda-x', pid = self.exclusive.pk)).status_code, 404,
        )
        #El producto normal sí (lista vacía, 200).
        response    =   self.anon.get(PUBLIC_REVIEWS.format(slug = 'tienda-x', pid = self.normal.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
