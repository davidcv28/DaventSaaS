"""
Purga de datos personales por retención (Ley 25.326).

Borra/anonymiza lo que ya no hace falta para la relación comercial:

- ``ProductReview.email``: pasado ``--days`` se reemplaza por vacío (la
  opinión y el nombre se conservan; el correo solo servía antispam/moderación).
- ``ChatMessage`` anterior a ``--days``: se borra el mensaje y su adjunto
  (R2 o MEDIA_ROOT). El hilo del cliente se conserva.

Nunca toca datos fiscales ni de cobro (``Payment``, ``Suscription``,
``Invoice``): esos tienen obligación legal de conservación y quedan fuera
del alcance del comando por diseño — no se agregan modelos acá.

Uso:
    manage.py purge_personal_data --days 365 [--dry-run]
"""
import logging
from datetime import timedelta

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from AdminApp.domains.chat.models import ChatMessage
from StoreApp.domains.catalog.models import ProductReview
from StoreApp.domains.stores.services import storage

logger      =   logging.getLogger(__name__)
BATCH_SIZE  =   500


class Command(BaseCommand):
    help = 'Purga review.email y mensajes de chat más viejos que --days (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type = int, default = 365, help = 'Retención en días (default 365).')
        parser.add_argument('--dry-run', action = 'store_true', help = 'Solo cuenta, no borra ni modifica.')

    def handle(self, *args, **options):
        days        =   max(1, options['days'])
        cutoff      =   timezone.now() - timedelta(days = days)
        dry_run     =   options['dry_run']
        reviews     =   ProductReview.objects.filter(created_at__lt = cutoff).exclude(email = '')
        review_count = reviews.count()
        messages    =   ChatMessage.objects.filter(created_at__lt = cutoff)
        chat_count  = messages.count()
        if dry_run:
            self.stdout.write(
                f'[dry-run] {review_count} review.email y {chat_count} mensajes de chat '
                f'con más de {days} días serían purgados.'
            )
            return
        reviews.update(email = '')
        files       =   0
        while True:
            batch   =   list(messages.values_list('id', 'image_key')[:BATCH_SIZE])
            if not batch:
                break
            ids     =   [row[0] for row in batch]
            for _, key in batch:
                if key and self._delete_file(key):
                    files   +=  1
            ChatMessage.objects.filter(id__in = ids).delete()
        logger.info(
            'purge_personal_data: %s review.email anonimizados, %s mensajes de chat borrados, '
            '%s adjuntos eliminados (retención %sd)',
            review_count, chat_count, files, days,
        )
        self.stdout.write(
            f'Purgado: {review_count} review.email · {chat_count} mensajes de chat · '
            f'{files} adjuntos (retención {days} días).'
        )

    @staticmethod
    def _delete_file(key):
        """Borra el adjunto del bucket o de MEDIA_ROOT; True si lo intentó."""
        try:
            if storage.storage_configured():
                storage._delete_object(key)
            elif default_storage.exists(key):
                default_storage.delete(key)
            else:
                return False
            return True
        except Exception:
            logger.warning('purge_personal_data: no se pudo borrar el adjunto %s', key)
            return False
