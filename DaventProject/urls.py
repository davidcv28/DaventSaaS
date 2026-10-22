"""
URL configuration for DaventProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView
)
from AdminApp.domains.users.views.auth_views import CustomTokenObtainPairView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
urlpatterns = [
    path('admin/', admin.site.urls),
    #=================================
    # DOMAINS URLS
    #=================================
    path('api/', include('AdminApp.domains.suscriptions.urls.urls')),
    path('api/', include('AdminApp.domains.users.urls.urls')),
    path('api/', include('AdminApp.domains.locations.urls.urls')),
    path('api/', include('AdminApp.domains.payments.urls.urls')),
    path('api/', include('AdminApp.domains.invoices.urls.urls')),
    path('api/', include('AdminApp.domains.legal.urls.urls')),
    path('api/', include('SuscriptionApp.domains.benefits.urls.urls')),
    path('api/', include('StoreApp.domains.stores.urls.urls')),
    path('api/', include('StoreApp.domains.catalog.urls.urls')),
    #=================================
    # JWT
    #=================================
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]

# Solo en desarrollo: el schema OpenAPI y los docs interactivos exponen la
# estructura completa de la API; en producción quedan cerrados (404). Lo
# mismo para el login de la browsable API de DRF.
if settings.DEBUG:
    urlpatterns += [
        path("api-auth/", include("rest_framework.urls")),
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
