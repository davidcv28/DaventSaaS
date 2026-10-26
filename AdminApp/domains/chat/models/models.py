from django.conf import settings
from django.db import models

"""
Modelos del dominio chat (soporte asincrono cliente <-> staff).

Un cliente tiene UNA conversacion de soporte (ChatThread, OneToOne al
usuario) que el staff responde desde el panel admin. La "presencia" no es
un booleano permanente: es un heartbeat que vence — ChatPresence.last_seen
se actualiza mientras el usuario tiene el chat abierto y se considera
conectado solo dentro de la ventana ONLINE_SECONDS del service.
"""

#=========================================
# CHAT THREAD MODEL
#=========================================
class ChatThread(models.Model):
    #Un hilo de soporte por cliente; staff responde dentro del mismo hilo
    customer            =   models.OneToOneField(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'chat_thread', verbose_name = 'Cliente')
    created_at          =   models.DateTimeField(auto_now_add = True)
    #Se toca a mano en cada mensaje para ordenar la bandeja del staff
    updated_at          =   models.DateTimeField(auto_now = True, db_index = True)

    class Meta:
        verbose_name        =   'Conversación de soporte'
        verbose_name_plural =   'Conversaciones de soporte'

    def __str__(self):
        return f'Chat de {self.customer.username}'


#=========================================
# CHAT MESSAGE MODEL
#=========================================
class ChatMessage(models.Model):
    thread              =   models.ForeignKey(ChatThread, on_delete = models.CASCADE, related_name = 'messages', verbose_name = 'Conversación')
    sender              =   models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'chat_messages', verbose_name = 'Remitente')
    #Denormalizado: staff puede escribir en cualquier hilo — el flag lo
    #fija el service al crear (nunca viene del request del cliente).
    from_staff          =   models.BooleanField(default = False, verbose_name = 'Del staff')
    body                =   models.TextField(max_length = 2000, blank = True, verbose_name = 'Mensaje')
    #Adjunto de imagen: en DB solo viaja la KEY del objeto (R2) o el path
    #bajo MEDIA_ROOT — el archivo jamás es un blob de base de datos; vive
    #como archivo (el emisor lo elige de su PC, el receptor lo descarga a
    #la suya). '' = mensaje solo texto.
    image_key           =   models.CharField(max_length = 300, blank = True, default = '', verbose_name = 'Imagen adjunta')
    #Leido por la contraparte; null = pendiente. Es lo que alimenta los
    #contadores de no-leidos de ambos lados.
    read_at             =   models.DateTimeField(null = True, blank = True, verbose_name = 'Leído')
    created_at          =   models.DateTimeField(auto_now_add = True)

    class Meta:
        verbose_name        =   'Mensaje de chat'
        verbose_name_plural =   'Mensajes de chat'
        ordering            =   ['created_at']
        indexes             =   [
            models.Index(fields = ['thread', 'created_at'], name = 'idx_chatmsg_thread_date'),
            models.Index(fields = ['thread', 'from_staff', 'read_at'], name = 'idx_chatmsg_unread'),
        ]

    def __str__(self):
        return f'{self.sender.username}: {self.body[:40]}'


#=========================================
# CHAT PRESENCE MODEL
#=========================================
class ChatPresence(models.Model):
    #Heartbeat: last_seen se actualiza mientras el chat esta abierto; un
    #usuario esta "conectado" solo si last_seen entra en la ventana.
    user                =   models.OneToOneField(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'chat_presence', verbose_name = 'Usuario')
    last_seen           =   models.DateTimeField(db_index = True, verbose_name = 'Última conexión')

    class Meta:
        verbose_name        =   'Presencia de chat'
        verbose_name_plural =   'Presencias de chat'

    def __str__(self):
        return f'{self.user.username} — {self.last_seen:%Y-%m-%d %H:%M}'
