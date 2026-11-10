"""
Tests del dominio support (e-commerce DAVENT — track G, Ola 2).

Cobertura (PROMPT_MAESTRO §3.5 + spec de la ola):
- API comprador: auth requerida, alta de hilo (tienda publicada/no
  bloqueada, order_token propio de ESA tienda — anti-IDOR doble),
  validación de subject/body, bandeja scoped al customer, detalle 404
  ajeno, responder/cerrar, unread_count y marcado de lectura por lado.
- API dueño: bandeja scoped a SU tienda (?status=&unread=), detalle/
  responder/cerrar/reabrir, IDOR → 404, el dueño NO notifica al escribir.
- Notificaciones: mensaje del comprador → Notification 'store_message'
  deduplicada por hilo para el auth.User del dueño + enqueue del email;
  mensaje del dueño → ninguna.
- Throttles presentes en las escrituras.
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from AdminApp.domains.notifications.models import Notification
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.customers.models import Customer
from StoreApp.domains.orders.models import Order
from StoreApp.domains.stores.models import Store
from StoreApp.domains.support.models import SupportMessage, SupportThread
from StoreApp.domains.support.services import create_thread, post_message
from StoreApp.domains.support.views.customer import (
    SupportMessageThrottle,
    SupportThreadCreateThrottle,
)
from StoreApp.domains.support.views.owner import SupportOwnerWriteThrottle

THREADS_URL       =   '/api/support/threads/'
OWNER_THREADS_URL =   '/api/store-support/threads/'


def _make_owner(username):
    user    =   User.objects.create_user(username = username, email = f'{username}@example.com', password = 'x')
    profile =   UserProfile.objects.create(user = user)
    return profile


def _make_store(slug, *, published = True, blocked = False):
    profile =   _make_owner(f'owner-{slug}')
    return Store.objects.create(user = profile, slug = slug, is_published = published, is_blocked = blocked)


def _make_customer(email = 'ana@example.com', first_name = 'Ana', last_name = 'Perez'):
    customer    =   Customer(email = email, first_name = first_name, last_name = last_name)
    customer.set_password('Comprador#2026')
    customer.save()
    return customer


def _bearer(client, customer):
    from StoreApp.domains.customers.services.tokens import issue_customer_tokens
    access, _refresh =   issue_customer_tokens(customer)
    client.credentials(HTTP_AUTHORIZATION = f'Bearer {access}')
    return access


def _owner_bearer(client, profile):
    token   =   RefreshToken.for_user(profile.user)
    client.credentials(HTTP_AUTHORIZATION = f'Bearer {token.access_token}')


def _make_order(store, customer, tracking = 'tok-publico-1', number = 1):
    return Order.objects.create(
        store           =   store,
        number          =   number,
        tracking_token  =   tracking,
        customer        =   customer,
        payment_method  =   Order.PaymentMethod.TRANSFER,
        expires_at      =   timezone.now() + timedelta(hours = 48),
    )


def _create_thread_via_api(client, store, **extra):
    payload =   {'store': store.slug, 'subject': 'Consulta por mi pedido', 'body': 'Hola, ¿me ayudan con el envío?'}
    payload.update(extra)
    return client.post(THREADS_URL, payload, format = 'json')


class CustomerSupportApiTests(TestCase):
    client_class    =   APIClient

    def setUp(self):
        cache.clear()
        self.store      =   _make_store('mitienda')
        self.store_b    =   _make_store('otratienda')
        self.customer   =   _make_customer()
        self.other      =   _make_customer('bob@example.com', 'Bob', 'Gomez')
        self.client     =   APIClient()
        _bearer(self.client, self.customer)
        self.order      =   _make_order(self.store, self.customer)

    #AUTH + THROTTLE
    def test_requires_customer_auth(self):
        anon    =   APIClient()
        self.assertIn(anon.get(THREADS_URL).status_code, (401, 403))
        self.assertIn(anon.post(THREADS_URL, {'store': 'mitienda', 'subject': 'x', 'body': 'y'}, format = 'json').status_code, (401, 403))
        #Un JWT DAVENT del dueño TAMPOCO autentica como comprador.
        owner_client   =   APIClient()
        _owner_bearer(owner_client, self.store.user)
        self.assertIn(owner_client.get(THREADS_URL).status_code, (401, 403))

    def test_throttle_classes_present(self):
        self.assertTrue(SupportThreadCreateThrottle.rate)
        self.assertTrue(SupportMessageThrottle.rate)
        self.assertTrue(SupportOwnerWriteThrottle.rate)

    #CREATE THREAD
    def test_create_thread_happy_path(self):
        with patch('StoreApp.domains.support.services.services.enqueue_support_email') as mock_mail:
            response    =   _create_thread_via_api(self.client, self.store)
        self.assertEqual(response.status_code, 201)
        data        =   response.json()
        self.assertEqual(data['subject'], 'Consulta por mi pedido')
        self.assertEqual(data['status'], 'open')
        self.assertEqual(data['store']['slug'], 'mitienda')
        self.assertEqual(data['unread_count'], 0)
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['sender'], 'customer')
        thread  =   SupportThread.objects.get(pk = data['id'])
        self.assertEqual(thread.customer_id, self.customer.pk)
        self.assertEqual(thread.store_id, self.store.pk)
        self.assertEqual(thread.messages.count(), 1)
        mock_mail.assert_called_once()

    def test_create_thread_with_own_order_token(self):
        response    =   _create_thread_via_api(self.client, self.store, order_token = 'tok-publico-1')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['order']['code'], 'PED-0001')
        thread  =   SupportThread.objects.get(pk = response.json()['id'])
        self.assertEqual(thread.order_id, self.order.pk)

    def test_create_thread_rejects_foreign_order_token(self):
        #Pedido de OTRO comprador en la misma tienda.
        foreign_customer   =   _make_customer('c@example.com')
        foreign_order      =   _make_order(self.store, foreign_customer, tracking = 'tok-ajeno', number = 2)
        response    =   _create_thread_via_api(self.client, self.store, order_token = foreign_order.tracking_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('order_token', response.json())
        #Pedido del MISMO comprador pero en OTRA tienda.
        other_store_order  =   _make_order(self.store_b, self.customer, tracking = 'tok-tienda-b', number = 1)
        response    =   _create_thread_via_api(self.client, self.store, order_token = other_store_order.tracking_token)
        self.assertEqual(response.status_code, 400)
        #Token inventado.
        response    =   _create_thread_via_api(self.client, self.store, order_token = 'no-existe')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SupportThread.objects.exists())

    def test_create_thread_store_gates(self):
        draft   =   _make_store('borrador', published = False)
        blocked =   _make_store('bloqueada', blocked = True)
        for store in (draft, blocked):
            response    =   _create_thread_via_api(self.client, store)
            self.assertEqual(response.status_code, 404, store.slug)
        #Slug inexistente también es 404.
        response    =   self.client.post(THREADS_URL, {'store': 'fantasma', 'subject': 'ok', 'body': 'hola'}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_create_thread_validation(self):
        for payload in (
            {'store': 'mitienda', 'subject': '', 'body': 'hola'},
            {'store': 'mitienda', 'subject': '   ', 'body': 'hola'},
            {'store': 'mitienda', 'subject': 'x' * 141, 'body': 'hola'},
            {'store': 'mitienda', 'subject': 'ok', 'body': ''},
            {'store': 'mitienda', 'subject': 'ok', 'body': 'x' * 2001},
        ):
            response    =   self.client.post(THREADS_URL, payload, format = 'json')
            self.assertEqual(response.status_code, 400, payload)
        self.assertFalse(SupportThread.objects.exists())
        #Mass assignment: status/store_id/customer inyectados se ignoran.
        response    =   self.client.post(THREADS_URL, {
            'store': 'mitienda', 'subject': 'ok', 'body': 'hola',
            'status': 'closed', 'customer': self.other.pk, 'store_id': self.store_b.pk,
        }, format = 'json')
        self.assertEqual(response.status_code, 201)
        thread  =   SupportThread.objects.get(pk = response.json()['id'])
        self.assertEqual(thread.status, 'open')
        self.assertEqual(thread.customer_id, self.customer.pk)
        self.assertEqual(thread.store_id, self.store.pk)

    #LIST + DETAIL (IDOR)
    def _seed_thread(self, customer = None, store = None):
        return create_thread(
            customer    =   customer or self.customer,
            store       =   store or self.store,
            subject     =   'Mi consulta',
            body        =   'Mensaje inicial',
        )

    def test_list_scoped_to_customer(self):
        mine    =   self._seed_thread()
        self._seed_thread(customer = self.other)
        response    =   self.client.get(THREADS_URL)
        self.assertEqual(response.status_code, 200)
        rows    =   response.json().get('results', response.json())
        self.assertEqual({row['id'] for row in rows}, {mine.pk})
        row     =   rows[0]
        self.assertEqual(row['store']['slug'], 'mitienda')
        self.assertEqual(row['store']['name'], 'mitienda')   # sin customization → slug

    def test_detail_and_reply_idor_404(self):
        foreign =   self._seed_thread(customer = self.other)
        self.assertEqual(self.client.get(f'{THREADS_URL}{foreign.pk}/').status_code, 404)
        self.assertEqual(
            self.client.post(f'{THREADS_URL}{foreign.pk}/messages/', {'body': 'hola'}, format = 'json').status_code,
            404,
        )
        self.assertEqual(self.client.post(f'{THREADS_URL}{foreign.pk}/close/', {}, format = 'json').status_code, 404)

    #MESSAGES + READ STATE
    def test_reply_and_unread_flow(self):
        thread  =   self._seed_thread()
        owner_user  =   self.store.user.user
        #El dueño responde desde el service (mismo camino que la vista).
        with patch('StoreApp.domains.support.services.services.enqueue_support_email') as mock_mail:
            post =   post_message(thread, sender = SupportMessage.Sender.OWNER, body = 'Respuesta del dueño')
        mock_mail.assert_not_called()      # el dueño no dispara email
        #Lista del comprador: 1 no leído (mensaje del dueño).
        rows    =   self.client.get(THREADS_URL).json().get('results', [])
        self.assertEqual(rows[0]['unread_count'], 1)
        #Detalle: marca read_by_customer_at y baja el contador.
        detail  =   self.client.get(f'{THREADS_URL}{thread.pk}/')
        self.assertEqual(detail.status_code, 200)
        msgs    =   detail.json()['messages']
        self.assertEqual([m['sender'] for m in msgs], ['customer', 'owner'])
        post.refresh_from_db()
        self.assertIsNotNone(post.read_by_customer_at)
        rows    =   self.client.get(THREADS_URL).json().get('results', [])
        self.assertEqual(rows[0]['unread_count'], 0)
        #Y la NOTIFICACIÓN del dueño quedó deduplicada por hilo.
        notif   =   Notification.objects.get(user = owner_user, kind = 'store_message')
        self.assertEqual(notif.dedupe_key, f'support:{thread.pk}')
        self.assertEqual(notif.target, 'support')
        self.assertIn('Mi consulta', notif.body)

    def test_customer_reply_endpoint_and_closed(self):
        thread  =   self._seed_thread()
        with patch('StoreApp.domains.support.services.services.enqueue_support_email') as mock_mail:
            response    =   self.client.post(f'{THREADS_URL}{thread.pk}/messages/', {'body': 'Otra consulta'}, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['sender'], 'customer')
        mock_mail.assert_called_once()
        #Validación del body.
        for body in ('', '   ', 'x' * 2001):
            bad =   self.client.post(f'{THREADS_URL}{thread.pk}/messages/', {'body': body}, format = 'json')
            self.assertEqual(bad.status_code, 400, body)
        #Cerrar → responder da 400; el cliente NO puede reabrir (no hay endpoint).
        close   =   self.client.post(f'{THREADS_URL}{thread.pk}/close/', {}, format = 'json')
        self.assertEqual(close.status_code, 200)
        thread.refresh_from_db()
        self.assertEqual(thread.status, 'closed')
        reply   =   self.client.post(f'{THREADS_URL}{thread.pk}/messages/', {'body': 'sigo'}, format = 'json')
        self.assertEqual(reply.status_code, 400)
        reopen  =   self.client.post(f'{THREADS_URL}{thread.pk}/reopen/', {}, format = 'json')
        self.assertEqual(reopen.status_code, 404)      # ruta inexistente para el comprador


class OwnerSupportApiTests(TestCase):
    client_class    =   APIClient

    def setUp(self):
        cache.clear()
        self.owner_a    =   _make_owner('duenio-a')
        self.owner_b    =   _make_owner('duenio-b')
        self.store_a    =   _make_store('tienda-a')
        self.store_b    =   _make_store('tienda-b')
        self.store_a.user   =   self.owner_a
        self.store_a.save()
        self.store_b.user   =   self.owner_b
        self.store_b.save()
        self.customer   =   _make_customer()
        self.thread_a   =   self._seed(self.store_a)
        self.thread_b   =   self._seed(self.store_b)
        self.client     =   APIClient()
        _owner_bearer(self.client, self.owner_a)

    def _seed(self, store):
        return create_thread(customer = self.customer, store = store, subject = f'Hilo {store.slug}', body = 'hola')

    #LIST + FILTERS
    def test_owner_sees_only_own_threads(self):
        response    =   self.client.get(OWNER_THREADS_URL)
        self.assertEqual(response.status_code, 200)
        rows    =   response.json().get('results', response.json())
        self.assertEqual({row['id'] for row in rows}, {self.thread_a.pk})
        row     =   rows[0]
        self.assertEqual(row['customer']['email'], 'ana@example.com')
        self.assertEqual(row['customer']['name'], 'Ana Perez')
        self.assertEqual(row['unread_count'], 1)       # el mensaje del comprador sin leer

    def test_owner_filters_status_and_unread(self):
        self.client.post(f'{OWNER_THREADS_URL}{self.thread_a.pk}/close/', {}, format = 'json')
        rows    =   self.client.get(f'{OWNER_THREADS_URL}?status=closed').json().get('results', [])
        self.assertEqual({r['id'] for r in rows}, {self.thread_a.pk})
        rows    =   self.client.get(f'{OWNER_THREADS_URL}?status=open').json().get('results', [])
        self.assertEqual(rows, [])
        rows    =   self.client.get(f'{OWNER_THREADS_URL}?unread=1').json().get('results', [])
        self.assertEqual({r['id'] for r in rows}, {self.thread_a.pk})
        #Leer el detalle marca leído → unread=1 ya no lo lista.
        self.client.get(f'{OWNER_THREADS_URL}{self.thread_a.pk}/')
        rows    =   self.client.get(f'{OWNER_THREADS_URL}?unread=1').json().get('results', [])
        self.assertEqual(rows, [])

    def test_owner_idor_404(self):
        for suffix in ('', 'messages/', 'close/', 'reopen/'):
            url =   f'{OWNER_THREADS_URL}{self.thread_b.pk}/{suffix}'
            if suffix == 'messages/':
                response    =   self.client.post(url, {'body': 'hola'}, format = 'json')
            else:
                response    =   self.client.post(url, {}, format = 'json') if suffix else self.client.get(url)
            self.assertEqual(response.status_code, 404, suffix)

    #REPLY + LIFECYCLE
    def test_owner_reply_and_lifecycle(self):
        #Responder notifica a NADIE (el dueño ya está en su panel).
        before  =   Notification.objects.filter(user = self.owner_a.user).count()
        with patch('StoreApp.domains.support.services.services.enqueue_support_email') as mock_mail:
            response    =   self.client.post(f'{OWNER_THREADS_URL}{self.thread_a.pk}/messages/', {'body': 'Respuesta'}, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['sender'], 'owner')
        mock_mail.assert_not_called()
        self.assertEqual(Notification.objects.filter(user = self.owner_a.user).count(), before)
        #Hilo cerrado → responder 400; reopen → open; responder OK.
        self.client.post(f'{OWNER_THREADS_URL}{self.thread_a.pk}/close/', {}, format = 'json')
        response    =   self.client.post(f'{OWNER_THREADS_URL}{self.thread_a.pk}/messages/', {'body': 'tarde'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.client.post(f'{OWNER_THREADS_URL}{self.thread_a.pk}/reopen/', {}, format = 'json')
        self.thread_a.refresh_from_db()
        self.assertEqual(self.thread_a.status, 'open')
        response    =   self.client.post(f'{OWNER_THREADS_URL}{self.thread_a.pk}/messages/', {'body': 'ahora sí'}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_owner_without_store_gets_404(self):
        lonely  =   _make_owner('sin-tienda')
        client  =   APIClient()
        _owner_bearer(client, lonely)
        self.assertEqual(client.get(OWNER_THREADS_URL).status_code, 404)


class SupportNotificationTests(TestCase):
    """Aviso al dueño: un solo Notification por hilo, se re-aviva."""

    def setUp(self):
        cache.clear()
        self.store      =   _make_store('mitienda')
        self.customer   =   _make_customer()

    def test_customer_message_notifies_owner_deduped(self):
        with patch('StoreApp.domains.support.services.services.enqueue_support_email'):
            thread  =   create_thread(customer = self.customer, store = self.store, subject = 'Ayuda', body = 'uno')
            post_message(thread, sender = SupportMessage.Sender.CUSTOMER, body = 'dos')
            post_message(thread, sender = SupportMessage.Sender.CUSTOMER, body = 'tres')
        owner_user  =   self.store.user.user
        notifs  =   Notification.objects.filter(user = owner_user, kind = Notification.KIND_STORE_MESSAGE)
        self.assertEqual(notifs.count(), 1)                     # dedupe por hilo
        notif   =   notifs.get()
        self.assertEqual(notif.dedupe_key, f'support:{thread.pk}')
        self.assertEqual(notif.target, 'support')
        self.assertIn('tres', notif.body)                       # último mensaje en el body
        #Y el dueño NO genera notificación al responder.
        post_message(thread, sender = SupportMessage.Sender.OWNER, body = 'respuesta')
        self.assertEqual(Notification.objects.filter(user = owner_user).count(), 1)
