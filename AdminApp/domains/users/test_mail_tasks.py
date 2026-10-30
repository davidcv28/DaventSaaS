"""
Tests de correos fuera del request (auditoría 30/10/2026, bloque 3).

Con broker configurado los services solo encolan (`.delay`): el request no
espera SMTP. La task hace el envío real y es la que llena `mail.outbox`.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.users.tasks import (
    send_contact_email,
    send_password_reset_email,
    send_verification_email,
)
from StoreApp.domains.stores.models import Store, StoreCustomization
from StoreApp.domains.stores.services.contact import send_contact_message

PASSWORD = 'Xq7#mP2vL9bT'


def _user(username = 'cliente'):
    return User.objects.create_user(username = username, email = f'{username}@example.com', password = PASSWORD)


class MailTaskTests(TestCase):
    def setUp(self):
        mail.outbox.clear()

    @override_settings(CELERY_TASK_ALWAYS_EAGER = False)
    def test_password_reset_request_only_enqueues(self):
        user    =   _user()
        with patch('AdminApp.domains.users.tasks.send_password_reset_email.delay') as delay:
            self.client.post('/api/password-reset/', {'email': user.email}, format = 'json')
        self.assertEqual(mail.outbox, [])
        delay.assert_called_once_with(user.pk)

    def test_password_reset_task_sends_mail(self):
        user    =   _user()
        send_password_reset_email(user.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Restablecé', mail.outbox[0].subject)

    @override_settings(CELERY_TASK_ALWAYS_EAGER = False)
    def test_resend_endpoint_only_enqueues(self):
        user    =   _user()
        client  =   APIClient()
        client.force_authenticate(user = user)
        with patch('AdminApp.domains.users.tasks.send_verification_email.delay') as delay:
            response    =   client.post('/api/verify-email/resend/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mail.outbox, [])
        delay.assert_called_once_with(user.pk)

    def test_verification_task_sends_mail(self):
        user    =   _user()
        send_verification_email(user.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verificá', mail.outbox[0].subject)


class ContactMailTaskTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        user        =   _user('duenio')
        profile     =   UserProfile.objects.create(user = user, phone = '1100000099')
        self.store  =   Store.objects.create(user = profile, slug = 'mi-tienda')
        StoreCustomization.objects.create(store = self.store, display_name = 'Mi Tienda')

    def test_contact_message_only_enqueues(self):
        with patch('AdminApp.domains.users.tasks.send_contact_email.delay') as delay:
            sent    =   send_contact_message(self.store, name = 'Ana', email = 'ana@example.com', message = 'Hola')
        self.assertTrue(sent)
        self.assertEqual(mail.outbox, [])
        delay.assert_called_once()

    def test_contact_task_sends_mail(self):
        send_contact_email(self.store.pk, 'Ana', 'ana@example.com', 'Hola')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Mi Tienda', mail.outbox[0].subject)
