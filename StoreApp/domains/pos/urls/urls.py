from django.urls import path

from StoreApp.domains.pos.views import (
    PosAppsView,
    PosDownloadView,
    PosLicenseView,
    PosPairCodeView,
    PosPairView,
)

"""
URLs del dominio POS (incluidas bajo /api/ por DaventProject/urls).

Dueño: pair-code + apps (sesión DAVENT, su tienda — IDOR 404).
Dispositivo: pair (anónimo, throttled) y license (device_token Bearer).
"""
urlpatterns = [
    #=========================================
    # DUEÑO
    #=========================================
    path('pos/pair-code/', PosPairCodeView.as_view(), name = 'pos-pair-code'),
    path('pos/apps/', PosAppsView.as_view(), name = 'pos-apps'),
    path('pos/download/<slug:slug>/', PosDownloadView.as_view(), name = 'pos-download'),
    #=========================================
    # DISPOSITIVO (app de mostrador)
    #=========================================
    path('pos/pair/', PosPairView.as_view(), name = 'pos-pair'),
    path('pos/license/', PosLicenseView.as_view(), name = 'pos-license'),
]
