from rest_framework import serializers

from StoreApp.domains.support.models import SupportMessage, SupportThread

"""

Serializers del dominio support.

Regla de oro: `body`/`subject` son TEXTO PLANO — ningún serializer los
marca safe ni los sanea como HTML (el frontend los escapa al renderizar;
escapes del lado del cliente, no sanitizer server-side, mismo criterio
que OrderEvent.note y los bodies del chat interno).

Entrada: SOLO campos whitelisted — status/order/store/customer jamás
vienen del body (los resuelve la vista: store por slug validado,
customer por request.customer, order por order_token verificado).
"""
#=========================================
# INPUT (creación de hilo / mensaje)
#=========================================
class SupportThreadCreateSerializer(serializers.Serializer):
    """
    POST /api/support/threads/ — `store` es el slug público de la tienda;
    `order_token` (opcional) enlaza un pedido DEL comprador en ESA tienda.
    """
    store           =   serializers.CharField(max_length = 60, trim_whitespace = True)
    subject         =   serializers.CharField(min_length = 1, max_length = 140, trim_whitespace = True)
    body            =   serializers.CharField(min_length = 1, max_length = 2000, trim_whitespace = True)
    order_token     =   serializers.CharField(required = False, allow_blank = True, max_length = 64, trim_whitespace = True)


class SupportMessageCreateSerializer(serializers.Serializer):
    """POST .../messages/ — el único campo editable del mensaje."""
    body            =   serializers.CharField(min_length = 1, max_length = 2000, trim_whitespace = True)
#=========================================
# OUTPUT — mensaje (compartido por ambos lados)
#=========================================
class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model       =   SupportMessage
        fields      =   ['id', 'sender', 'body', 'created_at']
#=========================================
# OUTPUT — hilo para el COMPRADOR
#=========================================
class SupportThreadCustomerSerializer(serializers.ModelSerializer):
    """
    Fila de /api/support/threads/: store (slug+nombre público), pedido de
    contexto (código + su propio tracking_token — el comprador ya lo
    tiene del checkout) y unread_count anotado por el queryset.
    """
    store           =   serializers.SerializerMethodField()
    order           =   serializers.SerializerMethodField()
    unread_count    =   serializers.IntegerField(read_only = True)
    class Meta:
        model       =   SupportThread
        fields      =   ['id', 'subject', 'status', 'store', 'order', 'last_message_at', 'last_message_by', 'unread_count', 'created_at', 'updated_at']
    def get_store(self, thread):
        store   =   thread.store
        customization =   getattr(store, 'customization', None)
        name    =   (getattr(customization, 'display_name', '') or '').strip()
        if not name:
            name    =   (getattr(store.user, 'business_name', '') or '').strip() or store.slug
        return {'slug': store.slug, 'name': name}
    def get_order(self, thread):
        order   =   getattr(thread, 'order', None)
        if order is None:
            return None
        return {'code': order.code, 'tracking_token': order.tracking_token}


class SupportThreadCustomerDetailSerializer(SupportThreadCustomerSerializer):
    messages        =   SupportMessageSerializer(many = True, read_only = True)
    class Meta(SupportThreadCustomerSerializer.Meta):
        fields      =   [*SupportThreadCustomerSerializer.Meta.fields, 'messages']
#=========================================
# OUTPUT — hilo para el DUEÑO
#=========================================
class SupportThreadOwnerSerializer(serializers.ModelSerializer):
    """
    Fila de /api/store-support/threads/: datos del comprador (nombre +
    email — el vendedor ya los ve en sus pedidos) y el pedido por id/código
    (el dueño gestiona pedidos por id en su panel).
    """
    store           =   serializers.SerializerMethodField()
    customer        =   serializers.SerializerMethodField()
    order           =   serializers.SerializerMethodField()
    unread_count    =   serializers.IntegerField(read_only = True)
    class Meta:
        model       =   SupportThread
        fields      =   ['id', 'subject', 'status', 'store', 'customer', 'order', 'last_message_at', 'last_message_by', 'unread_count', 'created_at', 'updated_at']
    def get_store(self, thread):
        store   =   thread.store
        return {'slug': store.slug, 'name': store.slug}
    def get_customer(self, thread):
        customer    =   thread.customer
        name        =   f'{customer.first_name} {customer.last_name}'.strip() or customer.email
        return {'name': name, 'email': customer.email}
    def get_order(self, thread):
        order   =   getattr(thread, 'order', None)
        if order is None:
            return None
        return {'id': order.pk, 'code': order.code, 'status': order.status}


class SupportThreadOwnerDetailSerializer(SupportThreadOwnerSerializer):
    messages        =   SupportMessageSerializer(many = True, read_only = True)
    class Meta(SupportThreadOwnerSerializer.Meta):
        fields      =   [*SupportThreadOwnerSerializer.Meta.fields, 'messages']
