"""
Tests del dominio storeadmin (panel del dueño — Ola 2 e-commerce).

Cobertura:
- Sales summary: agregados en DB, aislamiento por tienda (los números
  de A nunca incluyen pedidos de B), "cobrado" = paid_at+no reembolsado,
  rangos de fecha (default 30d, from/to, validaciones 400), filtros
  payment_method/status.
- Sales daily: un punto por día con ceros en días sin ventas.
- Customers: unión membresía ∪ compradores con pedidos, LTV bruto
  (total_spent solo cobrado de ESTA tienda), q/membership/ordering,
  detalle con últimos pedidos + addresses + membresía, IDOR → 404.
- Export CSV: headers, BOM, Content-Disposition, escape de fórmulas,
  filtros y tope de filas.
- Auth: 401 anónimo en todos los endpoints.
"""
import csv
import io
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.customers.models import (
    Customer,
    CustomerAddress,
    StoreMembership,
)
from StoreApp.domains.memberships.models import StorePlan, StoreSubscription
from StoreApp.domains.orders.models import Order
from StoreApp.domains.stores.models import Store
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit


def _grant(profile, *codes):
    """Plan DAVENT + suscripción vigente de 30 días (reusa la suscripción
    existente si ya tiene una — user es OneToOne)."""
    suscription =   getattr(profile, 'suscription', None)
    plan    =   suscription.plan_suscription if suscription is not None else SuscriptionPlan.objects.create(name = f'Plan {profile.pk}')
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


def _make_owner(username, *, ecommerce = True):
    user    =   User.objects.create_user(username = username, email = f'{username}@example.com', password = 'x')
    profile =   UserProfile.objects.create(user = user)
    #plan_benefits_of cachea por PK y SQLite las reutiliza entre tests.
    cache.delete(f'planben:{profile.pk}')
    if ecommerce:
        _grant(profile, 'has_ecommerce')
    return profile


def _make_store(slug, owner):
    return Store.objects.create(user = owner, slug = slug, is_published = True)


_customer_seq    =   [0]
def _make_customer(email, first_name = 'Ana', last_name = 'Perez'):
    #phone_hash es unique global: cada buyer de la suite necesita el suyo.
    _customer_seq[0] +=   1
    customer    =   Customer(email = email, first_name = first_name, last_name = last_name, phone = f'+549110{_customer_seq[0]:07d}')
    customer.set_password('Comprador#2026')
    customer.save()
    return customer


_seq     =   {}
def _next_number(store):
    _seq[store.pk]  =   _seq.get(store.pk, 0) + 1
    return _seq[store.pk]


def _make_order(store, customer, *, total = '100.00', status = Order.Status.PENDING_PAYMENT,
                payment_method = 'transfer', paid = False, days_ago = 0,
                invoice_ref = '', **extra):
    """Order directo (sin checkout): paid=True → paid_at + estado pago
    realista (PACKING — PAID puro es transitorio por el auto-avance)."""
    if paid and status == Order.Status.PENDING_PAYMENT:
        status  =   Order.Status.PACKING
    order   =   Order.objects.create(
        store               =   store,
        number              =   _next_number(store),
        #uuid: los tokens no pueden colisionar entre tests (unique global).
        tracking_token      =   f'tok-{uuid.uuid4().hex}',
        customer            =   customer,
        customer_first_name =   customer.first_name,
        customer_last_name  =   customer.last_name,
        customer_email      =   customer.email,
        payment_method      =   payment_method,
        status              =   status,
        subtotal            =   Decimal(total),
        total               =   Decimal(total),
        expires_at          =   timezone.now() + timedelta(hours = 48),
        paid_at             =   timezone.now() if paid else None,
        invoice_ref         =   invoice_ref,
        **extra,
    )
    if days_ago:
        #created_at es auto_now_add: se corrige por UPDATE post-create.
        Order.objects.filter(pk = order.pk).update(
            created_at = timezone.now() - timedelta(days = days_ago),
        )
        order.refresh_from_db()
    return order


def _make_membership(customer, store, status = 'active', tags = None):
    return StoreMembership.objects.create(
        customer = customer, store = store, status = status, tags = tags or [],
    )


def _make_subscription(membership, store, plan_name = 'Plan Oro'):
    plan    =   StorePlan.objects.create(store = store, name = plan_name, price = Decimal('500.00'), period = 'monthly')
    now     =   timezone.now()
    return StoreSubscription.objects.create(
        membership      =   membership,
        plan            =   plan,
        status          =   StoreSubscription.STATUS_ACTIVE,
        started_at      =   now,
        vigente_hasta   =   now + timedelta(days = 30),
    )


def _jwt(client, profile):
    token   =   RefreshToken.for_user(profile.user)
    client.credentials(HTTP_AUTHORIZATION = f'Bearer {token.access_token}')
    return client


class _StoreAdminBase(TestCase):
    """Dos tiendas con dueños distintos + un cliente compartido."""
    def setUp(self):
        #El contador de números es por store.pk y persiste entre tests
        #(los sequences de Postgres no vuelven atrás) — se resetea para
        #que los PED-XXXX sean deterministas dentro de cada test.
        _seq.clear()
        self.owner_a    =   _make_owner('duenio-a')
        self.owner_b    =   _make_owner('duenio-b')
        self.store_a    =   _make_store('tienda-a', self.owner_a)
        self.store_b    =   _make_store('tienda-b', self.owner_b)
        self.customer   =   _make_customer('ana@example.com')
        self.client     =   _jwt(APIClient(), self.owner_a)


#=========================================
# SALES SUMMARY
#=========================================
class SalesSummaryTests(_StoreAdminBase):
    def setUp(self):
        super().setUp()
        #Pedidos de la tienda A: 1 cobrado transfer, 1 pendiente whatsapp,
        #1 cobrado viejo (40 días — fuera del default de 30), 1 reembolsado.
        self.o_paid      =   _make_order(self.store_a, self.customer, total = '100.00', paid = True, payment_method = 'transfer')
        self.o_pending   =   _make_order(self.store_a, self.customer, total = '50.00', payment_method = 'whatsapp')
        self.o_old       =   _make_order(self.store_a, self.customer, total = '200.00', paid = True, payment_method = 'mp', days_ago = 40)
        self.o_refunded  =   _make_order(
            self.store_a, self.customer, total = '80.00',
            status = Order.Status.REFUNDED, paid = True, payment_method = 'cash',
        )
        #Y uno de la tienda B que NO debe colarse en los números de A.
        self.o_foreign   =   _make_order(self.store_b, self.customer, total = '999.00', paid = True)
        self.url         =   '/api/store-admin/sales/summary/'

    def test_summary_aggregates_and_store_isolation(self):
        response    =   self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        #Default = últimos 30 días: el pedido de hace 40 días queda afuera.
        self.assertEqual(data['orders_count'], 3)          #paid+pending+refunded
        self.assertEqual(data['cobrado_count'], 1)
        self.assertEqual(data['gross_total'], '100.00')    #solo el cobrado vigente
        self.assertEqual(data['pending_count'], 1)
        self.assertEqual(data['pending_total'], '50.00')
        self.assertEqual(data['refunded_count'], 1)
        self.assertEqual(data['refunded_total'], '80.00')
        self.assertEqual(data['avg_ticket'], '100.00')
        #Aislamiento: el pedido de 999 de la tienda B no aparece en nada.
        self.assertNotIn('999.00', str(data))
        #Cortes por método de pago (shape estable: las 4 opciones).
        self.assertEqual(set(data['by_payment_method']), {'transfer', 'whatsapp', 'cash', 'mp'})
        self.assertEqual(data['by_payment_method']['transfer'],
                         {'orders_count': 1, 'total_cobrado': '100.00', 'total_pendiente': '0.00'})
        self.assertEqual(data['by_payment_method']['whatsapp']['total_pendiente'], '50.00')
        self.assertEqual(data['by_payment_method']['cash']['orders_count'], 1)   #el reembolsado cuenta como pedido
        #Cortes por estado.
        self.assertEqual(data['by_status']['PACKING']['orders_count'], 1)
        self.assertEqual(data['by_status']['PENDING_PAYMENT']['total'], '50.00')
        self.assertEqual(data['by_status']['REFUNDED']['total'], '80.00')
        #Nota de "bruto" para la UI.
        self.assertIn('bruto', data['note'].lower())
        self.assertIn('Mercado Pago', data['note'])

    def test_summary_date_range_includes_old_order(self):
        d_from  =   (timezone.localdate() - timedelta(days = 45)).isoformat()
        d_to    =   timezone.localdate().isoformat()
        data    =   self.client.get(f'{self.url}?from={d_from}&to={d_to}').json()
        self.assertEqual(data['orders_count'], 4)
        self.assertEqual(data['gross_total'], '300.00')    #100 + 200 (el refunded no)
        self.assertEqual(data['cobrado_count'], 2)

    def test_summary_partial_range_is_400(self):
        today   =   timezone.localdate().isoformat()
        self.assertEqual(self.client.get(f'{self.url}?from={today}').status_code, 400)
        self.assertEqual(self.client.get(f'{self.url}?to={today}').status_code, 400)

    def test_summary_invalid_dates_and_range(self):
        self.assertEqual(self.client.get(f'{self.url}?from=nope&to=2025-01-01').status_code, 400)
        self.assertEqual(self.client.get(f'{self.url}?from=2025-02-01&to=2025-01-01').status_code, 400)
        #Rango > 366 días → 400.
        self.assertEqual(self.client.get(f'{self.url}?from=2020-01-01&to=2025-01-01').status_code, 400)

    def test_owner_without_ecommerce_benefit_403(self):
        #Métricas/clientes/CSV: superficie de venta online — un plan sin
        #has_ecommerce responde 403 en los tres endpoints del panel.
        owner   =   _make_owner('duenio-sin-plan', ecommerce = False)
        _make_store('tienda-sin-plan', owner)
        client  =   _jwt(APIClient(), owner)
        self.assertEqual(client.get(self.url).status_code, 403)
        self.assertEqual(client.get('/api/store-admin/sales/daily/').status_code, 403)
        self.assertEqual(client.get('/api/store-admin/sales/export.csv').status_code, 403)
        self.assertEqual(client.get('/api/store-admin/customers/').status_code, 403)

    def test_summary_filters(self):
        #Solo pendientes.
        data    =   self.client.get(f'{self.url}?status=PENDING_PAYMENT').json()
        self.assertEqual(data['orders_count'], 1)
        self.assertEqual(data['pending_total'], '50.00')
        self.assertEqual(data['gross_total'], '0.00')
        #Solo transfer.
        data    =   self.client.get(f'{self.url}?payment_method=transfer').json()
        self.assertEqual(data['orders_count'], 1)
        self.assertEqual(data['gross_total'], '100.00')
        #Filtros inválidos → 400.
        self.assertEqual(self.client.get(f'{self.url}?payment_method=crypto').status_code, 400)
        self.assertEqual(self.client.get(f'{self.url}?status=FOO').status_code, 400)


#=========================================
# SALES DAILY
#=========================================
class SalesDailyTests(_StoreAdminBase):
    def setUp(self):
        super().setUp()
        today   =   timezone.localdate()
        #Pedidos: hoy (cobrado 100), hace 3 días (pendiente 50 + cobrado 25).
        _make_order(self.store_a, self.customer, total = '100.00', paid = True, payment_method = 'transfer')
        for total, paid in (('50.00', False), ('25.00', True)):
            _make_order(self.store_a, self.customer, total = total, paid = paid,
                        payment_method = 'cash', days_ago = 3)
        #Y uno de la tienda B el mismo día — no debe aparecer.
        _make_order(self.store_b, self.customer, total = '777.00', paid = True, days_ago = 3)
        self.url =   '/api/store-admin/sales/daily/'
        self.today  =   today

    def test_daily_series_shape_and_isolation(self):
        data    =   self.client.get(f'{self.url}?days=5').json()
        self.assertEqual(len(data['series']), 5)
        self.assertEqual(data['from'], (self.today - timedelta(days = 4)).isoformat())
        self.assertEqual(data['to'], self.today.isoformat())
        by_date =   {point['date']: point for point in data['series']}
        #Hoy: 1 pedido cobrado.
        today_point  =   by_date[self.today.isoformat()]
        self.assertEqual(today_point['orders_count'], 1)
        self.assertEqual(today_point['total_cobrado'], '100.00')
        self.assertEqual(today_point['total_pendiente'], '0.00')
        #Hace 3 días: 2 pedidos de A (50 pend + 25 cobrado); el de B (777) no está.
        old     =   by_date[(self.today - timedelta(days = 3)).isoformat()]
        self.assertEqual(old['orders_count'], 2)
        self.assertEqual(old['total_cobrado'], '25.00')
        self.assertEqual(old['total_pendiente'], '50.00')
        #Días sin ventas → ceros (serie continua).
        empty   =   by_date[(self.today - timedelta(days = 1)).isoformat()]
        self.assertEqual(empty, {'date': empty['date'], 'orders_count': 0,
                                 'total_cobrado': '0.00', 'total_pendiente': '0.00'})
        self.assertNotIn('777.00', str(data))

    def test_daily_from_to_and_bad_days(self):
        d_from  =   (self.today - timedelta(days = 3)).isoformat()
        d_to    =   self.today.isoformat()
        data    =   self.client.get(f'{self.url}?from={d_from}&to={d_to}').json()
        self.assertEqual(len(data['series']), 4)
        self.assertEqual(self.client.get(f'{self.url}?days=0').status_code, 400)
        self.assertEqual(self.client.get(f'{self.url}?days=abc').status_code, 400)
        self.assertEqual(self.client.get(f'{self.url}?days=9999').status_code, 400)


#=========================================
# CUSTOMERS (lista + detalle)
#=========================================
class StoreAdminCustomerTests(_StoreAdminBase):
    def setUp(self):
        super().setUp()
        #Cliente CON membresía (y plan/suscripción) pero SIN pedidos.
        self.member     =   _make_customer('socio@example.com', 'Socia', 'Mina')
        self.membership  =   _make_membership(self.member, self.store_a, tags = ['vip'])
        self.subscription   =   _make_subscription(self.membership, self.store_a, plan_name = 'Plan Oro')
        #Cliente que SOLO compró (sin membresía): 2 cobrado + 1 pendiente + 1 reembolsado.
        self.buyer      =   _make_customer('comprador@example.com', 'Beto', 'Rios')
        _make_order(self.store_a, self.buyer, total = '100.00', paid = True)
        _make_order(self.store_a, self.buyer, total = '50.00', paid = True, payment_method = 'mp')
        _make_order(self.store_a, self.buyer, total = '30.00')                       #pendiente
        _make_order(self.store_a, self.buyer, total = '70.00',
                    status = Order.Status.REFUNDED, paid = True)                     #reembolsado
        #Pedido del buyer en OTRA tienda: no cuenta para el LTV de A.
        _make_order(self.store_b, self.buyer, total = '999.00', paid = True)
        #Cliente 100% ajeno (solo tienda B).
        self.foreign    =   _make_customer('ajeno@example.com', 'Ajeno', 'Total')
        _make_membership(self.foreign, self.store_b)
        _make_order(self.store_b, self.foreign, total = '10.00', paid = True)
        #Dirección del buyer (para addresses_count del detalle).
        CustomerAddress.objects.create(customer = self.buyer, line1 = 'Calle 1', city = 'CABA', province = 'CABA')
        self.url        =   '/api/store-admin/customers/'

    def _rows(self, response):
        return response.json().get('results', response.json())

    def test_list_unions_members_and_buyers(self):
        response    =   self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body    =   response.json()
        self.assertIn('results', body)      #paginado
        rows    =   {row['id']: row for row in body['results']}
        self.assertIn(self.member.pk, rows)
        self.assertIn(self.buyer.pk, rows)
        self.assertNotIn(self.foreign.pk, rows)
        #Miembro sin pedidos.
        member_row =   rows[self.member.pk]
        self.assertEqual(member_row['membership_status'], 'active')
        self.assertEqual(member_row['plan_name'], 'Plan Oro')
        self.assertIsNotNone(member_row['joined_at'])
        self.assertEqual(member_row['orders_count'], 0)
        self.assertEqual(member_row['total_spent'], '0.00')
        #Comprador sin membresía.
        buyer_row  =   rows[self.buyer.pk]
        self.assertIsNone(buyer_row['membership_status'])
        self.assertIsNone(buyer_row['plan_name'])
        self.assertIsNone(buyer_row['joined_at'])
        #LTV: 100+50 cobrados; el pendiente (30) y el reembolsado (70) no suman;
        #el pedido de 999 en tienda B tampoco.
        self.assertEqual(buyer_row['orders_count'], 4)
        self.assertEqual(buyer_row['total_spent'], '150.00')
        self.assertIsNotNone(buyer_row['last_order_at'])
        self.assertEqual(buyer_row['email'], 'comprador@example.com')
        self.assertEqual(buyer_row['phone'], self.buyer.phone)

    def test_search_q(self):
        data    =   self._rows(self.client.get(f'{self.url}?q=socio'))
        self.assertEqual({row['id'] for row in data}, {self.member.pk})
        data    =   self._rows(self.client.get(f'{self.url}?q=comprador@example.com'))
        self.assertEqual({row['id'] for row in data}, {self.buyer.pk})
        data    =   self._rows(self.client.get(f'{self.url}?q=ajeno'))
        self.assertEqual(data, [])

    def test_membership_filter(self):
        data    =   self._rows(self.client.get(f'{self.url}?membership=active'))
        self.assertEqual({row['id'] for row in data}, {self.member.pk})
        data    =   self._rows(self.client.get(f'{self.url}?membership=none'))
        self.assertEqual({row['id'] for row in data}, {self.buyer.pk})
        #Suspendemos la membresía del member → active ya no lo lista.
        StoreMembership.objects.filter(pk = self.membership.pk).update(status = 'suspended')
        data    =   self._rows(self.client.get(f'{self.url}?membership=active'))
        self.assertEqual(data, [])
        data    =   self._rows(self.client.get(f'{self.url}?membership=suspended'))
        self.assertEqual({row['id'] for row in data}, {self.member.pk})
        self.assertEqual(self.client.get(f'{self.url}?membership=vip').status_code, 400)

    def test_ordering(self):
        data    =   self._rows(self.client.get(f'{self.url}?ordering=-total_spent'))
        self.assertEqual(data[0]['id'], self.buyer.pk)
        data    =   self._rows(self.client.get(f'{self.url}?ordering=joined_at'))
        self.assertEqual(len(data), 2)
        self.assertEqual(self.client.get(f'{self.url}?ordering=password').status_code, 400)

    def test_detail_buyer(self):
        response    =   self.client.get(f'{self.url}{self.buyer.pk}/')
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertEqual(data['id'], self.buyer.pk)
        self.assertEqual(data['total_spent'], '150.00')
        self.assertEqual(data['addresses_count'], 1)
        self.assertIsNone(data['membership'])
        #Últimos pedidos: code/status/total/tracking_token, solo de A.
        self.assertEqual(len(data['last_orders']), 4)
        first   =   data['last_orders'][0]
        self.assertTrue(first['code'].startswith('PED-'))
        self.assertIn('tracking_token', first)
        self.assertIn('status', first)
        #Ningún pedido de la tienda B (el de 999 no está).
        self.assertTrue(all('999' not in str(o['total']) for o in data['last_orders']))
        #Los 4 pedidos de A en store_a son PED-0001..0004.
        codes   =   {o['code'] for o in data['last_orders']}
        self.assertEqual(codes, {f'PED-{n:04d}' for n in (1, 2, 3, 4)})

    def test_detail_member_with_plan(self):
        data    =   self.client.get(f'{self.url}{self.member.pk}/').json()
        self.assertEqual(data['membership']['status'], 'active')
        self.assertEqual(data['membership']['tags'], ['vip'])
        self.assertEqual(data['membership']['plan_name'], 'Plan Oro')
        self.assertEqual(data['membership']['subscription_status'], 'active')
        self.assertTrue(data['membership']['is_vigente'])
        self.assertEqual(data['last_orders'], [])

    def test_idor_foreign_customer_is_404(self):
        #El dueño B no ve al member de A (solo tiene vínculo con A); el
        #buyer SÍ es cliente de B (tiene un pedido de 999 ahí) → 200.
        client_b    =   _jwt(APIClient(), self.owner_b)
        self.assertEqual(client_b.get(f'{self.url}{self.member.pk}/').status_code, 404)
        self.assertEqual(client_b.get(f'{self.url}{self.buyer.pk}/').status_code, 200)
        self.assertEqual(self.client.get(f'{self.url}{self.foreign.pk}/').status_code, 404)
        #Y en el listado de B no aparecen los clientes de A — ojo: el
        #buyer SÍ es cliente de B también (tiene un pedido ahí), así que
        #la lista de B es {foreign, buyer}.
        rows_b  =   {row['id'] for row in client_b.get(self.url).json()['results']}
        self.assertEqual(rows_b, {self.foreign.pk, self.buyer.pk})

    def test_anonymous_is_401(self):
        anon    =   APIClient()
        self.assertEqual(anon.get(self.url).status_code, 401)
        self.assertEqual(anon.get(f'{self.url}{self.buyer.pk}/').status_code, 401)
        self.assertEqual(anon.get('/api/store-admin/sales/summary/').status_code, 401)
        self.assertEqual(anon.get('/api/store-admin/sales/daily/').status_code, 401)
        self.assertEqual(anon.get('/api/store-admin/sales/export.csv').status_code, 401)

    def test_list_no_n_plus_1(self):
        """La página no crece en queries al agregar clientes (prefetch fijo)."""
        def run():
            return self.client.get(self.url)
        run()   #warm
        with CaptureQueriesContext(connection) as ctx1:
            run()
        #3 clientes más con membresía+pedido.
        for i in range(3):
            c   =   _make_customer(f'extra{i}@example.com', f'Extra{i}', 'X')
            _make_membership(c, self.store_a)
            _make_order(self.store_a, c, total = '10.00', paid = True)
        with CaptureQueriesContext(connection) as ctx2:
            run()
        self.assertEqual(len(ctx2), len(ctx1), f'N+1 detectado: {len(ctx1)} → {len(ctx2)} queries')


#=========================================
# EXPORT CSV
#=========================================
class SalesExportTests(_StoreAdminBase):
    def setUp(self):
        super().setUp()
        self.o1 =   _make_order(self.store_a, self.customer, total = '100.00', paid = True,
                                payment_method = 'transfer', invoice_ref = 'A-0001-00000001')
        Order.objects.filter(pk = self.o1.pk).update(
            customer_first_name = '=HYPERLINK("http://evil")',
        )
        self.o1.refresh_from_db()
        self.o2 =   _make_order(self.store_a, self.customer, total = '50.00',
                                payment_method = 'whatsapp', days_ago = 10)
        _make_order(self.store_b, self.customer, total = '999.00', paid = True)     #ajeno
        self.url    =   '/api/store-admin/sales/export.csv'

    def _csv_rows(self, response):
        """Parsea la respuesta CSV (BOM incluido) → lista de filas."""
        body    =   response.content.decode('utf-8')
        self.assertTrue(body.startswith('\ufeff'))
        return list(csv.reader(io.StringIO(body.lstrip('\ufeff'))))

    def test_export_csv_headers_bom_and_rows(self):
        response    =   self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        disposition =   response['Content-Disposition']
        self.assertIn('attachment', disposition)
        self.assertIn('ventas-tienda-a-', disposition)
        self.assertIn('.csv', disposition)
        rows    =   self._csv_rows(response)
        self.assertEqual(rows[0], ['Fecha', 'Pedido', 'Cliente', 'Email', 'Método de pago',
                                   'Estado', 'Subtotal', 'Descuento', 'Envío', 'Total', 'Nº de factura'])
        #Dos pedidos de A (el de B no sale). Orden created_at ASC: el de
        #hace 10 días (PED-0002) va primero, el de hoy (PED-0001) segundo.
        self.assertEqual(len(rows), 3)
        old_row =   rows[1]
        self.assertEqual(old_row[1], 'PED-0002')
        self.assertIn('Coordinar por WhatsApp', old_row[4])
        self.assertIn('Pendiente de pago', old_row[5])
        self.assertEqual(old_row[9], '50.00')
        self.assertEqual(old_row[10], '')
        paid_row    =   rows[2]
        self.assertEqual(paid_row[1], 'PED-0001')
        self.assertIn('Transferencia', paid_row[4])
        self.assertIn('Preparando', paid_row[5])       #PACKING label
        self.assertEqual(paid_row[9], '100.00')
        self.assertEqual(paid_row[10], 'A-0001-00000001')
        #CSV injection: el nombre que empieza con '=' queda neutralizado
        #con apóstrofo inicial (la celda se muestra literal en Excel).
        self.assertTrue(paid_row[2].startswith("'"))
        self.assertIn('HYPERLINK', paid_row[2])

    def test_export_csv_filters(self):
        #Solo transfer → una fila de datos.
        response    =   self.client.get(f'{self.url}?payment_method=transfer')
        rows    =   self._csv_rows(response)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], 'PED-0001')
        #Rango de fechas que excluye el pedido de hace 10 días.
        today   =   timezone.localdate()
        d_from  =   (today - timedelta(days = 2)).isoformat()
        d_to    =   today.isoformat()
        response    =   self.client.get(f'{self.url}?from={d_from}&to={d_to}')
        rows    =   self._csv_rows(response)
        self.assertEqual(len(rows), 2)     #header + solo el de hoy
        self.assertEqual(rows[1][1], 'PED-0001')
        #Estado inválido → 400.
        self.assertEqual(self.client.get(f'{self.url}?status=FOO').status_code, 400)

    def test_export_csv_row_limit(self):
        with patch('StoreApp.domains.storeadmin.services.metrics.EXPORT_MAX_ROWS', 1):
            response    =   self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
