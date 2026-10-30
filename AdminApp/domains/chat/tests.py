"""
Tests de seguridad del chat de soporte (dominio chat).

El chat es premium-only (flag has_support_chat del plan) y con dos roles:
el cliente solo ve SU hilo; el staff ve la bandeja completa. La presencia
es un heartbeat que vence — sin heartbeat fresco el usuario aparece
desconectado, nunca es un booleano eterno.
"""
import os
import shutil
import tempfile
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
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
        #El asistente abre el hilo con la primera pregunta de diseño.
        self.assertIsNotNone(response.data['thread'])
        self.assertEqual(len(response.data['messages']), 1)
        self.assertTrue(response.data['messages'][0]['from_staff'])

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
        self.assertEqual(response.data['message']['sender_name'], 'Asistente de diseño')

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
        #Solo los del cliente: el asistente también responde y esos viajan
        #en el mismo incremental.
        bodies      =   [m['body'] for m in response.data['messages'] if not m['from_staff']]
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
        self.assertIsNotNone(ChatMessage.objects.get(body = 'pregunta').read_at)
        #Y la bandeja ya no lo cuenta como pendiente
        response    =   _client(self.staff).get(CHAT_URL)
        self.assertEqual(response.data['threads'][0]['unread'], 0)

    def test_staff_list_shows_unread_and_customer_identity(self):
        _client(self.user).post(CHAT_SEND_URL, {'body': 'hola'}, format = 'json')
        response    =   _client(self.staff).get(CHAT_URL)
        thread      =   response.data['threads'][0]
        self.assertEqual(thread['unread'], 1)
        self.assertEqual(thread['customer']['name'], 'Negocio cliente')
        #El último mensaje es la siguiente pregunta del asistente.
        self.assertTrue(thread['last_message']['from_staff'])


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
                self.assertEqual(m['sender_name'], 'Asistente de diseño')


class ChatAttachmentTests(TestCase):
    """
    Adjuntos de imagen: el archivo NUNCA entra a la DB — se guarda en el
    storage (R2 o MEDIA_ROOT) y la DB solo guarda image_key. En tests el
    bucket queda deshabilitado por patch -> cae al disco (media/ temporal).
    """

    def setUp(self):
        cache.clear()
        self.user, self.profile   =   _make_user('cliente')
        _grant_chat(self.profile)
        self.staff, _             =   _make_user('ayuda', staff = True)
        #Forzamos el fallback a disco para no tocar el bucket real: MEDIA_ROOT
        #temporal + storage_configured=False.
        self.tmp_media            =   tempfile.mkdtemp()
        self.override             =   override_settings(MEDIA_ROOT = self.tmp_media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.tmp_media, True)
        patcher                   =   patch(
            'AdminApp.domains.chat.services.attachments.storage.storage_configured',
            return_value = False,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _png(name = 'captura.png'):
        buf     =   BytesIO()
        Image.new('RGB', (10, 10), 'red').save(buf, format = 'PNG')
        return SimpleUploadedFile(name, buf.getvalue(), content_type = 'image/png')

    def test_customer_sends_image_only_message(self):
        upload      =   self._png()
        response    =   _client(self.user).post(CHAT_SEND_URL, {'image': upload}, format = 'multipart')
        self.assertEqual(response.status_code, 201)
        message     =   response.data['message']
        self.assertEqual(message['body'], '')
        self.assertTrue(message['image_url'])
        #La DB guarda la key; el archivo quedó en disco bajo private/chat/
        #(nginx bloquea /media/private/: solo lo sirve la API autenticada).
        msg_row     =   ChatMessage.objects.get(from_staff = False)
        self.assertTrue(msg_row.image_key.startswith('private/chat/'))
        self.assertTrue(msg_row.image_key.endswith('.webp'))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp_media, msg_row.image_key)))

    def test_staff_receives_and_views_customer_image(self):
        _client(self.user).post(CHAT_SEND_URL, {'image': self._png()}, format = 'multipart')
        thread      =   ChatThread.objects.get()
        response    =   _client(self.staff).get(f'{CHAT_MESSAGES_URL}?thread={thread.id}')
        self.assertEqual(response.status_code, 200)
        msg         =   response.data['messages'][0]
        self.assertTrue(msg['image_url'])
        #El staff también puede responder con imagen en el mismo hilo
        reply       =   _client(self.staff).post(
            CHAT_SEND_URL, {'image': self._png('respuesta.png'), 'thread': thread.id}, format = 'multipart',
        )
        self.assertEqual(reply.status_code, 201)
        self.assertTrue(reply.data['message']['from_staff'])

    def test_attachment_is_served_only_to_thread_participants(self):
        _client(self.user).post(CHAT_SEND_URL, {'image': self._png()}, format = 'multipart')
        msg         =   ChatMessage.objects.get(from_staff = False)
        #El dueño del hilo lo baja por la vista autenticada.
        own         =   _client(self.user).get(f'/api/chat/attachment/{msg.pk}/')
        self.assertEqual(own.status_code, 200)
        #Otro cliente no (404, sin filtrar existencia).
        other, other_profile    =   _make_user('intruso')
        _grant_chat(other_profile)
        self.assertEqual(_client(other).get(f'/api/chat/attachment/{msg.pk}/').status_code, 404)
        #El staff sí.
        self.assertEqual(_client(self.staff).get(f'/api/chat/attachment/{msg.pk}/').status_code, 200)

    def test_non_image_file_rejected(self):
        bad         =   SimpleUploadedFile('virus.exe', b'MZ fake bytes', content_type = 'application/octet-stream')
        response    =   _client(self.user).post(CHAT_SEND_URL, {'image': bad}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ChatMessage.objects.exists())

    def test_oversize_image_rejected_before_reading(self):
        #4 MB + 1: se corta por tamaño antes de decodificar.
        big         =   SimpleUploadedFile('grande.png', b'\x89PNG\r\n\x1a\n' + b'\0' * (4 * 1024 * 1024), content_type = 'image/png')
        response    =   _client(self.user).post(CHAT_SEND_URL, {'image': big}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('MB', str(response.data['image'][0]))
        self.assertFalse(ChatMessage.objects.exists())

    def test_declared_image_without_real_signature_rejected(self):
        #content_type mentiroso: el cuerpo no es una imagen -> firma real falla.
        fake        =   SimpleUploadedFile('foto.png', b'<script>alert(1)</script>', content_type = 'image/png')
        response    =   _client(self.user).post(CHAT_SEND_URL, {'image': fake}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ChatMessage.objects.exists())

    def test_truncated_image_with_valid_header_rejected_by_decoder(self):
        #Firma PNG válida + cuerpo corrupto: la revalidación con Pillow es la
        #que corta (no alcanza con mirar los primeros bytes).
        truncated   =   SimpleUploadedFile('rota.png', b'\x89PNG\r\n\x1a\n' + b'garbage', content_type = 'image/png')
        response    =   _client(self.user).post(CHAT_SEND_URL, {'image': truncated}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ChatMessage.objects.exists())

    def test_text_plus_image_same_message(self):
        response    =   _client(self.user).post(
            CHAT_SEND_URL, {'body': 'mirá esta captura', 'image': self._png()}, format = 'multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['message']['body'], 'mirá esta captura')
        self.assertTrue(response.data['message']['image_url'])


@override_settings(AI_PROVIDER = '', ANTHROPIC_API_KEY = '', GEMINI_API_KEY = '', GROQ_API_KEY = '', OPENROUTER_API_KEY = '')
class ChatDesignBotTests(TestCase):
    """El chat de soporte ahora es un asistente de diseño que entrevista."""

    def setUp(self):
        cache.clear()
        self.user, self.profile =   _make_user('disenante')
        _grant_chat(self.profile)

    def test_opening_asks_first_design_question(self):
        response    =   _client(self.user).get(CHAT_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['messages']), 1)
        self.assertIn('qué vendés', response.data['messages'][0]['body'])
        self.assertTrue(response.data['messages'][0]['from_staff'])

    def test_each_answer_advances_the_interview(self):
        client      =   _client(self.user)
        client.get(CHAT_URL)
        client.post(CHAT_SEND_URL, {'body': 'Vendo ropa urbana'}, format = 'json')
        thread      =   ChatThread.objects.get(customer = self.user)
        bot_bodies  =   list(thread.messages.filter(from_staff = True).values_list('body', flat = True))
        self.assertEqual(len(bot_bodies), 2)
        self.assertIn('objetivo principal', bot_bodies[-1])

    def test_after_interview_recommends_a_style(self):
        client      =   _client(self.user)
        answers     =   ['ropa', 'vender online', 'jóvenes', 'premium', 'negro', 'productos', 'fotos', 'whatsapp', 'midominio.com', 'sí, ese']
        for answer in answers:
            client.post(CHAT_SEND_URL, {'body': answer}, format = 'json')
        thread      =   ChatThread.objects.get(customer = self.user)
        last        =   thread.messages.filter(from_staff = True).order_by('-created_at').first()
        self.assertIn('estilo', last.body.lower())
