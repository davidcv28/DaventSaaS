from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone

from AdminApp.domains.chat.models import ChatMessage, ChatPresence, ChatThread

"""
Queries/servicios del chat de soporte.

- Gate: el cliente exige suscripción vigente NO trial (básico,
  estándar o premium — usuarios que pagan); el staff siempre responde.
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
    #Staff siempre (es el lado que responde); el cliente exige plan pago
    #vigente: suscripción activa y no-trial (el asistente es de pagos).
    if user.is_staff:
        return True
    suscription =   getattr(getattr(user, 'profile', None), 'suscription', None)
    return bool(
        suscription
        and suscription.grants_access()
        and not suscription.plan_suscription.is_trial
    )


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
    #El último mensaje viaja anotado por Subquery: sin esto la bandeja hacía
    #1 query extra por hilo (N+1) en cada poll del staff.
    last    =   ChatMessage.objects.filter(thread = OuterRef('pk')).order_by('-created_at')
    return (
        ChatThread.objects
        .select_related('customer', 'customer__profile')
        .annotate(
            unread_count = Count('messages', filter = Q(messages__from_staff = False, messages__read_at__isnull = True)),
            last_body = Subquery(last.values('body')[:1]),
            last_from_staff = Subquery(last.values('from_staff')[:1]),
            last_created_at = Subquery(last.values('created_at')[:1]),
        )
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
    if after and after > 0:
        #Tope en incremental: after=1 (o negativo que esquivaba el else)
        #devolvía TODO el historial sin límite — el cliente propio, pero
        #payload/egress no acotado. Con >page_size el front se pone al día
        #en el siguiente poll (avanza last_id con lo recibido).
        return qs.filter(id__gt = after).order_by('id')[:MESSAGES_PAGE_SIZE * 4]
    return qs.order_by('-created_at')[:MESSAGES_PAGE_SIZE][::-1]


def send_message(sender : User, body : str, thread : ChatThread, image_key : str = '') -> ChatMessage:
    message     =   ChatMessage.objects.create(
        thread      =   thread,
        sender      =   sender,
        from_staff  =   sender.is_staff,
        body        =   body or '',
        image_key   =   image_key or '',
    )
    ChatThread.objects.filter(pk = thread.pk).update(updated_at = message.created_at)
    if message.from_staff:
        #Aviso del sistema al cliente (notificación informativa — el click
        #no abre el chat, solo marca leído).
        from AdminApp.domains.notifications.services import notify_staff_message
        notify_staff_message(thread)
    return message


#=========================================
# PRESENCE
#=========================================
def touch_presence(user : User):
    ChatPresence.objects.update_or_create(user = user, defaults = {'last_seen': timezone.now()})


def _online_since():
    return timezone.now() - timedelta(seconds = ONLINE_SECONDS)


def staff_online() -> bool:
    #Mismo universo que staff_roster: superusers (admins) no son agentes
    #de soporte — su presencia no debe marcar "equipo en línea".
    return ChatPresence.objects.filter(
        user__is_staff = True, user__is_superuser = False,
        user__is_active = True, last_seen__gte = _online_since()).exists()


def staff_roster():
    #Equipo de soporte visible para el cliente: solo id, nombre publico y
    #presencia (nunca email, username ni datos de cuenta). Superusers
    #queda fuera — son admins, no agentes de soporte, y exponerlos a todo
    #cliente pago filtraba el directorio completo del staff. El nombre
    #nunca cae al username (expone el login): sin nombre cargado va la
    #etiqueta genérica. Conectados primero.
    since   =   _online_since()
    online  =   set(ChatPresence.objects.filter(
        user__is_staff = True, user__is_superuser = False,
        user__is_active = True, last_seen__gte = since,
    ).values_list('user_id', flat = True))
    roster  =   []
    for u in User.objects.filter(is_staff = True, is_active = True, is_superuser = False).order_by('first_name', 'username'):
        roster.append({
            'id'        :   u.id,
            'name'      :   u.get_full_name().strip() or 'Soporte DAVENT',
            'online'    :   u.id in online,
        })
    roster.sort(key = lambda s: not s['online'])
    return roster


def online_customer_ids():
    #Clientes conectados (para la bandeja del staff). No expone staff.
    return set(
        ChatPresence.objects
        .filter(user__is_staff = False, last_seen__gte = _online_since())
        .values_list('user_id', flat = True)
    )
