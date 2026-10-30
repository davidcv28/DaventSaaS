from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from AdminApp.domains.chat.models import ChatMessage, ChatThread
from AdminApp.domains.chat.serializers import (
    ChatMessageSerializer,
    ChatSendSerializer,
    ChatThreadSerializer,
)
from AdminApp.domains.chat.services import (
    CHAT_PRIVATE_PREFIX,
    chat_enabled,
    get_or_create_thread,
    messages_payload,
    online_customer_ids,
    reply_to_customer,
    send_message,
    staff_online,
    staff_roster,
    staff_threads_queryset,
    thread_of,
    touch_presence,
    unread_for,
    upload_chat_image,
    welcome_question,
)

"""
Viewset del chat de soporte cliente <-> staff (asincrono: polling +
heartbeat, sin websockets — el deploy corre gunicorn sync).

- Cliente: exige IsAuthenticated + flag `has_support_chat` del plan.
- Staff: siempre habilitado (es el lado que responde).
- Un cliente solo ve SU hilo; el staff ve la bandeja completa.
- Presencia: heartbeat que vence a los ONLINE_SECONDS — no hay un
  booleano eterno que finja conexion.
"""

#=========================================
# CHAT THROTTLES
#=========================================
class ChatPollThrottle(ScopedRateThrottle):
    #Scope 'chat' (settings): polling de mensajes + heartbeat. Reemplaza el
    #'user' default (1000/dia mataria el polling en ~40 min). Holgado para
    #intervalo de ~5s pero acota abusos.
    scope   =   'chat'

class ChatSendThrottle(ScopedRateThrottle):
    #Scope 'chat_send': spam de mensajes — mucho mas estricto que el read.
    scope   =   'chat_send'


#=========================================
# SUPPORT CHAT VIEWSET
#=========================================
class SupportChatViewSet(viewsets.GenericViewSet):
    permission_classes  =   [IsAuthenticated]
    throttle_classes    =   [ChatPollThrottle]

    def get_throttles(self):
        #El envio suma un segundo scope: leer 1500/h y escribir 120/h.
        throttles   =   super().get_throttles()
        if self.action == 'send':
            throttles.append(ChatSendThrottle())
        return throttles

    def _gate(self, request):
        #Fail-closed: sin beneficio el cliente recibe 403 (el frontend
        #oculta la seccion, pero el gate es este).
        if not chat_enabled(request.user):
            raise PermissionDenied('El asistente de diseño está disponible en el plan Premium.')

    #=========================================
    # LIST — GET /api/chat/ (role-aware)
    #=========================================
    def list(self, request):
        self._gate(request)
        if request.user.is_staff:
            online      =   online_customer_ids()
            threads     =   staff_threads_queryset()
            return Response({
                'threads'   :   ChatThreadSerializer(threads, many = True, context = {'request': request, 'online_ids': online}).data,
                'online'    :   sorted(online),
            })
        thread      =   thread_of(request.user)
        if thread is None:
            #El asistente abre la conversación con la primera pregunta de diseño.
            thread      =   get_or_create_thread(request.user)
            welcome_question(thread)
        messages    =   messages_payload(request.user, thread)
        return Response({
            'thread'        :   {'id': thread.id} if thread else None,
            'messages'      :   ChatMessageSerializer(messages, many = True, context = {'request': request}).data,
            'unread'        :   unread_for(request.user, thread) if thread else 0,
            'staff_online'  :   staff_online(),
            'staff'         :   staff_roster(),
        })

    #=========================================
    # MESSAGES — GET /api/chat/messages/?after=<id>&thread=<id>
    #=========================================
    @action(detail = False, methods = ['get'], url_path = 'messages')
    def messages(self, request):
        self._gate(request)
        thread      =   self._resolve_thread(request)
        if thread is None:
            return Response({'detail': 'No encontrado.'}, status = status.HTTP_404_NOT_FOUND)
        try:
            after   =   int(request.query_params.get('after', 0) or 0)
        except (TypeError, ValueError):
            after   =   0
        messages    =   messages_payload(request.user, thread, after = after)
        return Response({'messages': ChatMessageSerializer(messages, many = True, context = {'request': request}).data})

    #=========================================
    # SEND — POST /api/chat/send/ {body?, image?, thread?} (json o multipart)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'send')
    def send(self, request):
        self._gate(request)
        serializer  =   ChatSendSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        if request.user.is_staff:
            #Staff responde dentro de un hilo existente (thread requerido)
            thread_id   =   serializer.validated_data.get('thread')
            thread      =   ChatThread.objects.filter(pk = thread_id).first() if thread_id else None
            if thread is None:
                return Response({'detail': 'Elegí una conversación.'}, status = status.HTTP_404_NOT_FOUND)
        else:
            #El cliente escribe solo en su propio hilo (se crea al primer envio)
            thread      =   get_or_create_thread(request.user)
        image_key   =   ''
        image       =   serializer.validated_data.get('image')
        if image:
            #El adjunto viaja al bucket/disco — a la DB solo va la key.
            try:
                image_key   =   upload_chat_image(thread, image)
            except ValueError as exc:
                return Response({'image': [str(exc)]}, status = status.HTTP_400_BAD_REQUEST)
        message     =   send_message(request.user, serializer.validated_data['body'], thread, image_key = image_key)
        if not request.user.is_staff:
            #Asistente de diseño: responde y hace la siguiente pregunta.
            reply_to_customer(thread, serializer.validated_data['body'])
        return Response(
            {'message': ChatMessageSerializer(message, context = {'request': request}).data},
            status = status.HTTP_201_CREATED,
        )

    #=========================================
    # ATTACHMENT — GET /api/chat/attachment/<id>/ (solo dueño del hilo o staff)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = r'attachment/(?P<message_id>[0-9]+)')
    def attachment(self, request, message_id = None):
        self._gate(request)
        message =   ChatMessage.objects.select_related('thread').filter(pk = message_id).first()
        if message is None or not message.image_key:
            raise Http404
        if not request.user.is_staff and message.thread.customer_id != request.user.pk:
            #Un id ajeno no filtra existencia.
            raise Http404
        if message.image_key.startswith(CHAT_PRIVATE_PREFIX):
            handle  =   default_storage.open(message.image_key, 'rb')
            return FileResponse(handle, content_type = 'image/webp')
        #Bucket: URL firmada de vida corta (nunca la pública).
        from StoreApp.domains.stores.services import storage
        url     =   storage.object_url(message.image_key, private = True, expires = 3600)
        if not url:
            raise Http404
        return redirect(url)

    #=========================================
    # HEARTBEAT — POST /api/chat/heartbeat/
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'heartbeat')
    def heartbeat(self, request):
        self._gate(request)
        touch_presence(request.user)
        if request.user.is_staff:
            #No-leidos totales (badge del sidebar) + quienes estan conectados
            unread  =   ChatMessage.objects.filter(from_staff = False, read_at__isnull = True).count()
            return Response({'unread': unread, 'online': sorted(online_customer_ids())})
        thread      =   thread_of(request.user)
        return Response({
            'unread'        :   unread_for(request.user, thread) if thread else 0,
            'staff_online'  :   staff_online(),
            'staff'         :   staff_roster(),
        })

    def _resolve_thread(self, request):
        #Staff puede leer cualquier hilo por ?thread=<id>; el cliente solo
        #el suyo (un id ajeno no filtra existencia: devuelve el propio o 404).
        if request.user.is_staff:
            try:
                thread_id   =   int(request.query_params.get('thread', 0) or 0)
            except (TypeError, ValueError):
                return None
            return ChatThread.objects.filter(pk = thread_id).first()
        return thread_of(request.user)
