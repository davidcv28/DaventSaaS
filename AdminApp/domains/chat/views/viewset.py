from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from AdminApp.domains.chat.models import AssistantMessage, ChatMessage, ChatThread
from AdminApp.domains.chat.serializers import (
    AssistantMessageSerializer,
    ChatMessageSerializer,
    ChatSendSerializer,
    ChatThreadSerializer,
)
from AdminApp.domains.chat.services import (
    CHAT_PRIVATE_PREFIX,
    chat_enabled,
    ensure_greeting,
    get_or_create_thread,
    messages_payload,
    online_customer_ids,
    reply_to_user,
    send_message,
    staff_online,
    staff_roster,
    staff_threads_queryset,
    thread_of,
    touch_presence,
    unread_for,
    upload_chat_image,
)
from McpApp.domains.skills.services import mcp_user_access

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
            raise PermissionDenied('El asistente está disponible con un plan pago (básico, estándar o premium).')

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
            #Hilo de soporte puro (cliente <-> equipo): sin mensajes del
            #asistente — "Tu Asistente" vive en /api/assistant/, no acá.
            thread      =   get_or_create_thread(request.user)
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
        #Sin chat en el plan el heartbeat responde 204 (no 403): el panel lo
        #llama en cada carga aunque el beneficio esté apagado y el 403
        #ensuciaba la consola del navegador en cada visita. El gate real
        #sigue en list/messages/send; acá no hay nada que reportar y la
        #presencia no se toca (no hay sesión "en línea" que marcar).
        if not chat_enabled(request.user):
            return Response(status = status.HTTP_204_NO_CONTENT)
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


#=========================================
# ASSISTANT VIEWSET — "Tu Asistente" (MCP, solo plan pago)
#=========================================
class AssistantViewSet(viewsets.GenericViewSet):
    """
    Conversación del usuario con Tu Asistente (bot MCP). Hilo aparte del
    soporte: el staff no lo ve. Gate: autenticado + plan pago vigente
    no-trial (mcp_user_access) — el asistente solo conoce los datos del
    usuario en sesión vía las tools my_*.
    """
    permission_classes  =   [IsAuthenticated]
    throttle_classes    =   [ChatPollThrottle]

    def get_throttles(self):
        throttles   =   super().get_throttles()
        if self.action == 'send':
            throttles.append(ChatSendThrottle())
        return throttles

    def _gate(self, request):
        if not mcp_user_access(request.user):
            raise PermissionDenied('Tu Asistente está disponible con un plan pago (básico, estándar o premium).')

    #GET /api/assistant/ — historial propio (+ saludo en el primer acceso)
    def list(self, request):
        self._gate(request)
        ensure_greeting(request.user)
        messages    =   AssistantMessage.objects.filter(user = request.user)
        return Response({
            'messages'  :   AssistantMessageSerializer(messages, many = True).data,
        })

    #POST /api/assistant/send/ {body} — guarda y responde el bot
    @action(detail = False, methods = ['post'], url_path = 'send')
    def send(self, request):
        self._gate(request)
        body    =   (request.data.get('body') or '').strip()[:2000]
        if not body:
            return Response({'body': ['Escribí un mensaje.']}, status = status.HTTP_400_BAD_REQUEST)
        reply, action   =   reply_to_user(request.user, body)
        return Response(
            {
                'reply'     :   AssistantMessageSerializer(reply).data if reply else None,
                #Acción de panel (assist_design / assist_business) o None:
                #el front la ejecuta una vez; no viaja en el historial.
                'action'    :   action,
            },
            status = status.HTTP_201_CREATED,
        )
