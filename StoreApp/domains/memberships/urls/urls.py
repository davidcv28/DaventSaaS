from django.urls import path
from rest_framework import routers

from StoreApp.domains.memberships.views import (
    CustomerExclusiveProductsView,
    CustomerStorePlansView,
    CustomerSubscriptionCardView,
    CustomerSubscriptionsView,
    MembershipCardPublicView,
    PublicStorePlansView,
    StorePlanViewSet,
    StoreSubscriptionViewSet,
)

"""

URLs del dominio memberships (prefijo /api/ en DaventProject/urls.py):

DUEÑO (JWT DAVENT, scope a su tienda — IDOR 404):
- /api/store-plans/                      CRUD de planes (router).
- /api/store-subscriptions/              suscripciones de SUS clientes
  (?status= filtra) + /<id>/activate|cancel|expire/.

COMPRADOR (customer JWT — request.customer):
- /api/customer/subscriptions/           todas sus suscripciones.
- /api/customer/subscriptions/<slug>/    planes de la tienda + la suya
  (GET) y contratación pending (POST).
- /api/customer/subscriptions/<slug>/card/  su tarjeta digital.
- /api/customer/stores/<slug>/exclusive-products/  exclusivos p/ miembros.

PÚBLICO:
- /api/membership-cards/<slug>/<token>/  tarjeta digital por token.
- /api/stores/public/<slug>/membership-plans/  planes activos + cobro.

Nota: /api/customer/memberships/ la sirve el dominio customers (track
A) — acá no se duplica.

"""
router  =   routers.DefaultRouter()

#OWNER ROUTERS (dueño autenticado; scope a su tienda)
router.register(r'store-plans',          StorePlanViewSet,          basename = 'StorePlans')
router.register(r'store-subscriptions',  StoreSubscriptionViewSet,  basename = 'StoreSubscriptions')

urlpatterns = [
    #CUSTOMER (JWT de comprador)
    path('customer/subscriptions/',                                  CustomerSubscriptionsView.as_view(),           name = 'customer_subscriptions'),
    path('customer/subscriptions/<slug:store_slug>/',                CustomerStorePlansView.as_view(),               name = 'customer_store_plans'),
    path('customer/subscriptions/<slug:store_slug>/card/',           CustomerSubscriptionCardView.as_view(),          name = 'customer_subscription_card'),
    path('customer/stores/<slug:store_slug>/exclusive-products/',    CustomerExclusiveProductsView.as_view(),         name = 'customer_exclusive_products'),
    #MEMBERSHIP CARD (público por token)
    path('membership-cards/<slug:store_slug>/<str:public_token>/',   MembershipCardPublicView.as_view(),             name = 'membership_card_public'),
    #PLANES DE LA TIENDA (público — página Suscripciones)
    path('stores/public/<slug:slug>/membership-plans/',              PublicStorePlansView.as_view(),                  name = 'public_membership_plans'),
] + router.urls
