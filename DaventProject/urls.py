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
from django.http import FileResponse, Http404, JsonResponse
from django.urls import path, include, re_path


def healthz(request):
    # Healthcheck de contenedores (Docker/compose) y monitores: 200 si el
    # proceso WSGI responde. No toca la DB a propósito.
    return JsonResponse({'status': 'ok'})
from rest_framework_simplejwt.views import TokenVerifyView
from AdminApp.domains.users.views.auth_views import (
    CustomTokenObtainPairView,
    CookieTokenRefreshView,
    TokenLogoutView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    VerifyEmailView,
    VerifyEmailResendView,
    GoogleAuthView,
    PublicConfigView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    #ADMIN_URL por env: en prod un path no obvio reduce el ruido de bots que
    #escanean /admin/ (su login no tiene rate-limit propio). Default 'admin/'.
    path(settings.ADMIN_URL, admin.site.urls),
    #=================================
    # DOMAINS URLS
    #=================================
    path('api/', include('AdminApp.domains.suscriptions.urls.urls')),
    path('api/', include('AdminApp.domains.users.urls.urls')),
    path('api/', include('AdminApp.domains.locations.urls.urls')),
    path('api/', include('AdminApp.domains.payments.urls.urls')),
    path('api/', include('AdminApp.domains.invoices.urls.urls')),
    path('api/', include('AdminApp.domains.legal.urls.urls')),
    path('api/', include('AdminApp.domains.chat.urls.urls')),
    path('api/', include('SuscriptionApp.domains.benefits.urls.urls')),
    path('api/', include('StoreApp.domains.stores.urls.urls')),
    path('api/', include('StoreApp.domains.catalog.urls.urls')),
    #=================================
    # JWT
    #=================================
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/logout/', TokenLogoutView.as_view(), name='token_logout'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    #=================================
    # CUENTA (reset de contraseña + verificación de correo)
    #=================================
    path('api/password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('api/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('api/verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('api/verify-email/resend/', VerifyEmailResendView.as_view(), name='verify_email_resend'),
    #=================================
    # CONFIG PÚBLICA DEL FRONTEND (servida en runtime — no horneada en el
    # bundle: el client ID de Google sale del env del backend, nunca del
    # código ni del build de la imagen)
    #=================================
    path('api/config/', PublicConfigView.as_view(), name='public_config'),
    #=================================
    # LOGIN SOCIAL (Google — token exchange, mismo JWT/cookies)
    #=================================
    path('api/auth/google/', GoogleAuthView.as_view(), name='auth_google'),
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


def spa(request):
    # Catch-all del frontend empaquetado: los assets del build (fingerprint)
    # los sirve whitenoise vía STATICFILES_DIRS; cualquier ruta de la SPA
    # (/register, /dashboard, /<slug>) cae acá y devuelve index.html.
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.is_file():
        raise Http404
    resp = FileResponse(index.open('rb'), content_type='text/html')
    # El HTML jamás se cachea: referencia los chunks hasheados del deploy
    # vigente. Si el browser guardara uno viejo, pediría assets que ya no
    # existen y la app quedaría en blanco tras cada deploy.
    resp['Cache-Control'] = 'no-cache, must-revalidate'
    # CSP del SPA: recursos propios + Google Fonts (estilos on-demand del catálogo
    # de fuentes), iframe de Google Maps (mapa de ubicación), imágenes https (R2)
    # y data: (favicon inline / QR). Los scripts son solo archivos del build más
    # el SDK de Google Identity Services (accounts.google.com: script, frame del
    # botón, connect del exchange y su stylesheet); el frame cubre también el
    # iframe del botón de Google. Sin ellos ese login quedaba roto únicamente
    # en el deploy empaquetado (en dev la CSP no aplica porque la SPA la sirve Vite).
    # COOP: el default de SecurityMiddleware es 'same-origin', que aísla el
    # popup de Google (window.opener = null) y el login social quedaba en
    # blanco tras el consent — el popup no puede postMessagear la credencial.
    # 'same-origin-allow-popups' conserva la referencia en popups que abrimos.
    resp['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    resp['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://accounts.google.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com/gsi/style; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://accounts.google.com; "
        "frame-src https://maps.google.com https://www.google.com https://accounts.google.com; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    return resp


if settings.FRONTEND_DIST.is_dir():
    # Las rutas con pinta de archivo (…/x.js, /robots.txt) NO caen al SPA: si
    # el asset no existe es un 404 real — devolver index.html con MIME
    # text/html rompe los imports dinámicos (chunk viejo tras un deploy).
    urlpatterns += [re_path(r'^(?!api/|admin/|static/|media/|healthz/|.*\.[a-z0-9]{2,8}$).*$', spa, name='spa')]
