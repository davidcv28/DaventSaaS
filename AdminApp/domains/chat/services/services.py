from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone

from AdminApp.domains.chat.models         import ChatMessage, ChatPresence, ChatThread
from StoreApp.domains.stores.services     import profile_has_benefit

"""
Queries/servicios del chat de soporte.

- Gate: el cliente exige el flag `has_support_chat` (Premium + prueba);
  el staff siempre puede responder.
- Un cliente = un hilo (OneToOne). El staff ve todos los hilos.
- Presencia: heartbeat con ventana ONLINE_SECONDS — sin heartbeat fresco
  el usuario aparece desconectado (no hay booleano eterno).
"""

#Ventana de "conectado": el frontend hace heartbeat cada ~45s; 2 min de
#gracia cubre un intervalo perdido sin dejar presencias fantasma.
ONLINE_SECONDS      =   120
#Cantidad de mensajes que devuelve la carga inicial del hilo
MESSAGES_PAGE_SIZE  =   50


#=========================================
# GATING
#=========================================
def chat_enabled(user : User) -> bool:
    #Staff siempre (es el lado que responde); cliente exige el beneficio.
    if user.is_staff:
        return True
    profile     =   getattr(user, 'profile', None)
    return bool(profile and profile_has_benefit(profile, 'has_support_chat'))


#=========================================
# THREADS
#=========================================
def thread_of(user : User) -> ChatThread | None:
    return getattr(user, 'chat_thread', None)


def get_or_create_thread(user : User) -> ChatThread:
    #Solo el cliente crea su hilo (al primer mensaje); el staff responde
    #sobre hilos existentes.
    thread, _   =   ChatThread.objects.get_or_create(customer = user)
    return thread


def staff_threads_queryset():
    return (
        ChatThread.objects
        .select_related('customer', 'customer__profile')
        .annotate(unread_count = Count('messages', filter = Q(messages__from_staff = False, messages__read_at__isnull = True)))
        .order_by('-updated_at')
    )


def unread_for(user : User, thread : ChatThread) -> int:
    #Mensajes de la contraparte sin leer: para el cliente cuentan los del
    #staff (from_staff=True), para el staff los del cliente.
    if user.is_staff:
        return thread.messages.filter(from_staff = False, read_at__isnull = True).count()
    return thread.messages.filter(from_staff = True, read_at__isnull = True).count()


def mark_counterpart_read(user : User, thread : ChatThread):
    #Lectura marca solo los mensajes AJENOS: al abrir el hilo los
    #mensajes del otro lado pasan a leidos para ESTE usuario.
    qs      =   thread.messages.filter(read_at__isnull = True)
    if user.is_staff:
        qs  =   qs.filter(from_staff = False)
    else:
        qs  =   qs.filter(from_staff = True)
    qs.update(read_at = timezone.now())


def messages_payload(user : User, thread : ChatThread, after : int = 0):
    #Incremental: after = ultimo id conocido (0 = ultimos MESSAGES_PAGE_SIZE).
    #La lectura marca la contraparte como leida para este usuario.
    mark_counterpart_read(user, thread)
    qs      =   thread.messages.select_related('sender').order_by('created_at')
    if after:
        return qs.filter(id__gt = after)
    return qs.order_by('-created_at')[:MESSAGES_PAGE_SIZE][::-1]


def send_message(sender : User, body : str, thread : ChatThread) -> ChatMessage:
    message     =   ChatMessage.objects.create(
        thread      =   thread,
        sender      =   sender,
        from_staff  =   sender.is_staff,
        body        =   body,
    )
    ChatThread.objects.filter(pk = thread.pk).update(updated_at = message.created_at)
    return message


#=========================================
# PRESENCE
#=========================================
def touch_presence(user : User):
    ChatPresence.objects.update_or_create(user = user, defaults = {'last_seen': timezone.now()})


def _online_since():
    return timezone.now() - timedelta(seconds = ONLINE_SECONDS)


def staff_online() -> bool:
    return ChatPresence.objects.filter(user__is_staff = True, last_seen__gte = _online_since()).exists()


def online_customer_ids():
    #Clientes conectados (para la bandeja del staff). No expone staff.
    return set(
        ChatPresence.objects
        .filter(user__is_staff = False, last_seen__gte = _online_since())
        .values_list('user_id', flat = True)
    )
