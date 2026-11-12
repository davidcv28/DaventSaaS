from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.throttling import PublicReadThrottle
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.catalog.serializers.serializers import ProductPublicSerializer
from StoreApp.domains.catalog.services.services import (
    effective_pricing_of,
    running_discounts_of,
)
from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)
from StoreApp.domains.customers.models import StoreMembership
from StoreApp.domains.customers.services.customers import ensure_membership
from StoreApp.domains.customers.views.auth_views import CustomerApiThrottle
from StoreApp.domains.memberships.models import StorePlan, StoreSubscription
from StoreApp.domains.memberships.serializers import (
    MembershipCardSerializer,
    StorePlanPublicSerializer,
    StoreSubscriptionCustomerSerializer,
)
from StoreApp.domains.memberships.services.benefits import (
    active_subscription_of,
    has_exclusive_access,
    member_benefits,
    store_display_name,
)
from StoreApp.domains.stores.models import Store

"""

Endpoints del COMPRADOR (customer JWT de track A — request.customer).

- /api/customer/subscriptions/            → todas sus suscripciones.
- /api/customer/subscriptions/<slug>/     → planes de ESA tienda + la
  suya vigente/pendiente (GET) y contratación pending (POST).
- /api/customer/subscriptions/<slug>/card/→ su tarjeta digital.
- /api/customer/stores/<slug>/exclusive-products/ → catálogo de
  exclusivos para miembros (has_exclusive_access; si no, 404 — ni se
  revela que existen).
- /api/membership-cards/<slug>/<token>/   → tarjeta PÚBLICA por
  public_token (sin auth, throttle public_read, payload mínimo).

Nota: GET /api/customer/memberships/ ya la sirve el dominio customers
(track A — membresías crudas store/status/tags); acá no se duplica.
La "membresía con plan vigente resumido" viaja en
/api/customer/subscriptions/ (cada fila trae store_slug/store_name +
plan + is_vigente + benefits).

"""
#=========================================
# HELPERS
#=========================================
def _public_store_or_404(slug):
    """
    Tienda visible para un comprador: publicada, no bloqueada y con
    `has_ecommerce` en el plan del dueño — las membresías del comercio
    son superficie de venta online. Sin el beneficio es 404 (misma
    política de ocultamiento: un Customer GLOBAL con sesión válida no
    desbloquea la tienda de un plan caído).
    """
    store   =   Store.objects.filter(
        slug = (slug or '').strip().lower(), is_published = True, is_blocked = False,
    ).select_related('user', 'customization').first()
    if store is None:
        raise Http404
    from StoreApp.domains.stores.services.commerce import store_has_ecommerce
    if not store_has_ecommerce(store):
        raise Http404
    return store
def _payment_config(store):
    #Reverse O2O: DoesNotExist es subclase de AttributeError -> default OK.
    return getattr(store, 'payment_config', None)
def _mp_connected(store):
    account =   getattr(store, 'mp_account', None)
    return bool(account and account.is_connected)
def _payment_instructions(store):
    """
    Cómo paga el cliente la suscripción: los métodos de cobro del
    vendedor (StorePaymentConfig/StoreMpAccount — la plata va directo
    al dueño, DAVENT nunca la toca) + deadline para acreditar.
    """
    cfg     =   _payment_config(store)
    mp_on   =   bool(cfg.mp_enabled) if cfg else True
    return {
        'accept_transfer'       :   cfg.accept_transfer if cfg else True,
        'transfer_alias'        :   cfg.transfer_alias if cfg else '',
        'transfer_holder'       :   cfg.transfer_holder if cfg else '',
        'transfer_instructions' :   cfg.transfer_instructions if cfg else '',
        'accept_whatsapp'       :   cfg.accept_whatsapp if cfg else True,
        'whatsapp_number'       :   cfg.whatsapp_number if cfg else '',
        'accept_cash'           :   cfg.accept_cash if cfg else False,
        'mp_enabled'            :   mp_on,
        'mp_connected'          :   mp_on and _mp_connected(store),
        'deadline_hours'        :   cfg.payment_deadline_hours if cfg else 48,
    }
def _allowed_payment_methods(store):
    """Métodos que el cliente puede elegir según la config del vendedor."""
    cfg     =   _payment_config(store)
    methods =   {'manual'}    #manual = el dueño acredita como los pedidos
    if cfg is None or cfg.accept_transfer:
        methods.add('transfer')
    if cfg is None or cfg.accept_whatsapp:
        methods.add('whatsapp')
    if cfg is not None and cfg.accept_cash:
        methods.add('cash')
    if _mp_connected(store) and (cfg is None or cfg.mp_enabled):
        methods.add('mp')
    return methods
def _current_subscription(store, customer):
    """
    La suscripción "vigente" para el comprador: la que otorga beneficios
    ahora; si no hay, la pending más reciente (pago en curso). None si
    no tiene ninguna relevante.
    """
    current =   active_subscription_of(customer, store)
    if current is not None:
        return current
    membership   =   StoreMembership.objects.filter(customer = customer, store = store).first()
    if membership is None:
        return None
    return (
        membership.subscriptions
        .filter(status = StoreSubscription.STATUS_PENDING)
        .order_by('-created_at', '-id')
        .first()
    )
#=========================================
# CUSTOMER SUBSCRIPTIONS (todas las del comprador)
#=========================================
class CustomerSubscriptionsView(generics.ListAPIView):
    """
    GET /api/customer/subscriptions/ — historial de suscripciones del
    comprador en todas las tiendas (plan + store + is_vigente +
    benefits por fila; paginado por el default del proyecto).
    """
    serializer_class        =   StoreSubscriptionCustomerSerializer
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get_queryset(self):
        return (
            StoreSubscription.objects
            .filter(membership__customer = self.request.customer)
            .select_related('plan', 'membership__store__user', 'membership__store__customization')
            .order_by('-created_at', '-id')
        )
#=========================================
# STORE PLANS + SUBSCRIBE (por tienda)
#=========================================
class CustomerStorePlansView(APIView):
    """
    GET  /api/customer/subscriptions/<store_slug>/ → planes activos de
    la tienda + MI suscripción vigente/pendiente + mis beneficios.
    POST /api/customer/subscriptions/<store_slug>/ {plan_id,
    payment_method?} → crea la suscripción 'pending' (cobro manual como
    los pedidos) + asegura la StoreMembership + instrucciones de pago.
    """
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get(self, request, store_slug):
        store       =   _public_store_or_404(store_slug)
        customer    =   request.customer
        subscription    =   _current_subscription(store, customer)
        return Response({
            'store'         :   {'slug': store.slug, 'name': store_display_name(store)},
            'plans'         :   StorePlanPublicSerializer(
                StorePlan.objects.filter(store = store, is_active = True), many = True,
            ).data,
            'subscription'  :   StoreSubscriptionCustomerSerializer(subscription).data if subscription else None,
            'benefits'      :   sorted(member_benefits(customer, store)),
        }, status = status.HTTP_200_OK)
    def post(self, request, store_slug):
        store       =   _public_store_or_404(store_slug)
        customer    =   request.customer
        data        =   request.data if isinstance(request.data, dict) else {}
        plan_id     =   data.get('plan_id')
        try:
            plan    =   StorePlan.objects.filter(pk = plan_id, store = store, is_active = True).first()
        except (TypeError, ValueError):
            #plan_id no numérico ('abc', dict, lista): 404 controlado,
            #nunca un 500 por el cast del lookup.
            plan    =   None
        if plan is None:
            return Response({'plan_id': ['El plan no existe o no está disponible.']}, status = status.HTTP_404_NOT_FOUND)
        payment_method  =   str(data.get('payment_method') or StoreSubscription.PAYMENT_MANUAL).strip()
        if payment_method not in _allowed_payment_methods(store):
            return Response(
                {'payment_method': [f'Medio de pago no disponible en esta tienda. Opciones: {", ".join(sorted(_allowed_payment_methods(store)))}.']},
                status = status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                #ensure_membership lanza MembershipSuspended (403) si la
                #tienda suspendió al comprador — el alta no bypasea.
                membership   =   ensure_membership(customer, store)
                #Read-modify-write bajo lock de la membresía: dos POST
                #concurrentes se serializan y el segundo ve la pending
                #del primero (la unique parcial es la segunda capa).
                membership   =   StoreMembership.objects.select_for_update().get(pk = membership.pk)
                now         =   timezone.now()
                blocking    =   (
                    membership.subscriptions
                    .filter(
                        Q(status = StoreSubscription.STATUS_PENDING)
                        | Q(status = StoreSubscription.STATUS_ACTIVE, vigente_hasta__gt = now)
                    )
                    .order_by('-created_at', '-id')
                    .first()
                )
                if blocking is not None:
                    return Response(
                        {
                            'detail'        :   'Ya tenés una suscripción pendiente de pago o vigente en esta tienda.',
                            'subscription'  :   StoreSubscriptionCustomerSerializer(blocking).data,
                        },
                        status = status.HTTP_409_CONFLICT,
                    )
                subscription    =   StoreSubscription.objects.create(
                    membership      =   membership,
                    plan            =   plan,
                    status          =   StoreSubscription.STATUS_PENDING,
                    payment_method  =   payment_method,
                )
        except IntegrityError:
            #Carrera residual: la unique parcial (membership, status=
            #pending) cortó el segundo insert — mismo 409 idempotente.
            membership   =   StoreMembership.objects.filter(customer = customer, store = store).first()
            existing     =   membership.subscriptions.filter(status = StoreSubscription.STATUS_PENDING).order_by('-created_at', '-id').first() if membership else None
            return Response(
                {
                    'detail'        :   'Ya tenés una suscripción pendiente de pago o vigente en esta tienda.',
                    'subscription'  :   StoreSubscriptionCustomerSerializer(existing).data if existing else None,
                },
                status = status.HTTP_409_CONFLICT,
            )
        #Campana del comprador: la suscripción quedó pendiente de pago
        #(best-effort — nunca rompe el alta ya persistida).
        try:
            from StoreApp.domains.customers.services.notifications import notify_customer_subscription
            notify_customer_subscription(subscription, StoreSubscription.STATUS_PENDING)
        except Exception:                                   # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception('memberships customer: notification falló (sub=%s)', getattr(subscription, 'pk', None))
        return Response(
            {
                'Exito'         :   'Suscripción creada. Completá el pago con los datos de la tienda para activarla.',
                'subscription'  :   StoreSubscriptionCustomerSerializer(subscription).data,
                'payment'       :   _payment_instructions(store),
            },
            status = status.HTTP_201_CREATED,
        )
#=========================================
# MY DIGITAL CARD (autenticado)
#=========================================
class CustomerSubscriptionCardView(APIView):
    """
    GET /api/customer/subscriptions/<store_slug>/card/ — datos de MI
    tarjeta digital. Requiere suscripción vigente Y que el plan incluya
    el beneficio has_digital_card; membresía suspendida -> 403.
    """
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get(self, request, store_slug):
        store       =   _public_store_or_404(store_slug)
        customer    =   request.customer
        membership  =   StoreMembership.objects.filter(customer = customer, store = store).select_related('customer').first()
        if membership is None:
            return Response({'detail': 'No tenés membresía en esta tienda.'}, status = status.HTTP_404_NOT_FOUND)
        if membership.status == StoreMembership.STATUS_SUSPENDED:
            return Response({'detail': 'Tu cuenta está suspendida en esta tienda.'}, status = status.HTTP_403_FORBIDDEN)
        subscription    =   active_subscription_of(customer, store)
        if subscription is None:
            return Response({'detail': 'No tenés una suscripción vigente en esta tienda.'}, status = status.HTTP_404_NOT_FOUND)
        if not subscription.plan.has_digital_card:
            return Response({'detail': 'Tu plan actual no incluye tarjeta digital.'}, status = status.HTTP_403_FORBIDDEN)
        return Response(MembershipCardSerializer(subscription).data, status = status.HTTP_200_OK)
#=========================================
# EXCLUSIVE PRODUCTS (solo miembros con exclusive_access)
#=========================================
class CustomerExclusiveProductsView(APIView):
    """
    GET /api/customer/stores/<store_slug>/exclusive-products/ — los
    Product.is_exclusive de la tienda para quien tiene
    has_exclusive_access vigente. Sin acceso -> 404 (ni se revela que
    existen). Mismo serializer/precio efectivo que el catálogo público.
    """
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get(self, request, store_slug):
        store       =   _public_store_or_404(store_slug)
        customer    =   request.customer
        if not has_exclusive_access(customer, store):
            raise Http404
        products    =   (
            Product.objects
            .filter(store = store, is_active = True, is_exclusive = True)
            .select_related('category', 'brand')
            .order_by('name', 'id')
        )
        #Mismo cálculo de oferta efectiva que _public_catalog_data:
        #menor entre oferta manual y mejor descuento vigente.
        discounts   =   running_discounts_of(store)
        items       =   []
        for product in products:
            product.effective_offer, product.effective_discount   =   effective_pricing_of(product, discounts)
            items.append(product)
        return Response({'products': ProductPublicSerializer(items, many = True).data}, status = status.HTTP_200_OK)
#=========================================
# PUBLIC MEMBERSHIP CARD (sin auth — pase del miembro para el staff)
#=========================================
class MembershipCardPublicView(APIView):
    """
    GET /api/membership-cards/<store_slug>/<public_token>/ — tarjeta
    digital pública: la URL la ve el staff del comercio (o el propio
    miembro). Sin autenticación a propósito (el token es el identificador
    unguessable) pero con payload mínimo: nombre + inicial, tienda, plan,
    vigencia y beneficios — jamás email/teléfono/documento.
    Solo responde con suscripción vigente y plan con has_digital_card;
    cualquier otro caso -> 404 (no se revela estado ni existencia).

    Gate por plan: NINGUNO — es un documento ya emitido por token
    unguessable (misma doctrina que el tracking de pedidos: una baja de
    plan no invalida la credencial del miembro). Las membresías NUEVAS
    sí se gatean en _public_store_or_404 (has_ecommerce).
    """
    permission_classes      =   [AllowAny]
    #Cero autenticadores: un Bearer vencido del dueño no debe romper el
    #pase (mismo criterio que PUBLIC_ACTIONS del StoreViewSet).
    authentication_classes  =   []
    throttle_classes        =   [PublicReadThrottle]
    def get(self, request, store_slug, public_token):
        subscription    =   (
            StoreSubscription.objects
            .filter(public_token = public_token, membership__store__slug = (store_slug or '').strip().lower())
            .select_related('plan', 'membership__customer', 'membership__store__user', 'membership__store__customization')
            .first()
        )
        if subscription is None:
            raise Http404
        plan            =   subscription.plan
        #La tarjeta es un beneficio: membresía suspendida -> no vale
        #aunque la suscripción siga 'active' (mismo filtro que
        #_vigente_subscriptions de benefits.py).
        vigente         =   (
            subscription.membership.status == StoreMembership.STATUS_ACTIVE
            and subscription.status == StoreSubscription.STATUS_ACTIVE
            and subscription.vigente_hasta is not None
            and subscription.vigente_hasta > timezone.now()
        )
        if not (vigente and plan is not None and plan.has_digital_card):
            raise Http404
        return Response(MembershipCardSerializer(subscription).data, status = status.HTTP_200_OK)
