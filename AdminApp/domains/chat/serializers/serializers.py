from rest_framework import serializers

from AdminApp.domains.chat.models import ChatMessage, ChatThread

"""
Serializers del chat de soporte.
El payload expone lo minimo: cuerpo, lado (from_staff/mine) y fecha —
nunca emails ni ids del staff hacia el cliente.
"""

#=========================================
# MESSAGE SERIALIZER
#=========================================
class ChatMessageSerializer(serializers.ModelSerializer):
    mine            =   serializers.SerializerMethodField()
    sender_name     =   serializers.SerializerMethodField()
    image_url       =   serializers.SerializerMethodField()

    class Meta:
        model   =   ChatMessage
        fields  =   ['id', 'body', 'image_url', 'from_staff', 'mine', 'sender_name', 'read_at', 'created_at']

    def get_image_url(self, obj):
        from AdminApp.domains.chat.services import chat_image_url
        return chat_image_url(self.context.get('request'), obj)

    def get_mine(self, obj):
        request     =   self.context.get('request')
        return bool(request and obj.sender_id == request.user.id)

    def get_sender_name(self, obj):
        #El cliente ve "Soporte" para los del staff (no se filtra el nombre
        #del empleado); el staff ve el nombre del cliente.
        if obj.from_staff:
            return 'Soporte'
        profile     =   getattr(obj.sender, 'profile', None)
        return getattr(profile, 'business_name', None) or obj.sender.username


#=========================================
# SEND SERIALIZER
#=========================================
class ChatSendSerializer(serializers.Serializer):
    body    =   serializers.CharField(trim_whitespace = True, max_length = 2000, required = False, allow_blank = True)
    thread  =   serializers.IntegerField(required = False, min_value = 1)
    #Adjunto opcional: llega como archivo del multipart; la validación de
    #firma/tamaño y la subida corren en services.attachments (fail-closed).
    image   =   serializers.FileField(required = False)

    def validate(self, attrs):
        attrs['body']   =   (attrs.get('body') or '').strip()
        if not attrs['body'] and not attrs.get('image'):
            raise serializers.ValidationError('Escribí un mensaje o adjuntá una imagen.')
        return attrs


#=========================================
# THREAD LIST SERIALIZER (bandeja del staff)
#=========================================
class ChatThreadSerializer(serializers.ModelSerializer):
    customer        =   serializers.SerializerMethodField()
    unread          =   serializers.SerializerMethodField()
    online          =   serializers.SerializerMethodField()
    last_message    =   serializers.SerializerMethodField()

    class Meta:
        model   =   ChatThread
        fields  =   ['id', 'customer', 'unread', 'online', 'last_message', 'updated_at']

    def get_customer(self, obj):
        profile     =   getattr(obj.customer, 'profile', None)
        return {
            'id'    :   obj.customer_id,
            'name'  :   getattr(profile, 'business_name', None) or obj.customer.username,
            'email' :   obj.customer.email,
        }

    def get_unread(self, obj):
        #Anotado en staff_threads_queryset; fallback al count por si el
        #serializer se usa sin la anotacion.
        annotated   =   getattr(obj, 'unread_count', None)
        return annotated if annotated is not None else obj.messages.filter(from_staff = False, read_at__isnull = True).count()

    def get_online(self, obj):
        online  =   self.context.get('online_ids', set())
        return obj.customer_id in online

    def get_last_message(self, obj):
        #Anotado en staff_threads_queryset (Subquery, sin N+1); fallback al
        #query por si el serializer se usa sin la anotación.
        if hasattr(obj, 'last_body'):
            if obj.last_body is None:
                return None
            return {'body': obj.last_body[:80], 'from_staff': obj.last_from_staff, 'created_at': obj.last_created_at}
        last    =   obj.messages.order_by('-created_at').first()
        if not last:
            return None
        return {'body': last.body[:80], 'from_staff': last.from_staff, 'created_at': last.created_at}
