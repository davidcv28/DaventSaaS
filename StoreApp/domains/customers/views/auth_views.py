"""
Vistas de autenticación de COMPRADORES (e-commerce DAVENT).

Prefijo `/api/customer-auth/` — cuenta separada de la cuenta SaaS
(auth.User/UserProfile del dueño): nada de estos endpoints toca
`/api/token/`, `/api/auth/` ni las cookies `davent_*`.

Sesión: access JWT en el body (lo guarda el front en memoria, 30 min) +
refresh en cookie httpOnly `customer_refresh` (Path=/api/, 30 días,
SameSite=Lax, Secure si no DEBUG) con doble-submit CSRF `customer_csrf`
(Path=/, legible por JS) — mismo patrón que auth_views.py de users.
"""
import logging
import secrets
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.utils import datetime_from_epoch

from DaventProject.middleware import client_ip as _client_ip
from DaventProject.throttling import _ResilientThrottleMixin
from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
    customer_session_valid,
)
from StoreApp.domains.customers.models import Customer
from StoreApp.domains.customers.serializers import (
    CustomerLoginSerializer,
    CustomerPasswordResetConfirmSerializer,
    CustomerPasswordResetRequestSerializer,
    CustomerProfileUpdateSerializer,
    CustomerRegisterSerializer,
    CustomerSerializer,
    CustomerVerifyEmailSerializer,
    GoogleLoginSerializer,
)
from StoreApp.domains.customers.services.customers import (
    ConfirmCustomerPasswordResetQuery,
    MembershipSuspended,
    RegisterCustomerQuery,
    RequestCustomerPasswordResetQuery,
    SendCustomerVerificationEmailQuery,
    VerifyCustomerEmailQuery,
    authenticate_customer,
    ensure_membership,
    mark_login,
    resolve_store,
)
from StoreApp.domains.customers.services.google import (
    GoogleAuthError,
    google_customer_login,
    store_google_client_id,
    verify_google_credential,
)
from StoreApp.domains.customers.services.tokens import (
    CustomerRefreshToken,
    issue_customer_tokens,
    parse_refresh_token,
)

logger  =   logging.getLogger(__name__)
#=====================================
# COOKIES DE SESIÓN DE COMPRADOR
#=====================================
REFRESH_COOKIE   =   'customer_refresh'
CSRF_COOKIE      =   'customer_csrf'
COOKIE_PATH      =   '/api/'
#Refresh siempre persistente 30 días (el cliente vuelve a comprar semanas
#después; no hay flag "recordar" como en DAVENT — documentado).
REFRESH_MAX_AGE  =   int(30 * 24 * 60 * 60)

def _secure():
    #Secure solo bajo HTTPS real (prod); en dev http://localhost se omite.
    return settings.SESSION_COOKIE_SECURE

def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        REFRESH_COOKIE, str(refresh_token),
        max_age = REFRESH_MAX_AGE, path = COOKIE_PATH,
        httponly = True, secure = _secure(), samesite = 'Lax',
    )

def _set_csrf_cookie(response):
    #Doble-submit: el JS la lee (document.cookie) y la devuelve en
    #X-CSRFToken. Path=/ para que sea visible desde cualquier página.
    response.set_cookie(
        CSRF_COOKIE, secrets.token_urlsafe(32),
        max_age = REFRESH_MAX_AGE, path = '/',
        secure = _secure(), samesite = 'Lax',
    )

def _clear_session_cookies(response):
    response.delete_cookie(REFRESH_COOKIE, path = COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path = '/')

def _require_csrf(request):
    """Doble-submit: X-CSRFToken debe matchear la cookie CSRF."""
    cookie  =   request.COOKIES.get(CSRF_COOKIE)
    header  =   request.headers.get('X-CSRFToken')
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise PermissionDenied('CSRF token inválido o ausente')


def _session_origin_allowed(request):
    """
    Anti login-CSRF: los endpoints que EMITEN la sesión por cookie
    (register/login/google) solo aceptan POST desde orígenes confiables.
    Un POST cross-site de otro sitio puede hacer que el browser de la
    víctima quede logueado en la cuenta del atacante (Set-Cookie aplica
    igual aunque SameSite=Lax). Los browsers siempre mandan Origin (o
    Referer) en POST; un request sin ninguno es un cliente no-browser
    (app móvil, curl) sin contexto de cookies ajenas → se permite.

    Orígenes válidos: el mismo host del API (path-alias), CORS_ALLOWED_
    ORIGINS y CSRF_TRUSTED_ORIGINS — exactamente los orígenes desde los
    que el SPA puede tener una sesión legítima.
    """
    origin  =   (request.headers.get('Origin') or '').strip()
    if not origin:
        referer =   (request.headers.get('Referer') or '').strip()
        if referer:
            parsed  =   urlparse(referer)
            origin  =   f'{parsed.scheme}://{parsed.netloc}' if parsed.netloc else ''
    if not origin:
        return True
    host    =   (urlparse(origin).netloc or '').lower()
    if not host:
        return False
    if host == (request.get_host() or '').lower():
        return True
    trusted =   set()
    for o in list(getattr(settings, 'CORS_ALLOWED_ORIGINS', []) or []) + list(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []) or []):
        trusted.add((urlparse(o).netloc or o).lower())
    return host in trusted


def _session_response(request, customer, is_new = None):
    """
    Emite el par JWT y setea las cookies. `access` va en el body; el
    `refresh` NUNCA sale en la respuesta web (solo cookie httpOnly) —
    clientes API pueden mandar/recibir refresh por body si lo necesitan.
    """
    access_str, refresh =   issue_customer_tokens(customer)
    payload     =   {'access': access_str, 'customer': CustomerSerializer(customer).data}
    if is_new is not None:
        payload['is_new']   =   is_new
    response    =   Response(payload, status = status.HTTP_200_OK)
    _set_refresh_cookie(response, refresh)
    _set_csrf_cookie(response)
    return response


#=====================================
# THROTTLES — scopes de settings.py existentes (rates ya definidas:
# login/register/token_refresh/logout/password_reset/email_verification/
# social_auth/public_read/user). Keyed por customer.pk si hay sesión,
# si no por IP — NO se usa AnonRateThrottle porque saltaría la cuota a
# un comprador autenticado que golpee estos endpoints.
#=====================================
class CustomerRateThrottle(_ResilientThrottleMixin, SimpleRateThrottle):
    #Fail-open si el cache cae (misma política que el resto de throttles):
    #sin Redis estos endpoints devolvían 500 y la auth de compradores
    #quedaba caída por una falla de infraestructura ajena.
    scope   =   'user'
    def get_cache_key(self, request, view):
        customer    =   getattr(request, 'customer', None)
        ident       =   f'c{customer.pk}' if customer is not None else self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

class CustomerLoginThrottle(CustomerRateThrottle):
    scope   =   'login'

class CustomerRegisterThrottle(CustomerRateThrottle):
    scope   =   'register'

class CustomerRefreshThrottle(CustomerRateThrottle):
    scope   =   'token_refresh'

class CustomerLogoutThrottle(CustomerRateThrottle):
    scope   =   'logout'

class CustomerPasswordResetThrottle(CustomerRateThrottle):
    scope   =   'password_reset'

class CustomerPasswordResetConfirmThrottle(CustomerRateThrottle):
    #Scope 'password_reset_confirm' (settings): el confirm no envía mails —
    #bucket propio (30/h); compartir el de request dejaba al comprador sin
    #recuperar la clave tras reintentos del flujo completo.
    scope   =   'password_reset_confirm'

class CustomerVerifyEmailThrottle(CustomerRateThrottle):
    scope   =   'email_verification'

class CustomerSocialAuthThrottle(CustomerRateThrottle):
    scope   =   'social_auth'

class CustomerPublicReadThrottle(CustomerRateThrottle):
    scope   =   'public_read'

class CustomerApiThrottle(CustomerRateThrottle):
    #Endpoints autenticados del comprador (perfil, direcciones,
    #membresías, reenvío de verificación): bolsa 'user' de settings
    #keyeada por customer.pk — nunca por IP compartida.
    scope   =   'user'


#=====================================
# REGISTER / LOGIN / LOGOUT / REFRESH
#=====================================
class CustomerRegisterView(APIView):
    """
    POST /api/customer-auth/register/ {email, password, first_name?,
    last_name?, store_slug?} → crea la cuenta global, envía verificación
    por email y, si la tienda es válida, crea la StoreMembership.
    Devuelve {access, customer} + cookies de sesión.
    """
    permission_classes  =   [AllowAny]
    authentication_classes = [CustomerJWTAuthentication]
    throttle_classes    =   [CustomerRegisterThrottle]

    def post(self, request):
        if not _session_origin_allowed(request):
            raise PermissionDenied('Origen no permitido.')
        serializer  =   CustomerRegisterSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        store_slug  =   data.get('store_slug') or ''
        store       =   resolve_store(store_slug) if store_slug else None
        if store_slug and store is None:
            return Response({'store_slug': ['La tienda no existe o no está disponible.']}, status = status.HTTP_400_BAD_REQUEST)
        try:
            customer, _membership  =   RegisterCustomerQuery({**data, 'store': store})
        except MembershipSuspended:
            return Response({'detail': 'Tu cuenta está suspendida en esta tienda.'}, status = status.HTTP_403_FORBIDDEN)
        logger.info('Registro de cliente: customer_id=%s store=%s ip=%s', customer.pk, store.slug if store else '-', _client_ip(request))
        return _session_response(request, customer)


class CustomerLoginView(APIView):
    """
    POST /api/customer-auth/login/ {email, password, store_slug?} → JWT +
    cookies. Con store_slug asegura la membresía (auto-unión al entrar a
    comprar); membresía suspendida → 403.
    """
    permission_classes  =   [AllowAny]
    authentication_classes = [CustomerJWTAuthentication]
    throttle_classes    =   [CustomerLoginThrottle]

    def post(self, request):
        if not _session_origin_allowed(request):
            raise PermissionDenied('Origen no permitido.')
        serializer  =   CustomerLoginSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        customer    =   authenticate_customer(data['email'], data['password'])
        if customer is None:
            logger.warning('Login de cliente rechazado (ip=%s)', _client_ip(request))
            return Response({'detail': 'Email o contraseña incorrectos.'}, status = status.HTTP_401_UNAUTHORIZED)
        if not customer.is_active:
            return Response({'detail': 'Esta cuenta está inactiva. Contactá al comercio.'}, status = status.HTTP_403_FORBIDDEN)
        store_slug  =   data.get('store_slug') or ''
        if store_slug:
            store   =   resolve_store(store_slug)
            if store is None:
                return Response({'store_slug': ['La tienda no existe o no está disponible.']}, status = status.HTTP_400_BAD_REQUEST)
            try:
                ensure_membership(customer, store)
            except MembershipSuspended:
                return Response({'detail': 'Tu cuenta está suspendida en esta tienda.'}, status = status.HTTP_403_FORBIDDEN)
        mark_login(customer)
        return _session_response(request, customer)


class CustomerRefreshView(APIView):
    """
    POST /api/customer-auth/refresh/ → rota refresh+csrf y devuelve
    {access}. Web: lee la cookie httpOnly (exige CSRF doble-submit);
    clientes API: refresh en body (sin CSRF — no hay cookie).
    El refresh usado queda en blacklist (ROTATE) — replay = 401.
    """
    permission_classes  =   [AllowAny]
    authentication_classes = [CustomerJWTAuthentication]
    throttle_classes    =   [CustomerRefreshThrottle]

    def post(self, request):
        refresh     =   request.data.get('refresh')
        from_cookie =   False
        if not refresh:
            refresh     =   request.COOKIES.get(REFRESH_COOKIE)
            from_cookie =   bool(refresh)
        if from_cookie:
            _require_csrf(request)
        if not refresh:
            raise InvalidToken('Token de refresco ausente.')
        try:
            #Decode SIN verificar (firma incluida) solo para leer el jti y
            #tomar el lock de la fila OutstandingToken ANTES del check de
            #blacklist — un jti trucho solo crea una fila inerte, nunca una
            #sesión (la verificación real sigue abajo, dentro del lock).
            unverified  =   CustomerRefreshToken(refresh, verify = False)
        except TokenError as exc:
            raise InvalidToken(exc.args[0] if exc.args else 'Token inválido')
        try:
            #IDM-02 (replay concurrente): el verify→blacklist de SimpleJWT
            #es check-then-insert — dos requests con el MISMO refresh podían
            #pasar el check antes de que cualquiera escribiera la blacklist
            #y ambos rotaban (dos sesiones válidas). El get_or_create +
            #select_for_update sobre el jti serializa la rotación en
            #Postgres: el perdedor queda bloqueado hasta el commit del
            #ganador, y su check_blacklist ya ve la fila → 401.
            #(SQLite no honra select_for_update — la carrera se reproduce
            #solo en test/local; en Postgres la ventana queda cerrada.)
            with transaction.atomic():
                OutstandingToken.objects.select_for_update().get_or_create(
                    jti         =   unverified['jti'],
                    defaults    =   {
                        'token'      :   str(unverified),
                        'expires_at' :   datetime_from_epoch(unverified['exp']),
                    },
                )
                try:
                    old_refresh =   parse_refresh_token(refresh)
                except TokenError as exc:
                    #TokenError no es APIException: sin esto un refresh
                    #inválido o en blacklist sale como 500 (paridad
                    #CookieTokenRefreshView).
                    raise InvalidToken(exc.args[0] if exc.args else 'Token inválido')
                #Revocación global post-reset: un refresh emitido antes del
                #sello no puede renovarse.
                customer_id =   old_refresh.get('customer_id')
                customer    =   Customer.objects.filter(pk = customer_id, is_active = True).first() if customer_id else None
                if customer is None or not customer_session_valid(customer, old_refresh):
                    try:
                        old_refresh.blacklist()
                    except Exception:
                        pass
                    raise InvalidToken('La sesión fue revocada. Iniciá sesión de nuevo.')
                #Rotación: el refresh presentado queda blacklisteado y se
                #emite par nuevo. Fail-closed a propósito: si el blacklist
                #no puede escribirse el refresh viejo seguiría válido —
                #mejor 500 que una sesión duplicada (el lookup del customer
                #ya demostró que la DB responde).
                old_refresh.blacklist()
                access_str, new_refresh  =   issue_customer_tokens(customer)
        except InvalidToken:
            raise
        except TokenError as exc:
            raise InvalidToken(exc.args[0] if exc.args else 'Token inválido')
        response    =   Response({'access': access_str}, status = status.HTTP_200_OK)
        if from_cookie:
            _set_refresh_cookie(response, new_refresh)
            _set_csrf_cookie(response)
        else:
            #Cliente API (sin cookie): el nuevo refresh viaja en el body.
            response.data['refresh']    =   str(new_refresh)
        return response


class CustomerLogoutView(APIView):
    """
    POST /api/customer-auth/logout/ → blacklist del refresh de la cookie
    (o del body en clientes API) + limpieza de cookies. Idempotente.
    """
    permission_classes  =   [AllowAny]
    authentication_classes = [CustomerJWTAuthentication]
    throttle_classes    =   [CustomerLogoutThrottle]

    def post(self, request):
        refresh =   request.COOKIES.get(REFRESH_COOKIE)
        if refresh:
            _require_csrf(request)
        else:
            refresh =   request.data.get('refresh')
        if refresh:
            try:
                parse_refresh_token(refresh).blacklist()
            except Exception:
                pass  #token inválido/expirado: las cookies se limpian igual
        response    =   Response({'detail': 'Sesión cerrada.'}, status = status.HTTP_200_OK)
        _clear_session_cookies(response)
        return response


#=====================================
# ME (perfil del comprador autenticado)
#=====================================
class CustomerMeView(APIView):
    """
    GET/PATCH /api/customer-auth/me/ — perfil del comprador.
    PATCH whitelist: first_name, last_name, phone, document_type, document
    (email/password NO se editan por acá — ver CustomerProfileUpdateSerializer).
    """
    permission_classes      =   [IsCustomer]
    authentication_classes  =   [CustomerJWTAuthentication]

    def get(self, request):
        return Response({'customer': CustomerSerializer(request.customer).data})

    def patch(self, request):
        serializer  =   CustomerProfileUpdateSerializer(request.customer, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response({'customer': CustomerSerializer(request.customer).data})


#=====================================
# VERIFY EMAIL
#=====================================
class CustomerVerifyEmailView(APIView):
    """
    POST /api/customer-auth/verify-email/ {token} → marca el correo como
    verificado. El `token` es el firmado único del link del correo
    (django.core.signing, 24 h). Idempotente.
    """
    permission_classes      =   [AllowAny]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerVerifyEmailThrottle]

    def post(self, request):
        serializer  =   CustomerVerifyEmailSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        ok  =   VerifyCustomerEmailQuery(serializer.validated_data['token'])
        if not ok:
            return Response({'detail': 'El enlace es inválido o ya venció. Pedí uno nuevo.'}, status = status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Tu correo quedó verificado.'}, status = status.HTTP_200_OK)


class CustomerVerifyEmailResendView(APIView):
    """
    POST /api/customer-auth/verify-email/resend/ → reenvía el correo de
    verificación al customer autenticado (throttle email_verification).
    """
    permission_classes      =   [IsCustomer]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerVerifyEmailThrottle]

    def post(self, request):
        customer    =   request.customer
        if customer.email_verified:
            return Response({'detail': 'Tu correo ya está verificado.'}, status = status.HTTP_200_OK)
        SendCustomerVerificationEmailQuery(customer)
        return Response({'detail': 'Te reenviamos el correo de verificación. Revisá tu casilla (y el spam).'}, status = status.HTTP_200_OK)


#=====================================
# PASSWORD RESET
#=====================================
RESET_RESPONSE  =   'Si el correo está registrado, te va a llegar un enlace para restablecer tu contraseña.'

class CustomerPasswordResetRequestView(APIView):
    """
    POST /api/customer-auth/password-reset/ {email} → siempre 200 genérico
    (anti-enumeración); el mail sale solo si la cuenta existe.
    """
    permission_classes      =   [AllowAny]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerPasswordResetThrottle]

    def post(self, request):
        serializer  =   CustomerPasswordResetRequestSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        store_slug  =   (data.get('store_slug') or '').strip().lower()
        if store_slug and resolve_store(store_slug) is None:
            return Response({'store_slug': ['La tienda no existe o no está disponible.']}, status = status.HTTP_400_BAD_REQUEST)
        RequestCustomerPasswordResetQuery(data['email'], store_slug = store_slug)
        return Response({'detail': RESET_RESPONSE}, status = status.HTTP_200_OK)


class CustomerPasswordResetConfirmView(APIView):
    """
    POST /api/customer-auth/password-reset/confirm/ {uid, token,
    new_password, confirm_password} → valida el token firmado, aplica la
    policy de passwords y revoca todas las sesiones del cliente.
    """
    permission_classes      =   [AllowAny]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerPasswordResetConfirmThrottle]

    def post(self, request):
        serializer  =   CustomerPasswordResetConfirmSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        ConfirmCustomerPasswordResetQuery(serializer.validated_data['customer'], serializer.validated_data['new_password'])
        return Response({'detail': 'Tu contraseña se actualizó. Ya podés iniciar sesión con la clave nueva.'}, status = status.HTTP_200_OK)


#=====================================
# GOOGLE LOGIN (por tienda)
#=====================================
class CustomerGoogleConfigView(APIView):
    """
    GET /api/customer-auth/google-config/<store_slug>/ → {client_id, enabled}
    para renderizar el botón de Google Identity Services de ESA tienda.
    client_id = el propio del dueño (BYO) si configuró, si no el central
    DAVENT. Vacío/disabled = feature apagada (el front oculta el botón).
    """
    permission_classes      =   [AllowAny]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerPublicReadThrottle]

    def get(self, request, store_slug):
        store   =   resolve_store(store_slug)
        if store is None:
            return Response({'detail': 'La tienda no existe.'}, status = status.HTTP_404_NOT_FOUND)
        client_id   =   store_google_client_id(store)
        enabled     =   bool(client_id)
        return Response({'client_id': client_id if enabled else '', 'enabled': enabled})


class CustomerGoogleAuthView(APIView):
    """
    POST /api/customer-auth/google/ {credential, store_slug} → verifica el
    id_token contra tokeninfo (aud de la tienda + iss + email_verified +
    exp), find-or-create del Customer y ensure de la membresía.
    Devuelve {access, customer, is_new} + cookies.
    """
    permission_classes      =   [AllowAny]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerSocialAuthThrottle]

    def post(self, request):
        if not _session_origin_allowed(request):
            raise PermissionDenied('Origen no permitido.')
        serializer  =   GoogleLoginSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        store       =   resolve_store(data['store_slug'])
        if store is None:
            return Response({'store_slug': ['La tienda no existe o no está disponible.']}, status = status.HTTP_400_BAD_REQUEST)
        expected    =   store_google_client_id(store)
        if not expected:
            return Response({'detail': 'El ingreso con Google no está disponible en esta tienda.'}, status = status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            info    =   verify_google_credential(data['credential'], expected)
        except GoogleAuthError as e:
            logger.warning('Login Google de cliente rechazado (code=%s store=%s ip=%s)', e.code, store.slug, _client_ip(request))
            if e.code == 'no_email':
                detail  =   'Tu cuenta de Google no comparte un email. Registrate con el formulario.'
            else:
                detail  =   'No pudimos verificar tu cuenta de Google. Intentá de nuevo.'
            return Response({'detail': detail}, status = status.HTTP_400_BAD_REQUEST)
        try:
            customer, is_new    =   google_customer_login(info, store)
        except MembershipSuspended:
            return Response({'detail': 'Tu cuenta está suspendida en esta tienda.'}, status = status.HTTP_403_FORBIDDEN)
        if not customer.is_active:
            return Response({'detail': 'Esta cuenta está inactiva. Contactá al comercio.'}, status = status.HTTP_403_FORBIDDEN)
        mark_login(customer)
        logger.info('Login Google de cliente: customer_id=%s store=%s is_new=%s', customer.pk, store.slug, is_new)
        return _session_response(request, customer, is_new = is_new)
