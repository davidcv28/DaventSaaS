"""
Tests de seguridad del chat de soporte (dominio chat).

El chat es premium-only (flag has_support_chat del plan) y con dos roles:
el cliente solo ve SU hilo; el staff ve la bandeja completa. La presencia
es un heartbeat que vence — sin heartbeat fresco el usuario aparece
desconectado, nunca es un booleano eterno.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.chat.models import ChatMessage, ChatPresence, ChatThread
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

CHAT_URL            =   '/api/chat/'
CHAT_MESSAGES_URL   =   '/api/chat/messages/'
CHAT_SEND_URL       =   '/api/chat/send/'
CHAT_HEARTBEAT_URL  =   '/api/chat/heartbeat/'


def _make_user(username, staff = False):
    user        =   User.objects.create_user(
        username    =   username,
        email       =   f'{username}@gmail.com',
        password    =   'Xq7#mP2vL9bT',
        is_staff    =   staff,
    )
    profile     =   UserProfile.objects.create(user = user, business_name = f'Negocio {username}')
    return user, profile


def _grant_chat(profile, enabled = True):
    """Plan vigente con el flag has_support_chat en el valor pedido."""
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username}')
    benefit     =   Benefit.objects.get_or_create(
        code        =   'has_support_chat',
        defaults    =   {'label': 'Chat directo con el equipo de soporte', 'kind': Benefit.FLAG},
    )[0]
    PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = enabled)
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )


def _client(user):
    client      =   APIClient()
    client.force_authenticate(user = user)
    return client


class ChatGateTests(TestCase):
    """Gate de acceso: autenticación + flag has_support_chat (premium)."""

    def setUp(self):
        cache.clear()

    def test_anonymous_cannot_access(self):
        for url in (CHAT_URL, CHAT_MESSAGES_URL):
            self.assertEqual(APIClient().get(url).status_code, 401)
        for url in (CHAT_SEND_URL, CHAT_HEARTBEAT_URL):
            self.assertEqual(APIClient().post(url, {}, format = 'json').status_code, 401)

    def test_user_without_benefit_gets_403(self):
        user, _     =   _make_user('freeuser')
        _grant_chat(UserProfile.objects.get(user = user), enabled = False)
        response    =   _client(user).get(CHAT_URL)
        self.assertEqual(response.status_code, 403)
        response    =   _client(user).post(CHAT_SEND_URL, {'body': 'hola'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_user_without_subscription_gets_403(self):
        user, _     =   _make_user('nosub')
        response    =   _client(user).get(CHAT_URL)
        self.assertEqual(response.status_code, 403)

    def test_premium_user_can_access(self):
        user, profile   =   _make_user('premiumuser')
        _grant_chat(profile)
        response    =   _client(user).get(CHAT_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['thread'])

    def test_staff_always_allowed_without_benefit(self):
        staff, _    =   _make_user('staffer', staff = True)
        response    =   _client(staff).get(CHAT_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn('threads', response.data)


class ChatMessagingTests(TestCase):
    """Envío, lectura incremental y ownership del hilo."""

    def setUp(self):
        cache.clear()
        self.user, self.profile   =   _make_user('cliente')
        _grant_chat(self.profile)
        self.staff, _             =   _make_user('ayuda', staff = True)

    def test_customer_send_creates_thread(self):
        response    =   _client(self.user).post(CHAT_SEND_URL, {'body': 'Hola, tengo una duda'}, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['message']['from_staff'])
        thread      =   ChatThread.objects.get()
        self.assertEqual(thread.customer, self.user)

    def test_staff_replies_in_thread(self):
        _client(self.user).post(CHAT_SEND_URL, {'body': 'Hola'}, format = 'json')
        thread      =   ChatThread.objects.get()
        response    =   _client(self.staff).post(CHAT_SEND_URL, {'body': 'Contanos', 'thread': thread.id}, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['message']['from_staff'])
        self.assertEqual(response.data['message']['sender_name'], 'Soporte')

    def test_staff_send_requires_existing_thread(self):
        response    =   _client(self.staff).post(CHAT_SEND_URL, {'body': 'Hola'}, format = 'json')
        self.assertEqual(response.status_code, 404)
        response    =   _client(self.staff).post(CHAT_SEND_URL, {'body': 'Hola', 'thread': 9999}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_customer_cannot_pick_thread_id(self):
        #Si el cliente manda 'thread' lo ignoramos: escribe siempre en SU hilo
        other, other_profile  =   _make_user('otro')
        _grant_chat(other_profile)
        _client(other).post(CHAT_SEND_URL, {'body': 'msg de otro'}, format = 'json')
        other_thread            =   ChatThread.objects.get(customer = other)
        _client(self.user).post(CHAT_SEND_URL, {'body': 'intento en hilo ajeno', 'thread': other_thread.id}, format = 'json')
        #El mensaje cae en el hilo propio, no en el ajeno
        self.assertFalse(other_thread.messages.filter(body = 'intento en hilo ajeno').exists())
        my_thread               =   ChatThread.objects.get(customer = self.user)
        self.assertTrue(my_thread.messages.filter(body = 'intento en hilo ajeno').exists())

    def test_customer_messages_endpoint_returns_own_thread_only(self):
        other, other_profile  =   _make_user('vecino')
        _grant_chat(other_profile)
        _client(other).post(CHAT_SEND_URL, {'body': 'secreto ajeno'}, format = 'json')
        _client(self.user).post(CHAT_SEND_URL, {'body': 'mi mensaje'}, format = 'json')
        #Aunque pida ?thread=<ajeno> el endpoint resuelve el propio
        other_thread            =   ChatThread.objects.get(customer = other)
        response                =   _client(self.user).get(f'{CHAT_MESSAGES_URL}?thread={other_thread.id}')
        self.assertEqual(response.status_code, 200)
        bodies                  =   [m['body'] for m in response.data['messages']]
        self.assertIn('mi mensaje', bodies)
        self.assertNotIn('secreto ajeno', bodies)

    def test_customer_without_thread_gets_404_on_messages(self):
        response    =   _client(self.user).get(CHAT_MESSAGES_URL)
        self.assertEqual(response.status_code, 404)

    def test_incremental_after_returns_only_new(self):
        client      =   _client(self.user)
        client.post(CHAT_SEND_URL, {'body': 'primero'}, format = 'json')
        first       =   ChatMessage.objects.get(body = 'primero')
        client.post(CHAT_SEND_URL, {'body': 'segundo'}, format = 'json')
        response    =   client.get(f'{CHAT_MESSAGES_URL}?after={first.id}')
        bodies      =   [m['body'] for m in response.data['messages']]
        self.assertEqual(bodies, ['segundo'])

    def test_staff_reads_any_thread(self):
        _client(self.user).post(CHAT_SEND_URL, {'body': 'ayuda por favor'}, format = 'json')
        thread      =   ChatThread.objects.get()
        response    =   _client(self.staff).get(f'{CHAT_MESSAGES_URL}?thread={thread.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['messages'][0]['body'], 'ayuda por favor')

    def test_empty_and_oversized_body_rejected(self):
        client      =   _client(self.user)
        self.assertEqual(client.post(CHAT_SEND_URL, {'body': ''}, format = 'json').status_code, 400)
        self.assertEqual(client.post(CHAT_SEND_URL, {'body': '   '}, format = 'json').status_code, 400)
        self.assertEqual(client.post(CHAT_SEND_URL, {'body': 'x' * 2001}, format = 'json').status_code, 400)
        self.assertFalse(ChatMessage.objects.exists())

    def test_reading_marks_counterpart_messages_read(self):
        _client(self.user).post(CHAT_SEND_URL, {'body': 'pregunta'}, format = 'json')
        thread      =   ChatThread.objects.get()
        #El staff abre los mensajes del hilo -> el mensaje del cliente queda leido
        _client(self.staff).get(f'{CHAT_MESSAGES_URL}?thread={thread.id}')
        self.assertIsNotNone(ChatMessage.objects.get().read_at)
        #Y la bandeja ya no lo cuenta como pendiente
        response    =   _client(self.staff).get(CHAT_URL)
        self.assertEqual(response.data['threads'][0]['unread'], 0)

    def test_staff_list_shows_unread_and_customer_identity(self):
        _client(self.user).post(CHAT_SEND_URL, {'body': 'hola'}, format = 'json')
        response    =   _client(self.staff).get(CHAT_URL)
        thread      =   response.data['threads'][0]
        self.assertEqual(thread['unread'], 1)
        self.assertEqual(thread['customer']['name'], 'Negocio cliente')
        self.assertEqual(thread['last_message']['body'], 'hola')


class ChatPresenceTests(TestCase):
    """Presencia por heartbeat con ventana de expiración."""

    def setUp(self):
        cache.clear()
        self.user, self.profile   =   _make_user('conectado')
        _grant_chat(self.profile)
        self.staff, _             =   _make_user('soporte', staff = True)

    def test_heartbeat_makes_user_online(self):
        _client(self.user).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        presence    =   ChatPresence.objects.get(user = self.user)
        self.assertIsNotNone(presence.last_seen)
        #El staff ve al cliente en la lista de conectados
        response    =   _client(self.staff).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        self.assertIn(self.user.id, response.data['online'])

    def test_customer_sees_staff_online_flag(self):
        _client(self.staff).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        response    =   _client(self.user).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        self.assertTrue(response.data['staff_online'])

    def test_presence_expires_without_fresh_heartbeat(self):
        _client(self.staff).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        #last_seen viejo -> desconectado aunque el registro exista
        ChatPresence.objects.filter(user = self.staff).update(
            last_seen = timezone.now() - timedelta(seconds = 300)
        )
        response    =   _client(self.user).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        self.assertFalse(response.data['staff_online'])

    def test_presence_list_excludes_staff_from_customers(self):
        #La lista 'online' del staff solo muestra clientes, no empleados
        _client(self.staff).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        _client(self.user).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        response    =   _client(self.staff).post(CHAT_HEARTBEAT_URL, {}, format = 'json')
        self.assertNotIn(self.staff.id, response.data['online'])
        self.assertIn(self.user.id, response.data['online'])

    def test_customer_payload_never_leaks_staff_identity(self):
        _client(self.user).post(CHAT_SEND_URL, {'body': 'hola'}, format = 'json')
        thread      =   ChatThread.objects.get()
        _client(self.staff).post(CHAT_SEND_URL, {'body': 'respuesta', 'thread': thread.id}, format = 'json')
        response    =   _client(self.user).get(CHAT_URL)
        #Solo llega el flag booleano + mensajes con sender_name 'Soporte':
        #ningun email ni id de empleado.
        self.assertIsInstance(response.data['staff_online'], bool)
        self.assertNotIn('email', str(response.data['messages']))
        for m in response.data['messages']:
            if m['from_staff']:
                self.assertEqual(m['sender_name'], 'Soporte')
