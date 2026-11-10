from django.urls import path
from rest_framework import routers

from StoreApp.domains.orders.views import StoreOrderViewSet
from StoreApp.domains.orders.views.public import (
    OrderCaptchaView,
    PublicOrderCreateView,
    PublicOrderEventsView,
    PublicOrderProofView,
    PublicOrderReceiptView,
    PublicOrderTrackView,
)

#=========================================
# ORDERS URLS (se incluyen bajo /api/)
#=========================================
#Públicas: /api/stores/public/<slug>/orders/... — conviven con las rutas
#del router de stores (sus url_path están anclados, no pisan estos paths).
#Panel del dueño: /api/store-orders/ (basename del router).
router  =   routers.DefaultRouter()
router.register(r'store-orders', StoreOrderViewSet, basename = 'store-orders')
urlpatterns = [
    path('stores/public/<slug:slug>/orders/captcha/',                  OrderCaptchaView.as_view(),      name = 'order-captcha'),
    path('stores/public/<slug:slug>/orders/',                          PublicOrderCreateView.as_view(), name = 'order-create'),
    path('stores/public/<slug:slug>/orders/<str:tracking_token>/',     PublicOrderTrackView.as_view(),  name = 'order-track'),
    path('stores/public/<slug:slug>/orders/<str:tracking_token>/events/', PublicOrderEventsView.as_view(), name = 'order-events'),
    path('stores/public/<slug:slug>/orders/<str:tracking_token>/proof/',  PublicOrderProofView.as_view(), name = 'order-proof'),
    path('stores/public/<slug:slug>/orders/<str:tracking_token>/receipt/', PublicOrderReceiptView.as_view(), name = 'order-receipt'),
] + router.urls
