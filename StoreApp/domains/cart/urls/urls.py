from django.urls import path

from StoreApp.domains.cart.views import (
    CartItemsView,
    CartItemView,
    CartView,
)

#=========================================
# CART URLS (se incluyen bajo /api/)
#=========================================
#Un carrito por comprador y tienda: las rutas llevan el slug de la web.
urlpatterns = [
    path('cart/<slug:slug>/',                  CartView.as_view(),       name = 'cart'),
    path('cart/<slug:slug>/items/',            CartItemsView.as_view(),  name = 'cart-items'),
    path('cart/<slug:slug>/items/<int:item_id>/', CartItemView.as_view(), name = 'cart-item'),
]
