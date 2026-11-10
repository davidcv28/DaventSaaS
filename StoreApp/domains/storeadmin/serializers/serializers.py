from rest_framework import serializers

from StoreApp.domains.customers.models import Customer
from StoreApp.domains.memberships.services.benefits import is_vigente
from StoreApp.domains.orders.models import Order

"""
Serializers del dominio storeadmin (panel del dueño — Ola 2).

Solo LECTURA: ningún serializer acepta escritura. Los datos vienen de
querysets anotados (services.metrics.build_customer_queryset) y del
prefetch de membresía+suscripciones — cero N+1.

PII: email/nombre/teléfono SÍ salen (el dueño los necesita para
fulfill/envío — mismo criterio que StoreOrderDetailSerializer). El
`document` del cliente NUNCA se expone acá (el detalle de pedido ya lo
muestra cuando corresponde; no se amplía la superficie).
"""
#=========================================
# HELPERS — membresía del cliente EN la tienda
#=========================================
def _membership_of(customer):
    """StoreMembership del cliente en la tienda del request (≤1 por el
    unique customer×store) — viene por prefetch to_attr 'store_memberships'."""
    memberships =   getattr(customer, 'store_memberships', None) or []
    return memberships[0] if memberships else None
def _latest_subscription(membership):
    """
    Suscripción más reciente de la membresía (las trae el prefetch
    ordenadas -created_at). Es la 'foto' del plan del cliente: si
    renovó, la última fila es su plan actual/histórico más fresco.
    """
    if membership is None:
        return None
    subs    =   list(membership.subscriptions.all())
    return subs[0] if subs else None
#=========================================
# PEDIDO — resumen corto (últimos pedidos del detalle de cliente)
#=========================================
class StoreAdminOrderBriefSerializer(serializers.Serializer):
    """
    Fila compacta de pedido para el detalle de cliente: lo justo para
    que el dueño ubique la compra y abra el pedido completo en
    /api/store-orders/. `code` es la property PED-XXXX del modelo.
    """
    code            =   serializers.CharField(read_only = True)
    status          =   serializers.CharField(read_only = True)
    payment_method  =   serializers.CharField(read_only = True)
    total           =   serializers.DecimalField(max_digits = 12, decimal_places = 2, read_only = True)
    created_at      =   serializers.DateTimeField(read_only = True)
    paid_at         =   serializers.DateTimeField(read_only = True)
    tracking_token  =   serializers.CharField(read_only = True)
#=========================================
# CLIENTE — fila del listado
#=========================================
class StoreAdminCustomerListSerializer(serializers.ModelSerializer):
    """
    Cliente de la tienda (miembro o comprador). Los agregados vienen
    anotados por services.metrics.build_customer_queryset:

    - orders_count / total_spent / last_order_at: pedidos DE ESTA
      tienda (total_spent = LTV bruto de ventas vigentes — cobrado_q,
      sin pendientes ni reembolsos; NO incluye suscripciones).
    - joined_at / membership_status / plan_name: de la membresía en
      esta tienda — null si solo compró sin registrarse.
    """
    orders_count        =   serializers.IntegerField(read_only = True)
    total_spent         =   serializers.DecimalField(max_digits = 14, decimal_places = 2, read_only = True)
    last_order_at       =   serializers.DateTimeField(read_only = True)
    joined_at           =   serializers.SerializerMethodField()
    membership_status   =   serializers.SerializerMethodField()
    plan_name           =   serializers.SerializerMethodField()
    #`phone` descifra transparente por el ORM (EncryptedCharField) —
    #el dueño lo necesita para coordinar envíos/cobros.
    phone               =   serializers.CharField(read_only = True)
    class Meta:
        model               =   Customer
        fields              =   [
            'id', 'first_name', 'last_name', 'email', 'phone', 'is_active',
            'membership_status', 'plan_name', 'joined_at',
            'orders_count', 'total_spent', 'last_order_at',
        ]
        read_only_fields    =   fields
    def get_joined_at(self, customer):
        membership  =   _membership_of(customer)
        return membership.joined_at if membership else None
    def get_membership_status(self, customer):
        membership  =   _membership_of(customer)
        return membership.status if membership else None
    def get_plan_name(self, customer):
        sub =   _latest_subscription(_membership_of(customer))
        plan    =   getattr(sub, 'plan', None) if sub else None
        return plan.name if plan else None
#=========================================
# CLIENTE — detalle
#=========================================
class StoreAdminCustomerDetailSerializer(StoreAdminCustomerListSerializer):
    """
    Todo lo del listado + addresses_count, últimos pedidos de la tienda
    y el detalle de la membresía (tags, plan, suscripción vigente).
    """
    addresses_count     =   serializers.SerializerMethodField()
    last_orders         =   serializers.SerializerMethodField()
    membership          =   serializers.SerializerMethodField()
    class Meta(StoreAdminCustomerListSerializer.Meta):
        fields              =   StoreAdminCustomerListSerializer.Meta.fields + [
            'addresses_count', 'last_orders', 'membership',
        ]
        read_only_fields    =   fields
    def get_addresses_count(self, customer):
        #Direcciones globales del comprador (no son por tienda) — el
        #dueño las ve como dato de contacto útil para envíos.
        from StoreApp.domains.customers.models import CustomerAddress
        return CustomerAddress.objects.filter(customer = customer).count()
    def get_last_orders(self, customer):
        store   =   self.context.get('store')
        if store is None:
            return []
        qs  =   (Order.objects
            .filter(store = store, customer = customer)
            .order_by('-created_at', '-id')[:10])
        return StoreAdminOrderBriefSerializer(qs, many = True).data
    def get_membership(self, customer):
        membership  =   _membership_of(customer)
        if membership is None:
            return None
        sub     =   _latest_subscription(membership)
        plan    =   getattr(sub, 'plan', None) if sub else None
        return {
            'status'                :   membership.status,
            'tags'                  :   membership.tags or [],
            'joined_at'             :   membership.joined_at,
            'plan_name'             :   plan.name if plan else None,
            'subscription_status'   :   sub.status if sub else None,
            'vigente_hasta'         :   sub.vigente_hasta if sub else None,
            'is_vigente'            :   bool(sub and is_vigente(sub)),
        }
