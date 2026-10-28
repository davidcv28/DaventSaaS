"""
Tests de retención de datos personales (Ley 25.326) del comando
`purge_personal_data`: review.email se anonimiza y el chat viejo se borra
con su adjunto; los datos fiscales/de cobro no se tocan.
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from AdminApp.domains.users.models import UserProfile

STRONG_PASSWORD = 'Xq7#mPvL9bT'


class PurgePersonalDataTests(TestCase):
    """Retención: review.email se anonimiza y el chat viejo se borra con su
    adjunto; los datos fiscales/de cobro quedan intactos."""

    def setUp(self):
        from AdminApp.domains.chat.models import ChatMessage, ChatThread
        from StoreApp.domains.catalog.models import Product, ProductReview
        from StoreApp.domains.stores.models import Store
        self.user       =   User.objects.create_user(username = 'purga', email = 'purga@gmail.com', password = STRONG_PASSWORD)
        self.profile    =   UserProfile.objects.create(user = self.user)
        self.store      =   Store.objects.create(user = self.profile, slug = 'purga')
        product         =   Product.objects.create(store = self.store, name = 'Prod')
        self.review     =   ProductReview.objects.create(store = self.store, product = product, name = 'A', surname = 'B', email = 'viejo@mail.com', text = 'ok')
        self.thread     =   ChatThread.objects.create(customer = self.user)
        self.old_msg    =   ChatMessage.objects.create(thread = self.thread, sender = self.user, body = 'viejo', image_key = 'chat/1/old.webp')
        self.new_msg    =   ChatMessage.objects.create(thread = self.thread, sender = self.user, body = 'nuevo')
        old             =   timezone.now() - timedelta(days = 400)
        ProductReview.objects.filter(pk = self.review.pk).update(created_at = old)
        ChatMessage.objects.filter(pk = self.old_msg.pk).update(created_at = old)

    def _run(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out     =   StringIO()
        with patch('AdminApp.domains.users.management.commands.purge_personal_data.storage.storage_configured', return_value = False), \
             patch('AdminApp.domains.users.management.commands.purge_personal_data.default_storage.exists', return_value = True), \
             patch('AdminApp.domains.users.management.commands.purge_personal_data.default_storage.delete') as delete:
            call_command('purge_personal_data', *args, stdout = out)
        return out.getvalue(), delete

    def test_dry_run_changes_nothing(self):
        out, _      =   self._run('--days', '365', '--dry-run')
        self.assertIn('[dry-run] 1 review.email', out)
        self.review.refresh_from_db()
        self.assertEqual(self.review.email, 'viejo@mail.com')
        self.assertTrue(self.__class__.objects_ok(self))

    @staticmethod
    def objects_ok(test):
        from AdminApp.domains.chat.models import ChatMessage
        return ChatMessage.objects.filter(pk = test.old_msg.pk).exists()

    def test_purge_anonymizes_email_and_deletes_old_chat(self):
        from AdminApp.domains.chat.models import ChatMessage
        out, delete  =   self._run('--days', '365')
        self.assertIn('1 review.email', out)
        self.assertIn('1 mensajes de chat', out)
        self.review.refresh_from_db()
        self.assertEqual(self.review.email, '')
        self.assertFalse(ChatMessage.objects.filter(pk = self.old_msg.pk).exists())
        self.assertTrue(ChatMessage.objects.filter(pk = self.new_msg.pk).exists())
        delete.assert_called_once_with('chat/1/old.webp')
        #Idempotente: la segunda corrida no encuentra nada.
        out2, _      =   self._run('--days', '365')
        self.assertIn('0 review.email', out2)
        self.assertIn('0 mensajes de chat', out2)
