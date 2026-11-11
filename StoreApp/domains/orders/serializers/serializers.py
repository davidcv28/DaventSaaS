from rest_framework import serializers

from StoreApp.domains.orders.models import Order, OrderEvent, OrderItem

"""

Serializers del dominio orders.

Regla de oro: NINGÚN serializer de entrada acepta precios, totales,
estado ni ids de tienda/cliente — todo eso lo resuelve
services.checkout.create_order server-side (un `total`/`price` en el
body se ignora por diseño, no por validación).

"""
#=========================================
# ORDER CREATE (POST /api/stores/public/<slug>/orders/)
#=========================================
class OrderCreateSerializer(serializers.Serializer):
    """
    Body del checkout. `items` admite {product_id, qty}; `use_cart` (o
    `cart`) pide armar el pedido desde el carrito del cliente para esa
    tienda — orders lo consume vía services (orders→cart, sin ciclo).
    `address_id` referencia una CustomerAddress DEL comprador;
    `address` inline es el snapshot alternativo (envío a domicilio lo
    exige — lo valida el service).
    """
    items                   =   serializers.ListField(
        child   =   serializers.DictField(),
        required =   False,
        max_length = 50,
    )
    use_cart                =   serializers.BooleanField(required = False, default = False)
    cart                    =   serializers.BooleanField(required = False, default = False)
    address_id              =   serializers.IntegerField(required = False, min_value = 1)
    address                 =   serializers.DictField(required = False)
    shipping_method         =   serializers.ChoiceField(choices = Order.ShippingMethod.choices, default = Order.ShippingMethod.HOME)
    payment_method          =   serializers.ChoiceField(choices = Order.PaymentMethod.choices)
    idempotency_key         =   serializers.CharField(required = False, allow_blank = True, max_length = 80, trim_whitespace = True)
    #Antispam (mismo patrón que ProductReview): honeypot + captcha firmado.
    website                 =   serializers.CharField(required = False, allow_blank = True, write_only = True)
    challenge_id            =   serializers.CharField(required = True, write_only = True)
    captcha_answer          =   serializers.CharField(required = True, max_length = 8, write_only = True)
    def validate(self, attrs):
        #Domicilio obligatorio server-side (el front ya lo exige en
        #canSubmit, pero el endpoint es público): 'home' sin dirección
        #guardada requiere calle/ciudad/provincia no vacías — error por
        #campo para que la UI lo pinte bajo cada input. 'pickup' queda
        #exento y con `address_id` manda la CustomerAddress del comprador
        # (su serializer ya exige los campos; services.checkout lo
        # revalida como invariante para cualquier otro caller).
        if attrs.get('shipping_method') == Order.ShippingMethod.HOME and not attrs.get('address_id'):
            address =   attrs.get('address') or {}
            errors  =   {}
            for key, label in (('line1', 'la calle y el número'), ('city', 'la ciudad'), ('province', 'la provincia')):
                if not str(address.get(key) or '').strip():
                    errors[f'address.{key}']   =   f'Ingresá {label} para el envío a domicilio.'
            if errors:
                raise serializers.ValidationError(errors)
        return attrs
#=========================================
# OWNER ACTIONS (panel del dueño)
#=========================================
class OrderOwnerConfirmSerializer(serializers.Serializer):
    """POST confirm-payment: referencia opcional del pago recibido."""
    reference               =   serializers.CharField(required = False, allow_blank = True, max_length = 120, trim_whitespace = True)


class OrderOwnerAdvanceSerializer(serializers.Serializer):
    """POST advance: estado destino (la máquina de estados valida)."""
    status                  =   serializers.ChoiceField(choices = [
        Order.Status.PACKING,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
        Order.Status.REFUNDED,
    ])


class OrderOwnerCancelSerializer(serializers.Serializer):
    """POST cancel: motivo opcional para la bitácora."""
    reason                  =   serializers.CharField(required = False, allow_blank = True, max_length = 300, trim_whitespace = True)


class OrderInvoiceRefSerializer(serializers.Serializer):
    """POST invoice-ref: nº/CAE real que el vendedor emitió en ARCA."""
    invoice_ref             =   serializers.CharField(required = True, min_length = 1, max_length = 80, trim_whitespace = True)
#=========================================
# OWNER SERIALIZERS (panel — datos completos del pedido)
#=========================================
class StoreOrderItemSerializer(serializers.ModelSerializer):
    image                   =   serializers.SerializerMethodField()
    class Meta:
        model               =   OrderItem
        fields              =   ['id', 'product', 'name', 'list_price', 'unit_price', 'qty', 'line_total', 'image']
    def get_image(self, item):
        from StoreApp.domains.stores.services.storage import object_url
        return object_url(item.image_key)


class StoreOrderListSerializer(serializers.ModelSerializer):
    """Fila de la bandeja del dueño (sin items ni eventos — solo resúmen)."""
    code                    =   serializers.CharField(read_only = True)
    customer_name           =   serializers.SerializerMethodField()
    item_count              =   serializers.SerializerMethodField()
    proof_uploaded          =   serializers.SerializerMethodField()
    class Meta:
        model               =   Order
        fields              =   ['id', 'number', 'code', 'status', 'payment_method', 'shipping_method', 'total', 'created_at', 'paid_at', 'expires_at', 'customer_first_name', 'customer_last_name', 'customer_email', 'customer_name', 'item_count', 'proof_uploaded']
    def get_customer_name(self, order):
        name    =   f'{order.customer_first_name} {order.customer_last_name}'.strip()
        return name or order.customer_email
    def get_item_count(self, order):
        #items viene prefetcheado por el queryset del viewset — len() no
        #genera query extra (cero N+1 en la bandeja).
        return sum(item.qty for item in order.items.all())
    def get_proof_uploaded(self, order):
        return hasattr(order, 'proof')


class StoreOrderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model   =   OrderEvent
        fields  =   ['id', 'kind', 'status_from', 'status_to', 'actor', 'note', 'created_at']


class StoreOrderDetailSerializer(serializers.ModelSerializer):
    """
    Detalle completo para el dueño: items snapshot, dirección, eventos,
    comprobante y TODOS los datos del comprador (incluido documento —
    el vendedor lo necesita para facturar; el campo descifra solo).
    """
    code                    =   serializers.CharField(read_only = True)
    items                   =   StoreOrderItemSerializer(many = True, read_only = True)
    events                  =   StoreOrderEventSerializer(many = True, read_only = True)
    proof_image             =   serializers.SerializerMethodField()
    proof_uploaded          =   serializers.SerializerMethodField()
    class Meta:
        model               =   Order
        fields              =   [
            'id', 'number', 'code', 'status', 'payment_method', 'payment_ref', 'mp_payment_id',
            'shipping_method', 'shipping_address', 'subtotal', 'discount_total', 'shipping_cost', 'total',
            'expires_at', 'paid_at', 'created_at', 'updated_at', 'invoice_ref', 'proof_required', 'idempotency_key',
            'customer_first_name', 'customer_last_name', 'customer_email', 'customer_phone',
            'customer_document_type', 'customer_document',
            'items', 'events', 'proof_image', 'proof_uploaded',
        ]
    def get_proof_uploaded(self, order):
        return hasattr(order, 'proof')
    def get_proof_image(self, order):
        proof   =   getattr(order, 'proof', None)
        if proof is None:
            return None
        from StoreApp.domains.stores.services.storage import object_url
        #El comprobante NO es contenido público de tienda: URL firmada.
        return object_url(proof.image_key, private = True)
#=========================================
# CUSTOMER (listado de pedidos del comprador logueado)
#=========================================
class CustomerOrderListSerializer(serializers.ModelSerializer):
    """
    Fila del listado /api/customer/orders/: lo mínimo para que el
    comprador reconozca y linkee el seguimiento — tracking_token es la
    credencial pública (el id numérico NO viaja, mismo criterio
    anti-IDOR que order_public_payload). Sin PII del snapshot: el
    detalle completo lo da el endpoint de tracking ya auditado.
    """
    code                =   serializers.CharField(read_only = True)
    store_slug          =   serializers.SerializerMethodField()
    store_name          =   serializers.SerializerMethodField()
    items_count         =   serializers.SerializerMethodField()
    class Meta:
        model           =   Order
        fields          =   ['tracking_token', 'store_slug', 'store_name', 'code', 'status', 'payment_method', 'total', 'created_at', 'items_count']
    def get_store_slug(self, order):
        return order.store.slug
    def get_store_name(self, order):
        from StoreApp.domains.memberships.services.benefits import store_display_name
        return store_display_name(order.store)
    def get_items_count(self, order):
        #items viene prefetcheado por el queryset de la vista — len()
        #sobre la cache no genera query extra (cero N+1 en la lista).
        return sum(item.qty for item in order.items.all())
