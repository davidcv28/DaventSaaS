from django.urls import path

from StoreApp.domains.storepayments.views import (
    MpConnectView,
    MpDisconnectView,
    MpRefundView,
    MpStatusView,
    PublicOrderPayView,
    StoreMpWebhookView,
    StorePaymentConfigView,
)

#=========================================
# STORE PAYMENTS URLS (se incluyen bajo /api/)
#=========================================
#Dueño (auth): cuenta MP propia + config de métodos manuales + reembolso.
#Comprador (público): pay del pedido por tracking_token.
#Webhook: notificaciones IPN de la app MP del vendedor (auth por firma).
urlpatterns = [
    #MP DEL DUEÑO
    path('store-payments/mp/status/', MpStatusView.as_view(), name = 'store-mp-status'),
    path('store-payments/mp/connect/', MpConnectView.as_view(), name = 'store-mp-connect'),
    path('store-payments/mp/disconnect/', MpDisconnectView.as_view(), name = 'store-mp-disconnect'),
    #Reembolso: ruta propia de storepayments para no pisar /api/store-orders/
    #(dominio orders, track B). El service refund_payment(order, actor)
    #queda disponible para que B lo enchufe donde prefiera.
    path('store-payments/mp/refund/<int:order_id>/', MpRefundView.as_view(), name = 'store-mp-refund'),
    #CONFIG DE COBROS (métodos manuales — fiscal/OAuth/storage: otros tracks)
    path('store-payments/config/', StorePaymentConfigView.as_view(), name = 'store-payment-config'),
    #CHECKOUT MP DEL COMPRADOR (público)
    path('stores/public/<slug:slug>/orders/<str:tracking_token>/pay/', PublicOrderPayView.as_view(), name = 'store-order-mp-pay'),
    #WEBHOOK MP DEL VENDEDOR (firma x-signature por slug)
    path('webhooks/store-mp/<slug:slug>/', StoreMpWebhookView.as_view(), name = 'store-mp-webhook'),
]
