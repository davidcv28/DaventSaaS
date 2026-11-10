from django.urls import path
from rest_framework import routers

from StoreApp.domains.support.views import (
    CustomerSupportMessageCreateView,
    CustomerSupportThreadCloseView,
    CustomerSupportThreadDetailView,
    CustomerSupportThreadListCreateView,
    StoreSupportThreadViewSet,
)

"""

URLs del dominio support (se incluyen bajo /api/ en
DaventProject/urls.py).

COMPRADOR (customer JWT — request.customer):
- /api/support/threads/                 GET lista + POST alta de hilo.
- /api/support/threads/<id>/            GET detalle + mensajes.
- /api/support/threads/<id>/messages/   POST responder.
- /api/support/threads/<id>/close/      POST cerrar (solo el comprador;
  reabrir es del dueño).

DUEÑO (JWT DAVENT, scope a su tienda — IDOR 404):
- /api/store-support/threads/           GET bandeja (?status=&unread=).
- /api/store-support/threads/<id>/      GET detalle + mensajes.
- /api/store-support/threads/<id>/messages/  POST responder.
- /api/store-support/threads/<id>/close/     POST cerrar.
- /api/store-support/threads/<id>/reopen/    POST reabrir.

Nota: NO confundir con /api/chat/ (AdminApp.domains.chat — soporte
interno del usuario DAVENT con el staff de la plataforma).
"""
router  =   routers.DefaultRouter()
router.register(r'store-support/threads', StoreSupportThreadViewSet, basename = 'store-support-threads')
urlpatterns = [
    #CUSTOMER (JWT de comprador)
    path('support/threads/',                    CustomerSupportThreadListCreateView.as_view(),   name = 'support_threads'),
    path('support/threads/<int:pk>/',           CustomerSupportThreadDetailView.as_view(),      name = 'support_thread_detail'),
    path('support/threads/<int:pk>/messages/',  CustomerSupportMessageCreateView.as_view(),    name = 'support_thread_messages'),
    path('support/threads/<int:pk>/close/',     CustomerSupportThreadCloseView.as_view(),       name = 'support_thread_close'),
] + router.urls
