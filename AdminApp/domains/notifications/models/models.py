from django.conf import settings
from django.db import models
from django.utils import timezone

"""
Modelos del dominio notifications.

Notification: aviso del sistema por usuario — NO es un mensaje de chat:
el click solo marca leído y navega a la sección indicada en `target`
('reviews', 'plans', 'changelog', etc.; '' = solo se lee). Los avisos
recurrentes usan `dedupe_key` para ser UNO solo que se actualiza
(opinión nueva, mensaje del staff, fin de período); los de una sola
vez (cada entrada del changelog) deduplican por su id.

ChangelogEntry: novedades publicadas por el staff; al publicarse se
crea una Notification 'changelog' para cada usuario activo.
"""

#=========================================
# NOTIFICATION MODEL
#=========================================
class Notification(models.Model):
    KIND_REVIEW          =   'review'
    KIND_ADMIN_MESSAGE   =   'admin_message'
    KIND_SUBSCRIPTION    =   'subscription'
    KIND_CHANGELOG       =   'changelog'
    KIND_SYSTEM          =   'system'
    KIND_CHOICES         =   [
        (KIND_REVIEW,         'Opinión recibida'),
        (KIND_ADMIN_MESSAGE,  'Mensaje del equipo'),
        (KIND_SUBSCRIPTION,   'Estado de la suscripción'),
        (KIND_CHANGELOG,      'Novedades'),
        (KIND_SYSTEM,         'Aviso del sistema'),
    ]
    #Un aviso por (usuario, kind, dedupe_key): el mismo evento que se
    #repite actualiza el existente (y lo devuelve a no-leído) en vez de
    #llenar la lista de duplicados.
    user                =   models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'notifications', verbose_name = 'Usuario')
    kind                =   models.CharField(max_length = 20, choices = KIND_CHOICES, db_index = True, verbose_name = 'Tipo')
    dedupe_key          =   models.CharField(max_length = 80, blank = True, default = '', verbose_name = 'Clave de deduplicación')
    title               =   models.CharField(max_length = 200, verbose_name = 'Título')
    body                =   models.CharField(max_length = 500, blank = True, default = '', verbose_name = 'Detalle')
    #Sección del dashboard destino ('' = el click solo marca leído).
    target              =   models.CharField(max_length = 40, blank = True, default = '', verbose_name = 'Destino')
    #null = sin leer; al actualizar un aviso deduplicado vuelve a null.
    read_at             =   models.DateTimeField(null = True, blank = True, verbose_name = 'Leído')
    created_at          =   models.DateTimeField(auto_now_add = True)
    updated_at          =   models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name        =   'Notificación'
        verbose_name_plural =   'Notificaciones'
        ordering            =   ['-created_at', '-id']
        constraints         =   [
            models.UniqueConstraint(fields = ['user', 'kind', 'dedupe_key'], name = 'uniq_notif_user_kind_key'),
        ]
        indexes             =   [
            models.Index(fields = ['user', 'read_at'], name = 'idx_notif_user_read'),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} → {self.user.username}'


#=========================================
# CHANGELOG ENTRY MODEL
#=========================================
class ChangelogEntry(models.Model):
    """
    Novedad publicada por el staff (se escribe desde el admin o el panel
    staff). Al pasar a is_published se avisa a todos los usuarios activos
    con una Notification 'changelog' que apunta a la sección Novedades.
    """
    title               =   models.CharField(max_length = 200, verbose_name = 'Título')
    #Texto plano; el frontend respeta saltos de línea (pre-line).
    body                =   models.TextField(verbose_name = 'Contenido')
    is_published        =   models.BooleanField(default = False, verbose_name = 'Publicada')
    #Se fija una sola vez, en la primera publicación (no se re-notifica
    #al despublicar/ republicar: la novedad ya quedó contada).
    published_at        =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de publicación')
    created_at          =   models.DateTimeField(auto_now_add = True)
    updated_at          =   models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name        =   'Novedad del sistema'
        verbose_name_plural =   'Novedades del sistema'
        ordering            =   ['-published_at', '-created_at']

    def save(self, *args, **kwargs):
        publish_now     =   self.is_published and not self.published_at
        if publish_now:
            self.published_at   =   timezone.now()
        super().save(*args, **kwargs)
        if publish_now:
            from AdminApp.domains.notifications.services import notify_changelog
            notify_changelog(self)

    def __str__(self):
        return self.title
