from django.db import models

from StoreApp.domains.customers.models import Customer
from StoreApp.domains.orders.models import Order
from StoreApp.domains.stores.models import Store

"""

Soporte comprador <-> dueño de tienda (e-commerce DAVENT, track G).

Contrato comprador <-> vendedor: DAVENT no media ni modera el contenido —
los mensajes son texto plano que el frontend renderiza escapado (jamás
marcar `body` como HTML/safe en ningún serializer).

Decisiones de diseño:

- HILOS MÚLTIPLES por (store, customer): un comprador puede tener varios
  hilos con la misma tienda (uno por pedido o por tema); el `subject`
  los distingue en las listas. No hay unique — más simple y flexible que
  forzar "un hilo por tienda".
- `order` es contexto OPCIONAL: enlaza el hilo a un pedido propio del
  comprador en ESA tienda (la vista valida store+customer — anti-IDOR
  doble). SET_NULL: si el pedido se borra el hilo sobrevive.
- `customer` es PROTECT: el hilo es evidencia de la conversación
  comprador<->vendedor y sobrevive a la baja lógica de la cuenta
  (Customer usa soft-delete `is_active`; nadie borra filas en la práctica).
- Lectura POR LADO: cada SupportMessage lleva `read_by_customer_at` y
  `read_by_owner_at` (null = no leído por ese lado). Es lo que alimenta
  los contadores `unread_count` de ambas bandejas sin tabla extra.
- `last_message_at`/`last_message_by` van denormalizados en el thread
  (los actualiza services.post_message): ordenan la bandeja sin join y
  sin N+1. `updated_at` también se toca en cada mensaje.
- Append-only: no hay endpoints de edición/borrado de mensajes — igual
  que OrderEvent. El ciclo de vida del hilo es open/closed; cerrar NO
  borra nada y el dueño puede reabrir (el comprador no: cerrar es
  terminal para él, reabrir es decisión del vendedor).
"""
#=========================================
# SUPPORT THREAD (hilo comprador <-> dueño por tienda)
#=========================================
class SupportThread(models.Model):
    class Status(models.TextChoices):
        OPEN    =   'open',    'Abierto'
        CLOSED  =   'closed',  'Cerrado'
    class LastMessageBy(models.TextChoices):
        CUSTOMER    =   'customer',    'Comprador'
        OWNER       =   'owner',       'Dueño de la tienda'
    store                   =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'support_threads', db_index = False)
    customer                =   models.ForeignKey(Customer, on_delete = models.PROTECT, related_name = 'support_threads', db_index = False)
    #Pedido de contexto (opcional): solo el del comprador en ESTA tienda.
    order                   =   models.ForeignKey(Order, on_delete = models.SET_NULL, related_name = 'support_threads', null = True, blank = True, db_index = False)
    subject                 =   models.CharField(max_length = 140, verbose_name = 'Asunto')
    status                  =   models.CharField(max_length = 10, choices = Status.choices, default = Status.OPEN, verbose_name = 'Estado')
    #Denormalizado del último mensaje (lo escribe services.post_message).
    last_message_at         =   models.DateTimeField(null = True, blank = True, verbose_name = 'Último mensaje')
    last_message_by         =   models.CharField(max_length = 10, choices = LastMessageBy.choices, blank = True, default = '', verbose_name = 'Último mensaje de')
    created_at              =   models.DateTimeField(auto_now_add = True)
    updated_at              =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label           =   'support'
        verbose_name        =   'Hilo de soporte'
        verbose_name_plural =   'Hilos de soporte'
        ordering            =   ['-last_message_at', '-id']
        indexes             =   [
            #Bandeja del dueño: sus hilos filtrados por estado, más
            #reciente primero (índice principal del listado).
            models.Index(fields = ['store', 'status', 'last_message_at'], name = 'idx_supthr_store_status_msg'),
            #Bandeja del comprador: sus hilos en todas las tiendas.
            models.Index(fields = ['customer', 'last_message_at'], name = 'idx_supthr_customer_msg'),
        ]
    def __str__(self):
        return f'support:{self.store_id}/{self.customer_id} — {self.subject[:40]}'
#=========================================
# SUPPORT MESSAGE (append-only)
#=========================================
class SupportMessage(models.Model):
    class Sender(models.TextChoices):
        CUSTOMER    =   'customer',    'Comprador'
        OWNER       =   'owner',       'Dueño de la tienda'
    thread                  =   models.ForeignKey(SupportThread, on_delete = models.CASCADE, related_name = 'messages', db_index = False)
    sender                  =   models.CharField(max_length = 10, choices = Sender.choices, verbose_name = 'Remitente')
    #Texto plano — el front lo escapa al renderizar. El tope (2000) lo
    #enforcea el serializer; acá queda como red de seguridad del modelo.
    body                    =   models.TextField(max_length = 2000, verbose_name = 'Mensaje')
    #Leído POR ese lado (no "leído por el autor"): el comprador marca
    #read_by_customer_at al abrir el hilo; el dueño, read_by_owner_at.
    read_by_customer_at     =   models.DateTimeField(null = True, blank = True, verbose_name = 'Leído por el comprador')
    read_by_owner_at        =   models.DateTimeField(null = True, blank = True, verbose_name = 'Leído por el dueño')
    created_at              =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label           =   'support'
        verbose_name        =   'Mensaje de soporte'
        verbose_name_plural =   'Mensajes de soporte'
        ordering            =   ['created_at', 'id']
        indexes             =   [
            models.Index(fields = ['thread', 'created_at'], name = 'idx_supmsg_thread_date'),
        ]
    def __str__(self):
        return f'{self.sender}: {self.body[:40]}'
