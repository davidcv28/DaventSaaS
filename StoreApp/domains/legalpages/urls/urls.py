from django.urls import path, re_path

from StoreApp.domains.legalpages.views import (
    PublicLegalCaptchaView,
    PublicLegalIndexView,
    PublicLegalPageView,
    PublicReturnRequestView,
    ReturnRequestStatusView,
    ReturnRequestsView,
    StoreLegalPageDetailView,
    StoreLegalPagesView,
)

"""
URLs del dominio legalpages (incluidas bajo /api/ por DaventProject/urls).

Dueño: store-legal-pages/* — siempre resuelven la tienda del usuario
logueado (IDOR = 404). Público: stores/public/<slug>/legal/* — misma
regla de visibilidad que el resto de la web pública de la tienda.

OJO con el solape 'returns': es kind de página Y bandeja de solicitudes.
/api/store-legal-pages/returns/ despacha por método (GET = bandeja,
PUT = publicar/ocultar la página 'returns'); /returns/<id>/status/
sigue su propia ruta. En el frente público no hay choque porque
/legal/returns/request/ tiene un segmento más que /legal/<kind>/.
"""
urlpatterns = [
    #=========================================
    # DUEÑO (auth DAVENT — su tienda)
    #=========================================
    path('store-legal-pages/', StoreLegalPagesView.as_view(), name = 'legal-pages-list'),
    #La bandeja y la página 'returns' comparten path: GET = solicitudes,
    #PUT = editar la página legal de devoluciones.
    path('store-legal-pages/returns/', ReturnRequestsView.as_view(), name = 'legal-return-requests'),
    re_path(r'^store-legal-pages/returns/(?P<pk>[0-9]+)/status/$', ReturnRequestStatusView.as_view(), name = 'legal-return-status'),
    re_path(r'^store-legal-pages/(?P<kind>terms|privacy|returns)/$', StoreLegalPageDetailView.as_view(), name = 'legal-page-detail'),
    #=========================================
    # PÚBLICO (web de la tienda)
    #=========================================
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/legal/$', PublicLegalIndexView.as_view(), name = 'public-legal-index'),
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/legal/captcha/$', PublicLegalCaptchaView.as_view(), name = 'public-legal-captcha'),
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/legal/(?P<kind>terms|privacy|returns)/$', PublicLegalPageView.as_view(), name = 'public-legal-page'),
    re_path(r'^stores/public/(?P<slug>[a-z0-9-]+)/legal/returns/request/$', PublicReturnRequestView.as_view(), name = 'public-return-request'),
]
