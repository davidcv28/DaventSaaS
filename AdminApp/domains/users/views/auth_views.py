import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from AdminApp.domains.users.serializers import (
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from AdminApp.domains.users.services import (
    RequestPasswordResetQuery,
    ConfirmPasswordResetQuery,
    SendVerificationEmailQuery,
    VerifyEmailQuery,
    ConfirmPhoneVerificationQuery,
    SocialAuthError,
    SocialLoginQuery,
    VerifyGoogleCredentialQuery,
    VerifyFacebookTokenQuery,
    GOOGLE_CLIENT_ID,
    FACEBOOK_APP_ID,
    FACEBOOK_APP_SECRET,
    FRONTEND_URL,
    FIREBASE_API_KEY,
)

# Sesión web: el REFRESH viaja en cookie httpOnly scopeada a /api/token/ — el
# JavaScript del cliente jamás lo lee (anti-robo por XSS) y solo viaja a los
# endpoints de token. El ACCESS va en el body y vive solo en memoria del tab.
# Los clientes API (Bearer en body) siguen funcionando igual que antes.
REFRESH_COOKIE = 'davent_refresh'
CSRF_COOKIE    = 'davent_csrf'
REMEMBER_COOKIE = 'davent_remember'
COOKIE_PATH    = '/api/token/'
# "Mantener sesión iniciada": el refresh dura 30 días y las cookies son
# persistentes; sin el flag la cookie de refresh es de sesión del browser
# (expira el JWT normal de 7d, pero al cerrar el navegador ya no viaja).
REMEMBER_LIFETIME = timedelta(days = 30)

logger = logging.getLogger(__name__)


def _remember_requested(request) -> bool:
    """
    Parseo estricto del flag "mantener sesión": bool(request.data.get(...))
    trataba el string 'false' de un POST form-encoded como truthy y
    convertía una sesión efímera en persistente. Solo cuentan como sí
    el booleano JSON o sus equivalentes textuales.
    """
    return request.data.get('remember') in (True, 1, '1', 'true', 'True')


def _client_ip(request) -> str:
    forwarded     =   request.META.get('HTTP_X_FORWARDED_FOR') or ''
    return forwarded.split(',')[-1].strip() or request.META.get('REMOTE_ADDR') or '-'

class LoginRateThrottle(AnonRateThrottle):
    """
    Throttle personalizado para el endpoint de login.
    Limita las peticiones según el scope 'login' definido en settings.py.
    """
    scope = 'login'

class RefreshRateThrottle(AnonRateThrottle):
    """Scope 'token_refresh' (settings): acota el brute-force del cookie."""
    scope = 'token_refresh'

class PasswordResetRateThrottle(AnonRateThrottle):
    """Scope 'password_reset' (settings): frena el abuso del envío de correos."""
    scope = 'password_reset'

class VerifyEmailRateThrottle(UserRateThrottle):
    """Scope 'email_verification' (settings): reenvío por usuario autenticado."""
    scope = 'email_verification'

class LogoutRateThrottle(UserRateThrottle):
    """Scope 'logout' (settings): el endpoint es AllowAny y blacklistea el
    refresh de la cookie — acotado por usuario o por IP si no hay auth."""
    scope = 'logout'

class VerifyPhoneRateThrottle(UserRateThrottle):
    """Scope 'phone_verification' (settings): generación de códigos por usuario."""
    scope = 'phone_verification'

class SocialAuthRateThrottle(AnonRateThrottle):
    """Scope 'social_auth' (settings): cada exchange pega dos llamadas al
    provider (tokeninfo/debug_token + /me) — se acota por IP."""
    scope = 'social_auth'


def _secure():
    # Secure solo bajo HTTPS real (prod); en dev http://localhost se omite.
    return settings.SESSION_COOKIE_SECURE

def _remember_of(request):
    # Hint legible seteado en el login: en el refresh la rotación conserva
    # la persistencia original (sin el flag se degradaría a cookie de sesión).
    return request.COOKIES.get(REMEMBER_COOKIE) == '1'

def _set_refresh_cookie(response, refresh_token, remember = False):
    response.set_cookie(
        REFRESH_COOKIE, str(refresh_token),
        max_age = int(REMEMBER_LIFETIME.total_seconds()) if remember else None,
        path = COOKIE_PATH,
        httponly = True, secure = _secure(), samesite = 'Lax',
    )

def _set_csrf_cookie(response, remember = False):
    # Doble-submit: el frontend la lee (document.cookie) y la devuelve en
    # X-CSRFToken. Path=/ porque document.cookie solo ve cookies cuyo path
    # cubre la página actual — con /api/token/ no la leería desde /dashboard.
    response.set_cookie(
        CSRF_COOKIE, secrets.token_urlsafe(32),
        max_age = int(REMEMBER_LIFETIME.total_seconds()) if remember else None,
        path = '/',
        secure = _secure(), samesite = 'Lax',
    )

def _set_remember_cookie(response):
    response.set_cookie(
        REMEMBER_COOKIE, '1',
        max_age = int(REMEMBER_LIFETIME.total_seconds()), path = '/',
        secure = _secure(), samesite = 'Lax',
    )

def _clear_session_cookies(response):
    response.delete_cookie(REFRESH_COOKIE, path = COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path = '/')
    response.delete_cookie(REMEMBER_COOKIE, path = '/')

def _require_csrf(request):
    """Doble-submit: X-CSRFToken debe matchear la cookie CSRF. Sin ella, un
    POST forjado same-site (ej. desde un subdominio de tienda) se rechaza."""
    cookie = request.COOKIES.get(CSRF_COOKIE)
    header = request.headers.get('X-CSRFToken')
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise PermissionDenied('CSRF token inválido o ausente')


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login JWT: devuelve {access} en el body y setea el refresh como cookie
    httpOnly + la cookie CSRF de doble-submit. Controla fuerza bruta por IP.
    """
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            #Auditoría de fuerza bruta: nunca se loguea la contraseña.
            logger.warning('Login rechazado (status=%s user=%s ip=%s)',
                           response.status_code, request.data.get('username'), _client_ip(request))
            return response
        refresh = response.data.pop('refresh', None)
        if refresh:
            remember    =   _remember_requested(request)
            token       =   RefreshToken(refresh)
            if remember:
                token.set_exp(lifetime = REMEMBER_LIFETIME)
                _set_remember_cookie(response)
            _set_refresh_cookie(response, str(token), remember)
            _set_csrf_cookie(response, remember)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """
    Refresh JWT dual:
      - Web: lee el refresh de la cookie httpOnly (exige CSRF doble-submit),
        devuelve solo {access} y rota la cookie (ROTATE_REFRESH_TOKENS +
        blacklist: un refresh robado se inutiliza al primer uso legítimo).
      - Clientes API: refresh en body como siempre (sin CSRF — no hay cookie).
    """
    throttle_classes = [RefreshRateThrottle]

    def post(self, request, *args, **kwargs):
        refresh = request.data.get('refresh')
        from_cookie = False
        if not refresh:
            refresh = request.COOKIES.get(REFRESH_COOKIE)
            from_cookie = bool(refresh)
        if from_cookie:
            _require_csrf(request)
        serializer = self.get_serializer(data = {'refresh': refresh})
        try:
            serializer.is_valid(raise_exception = True)
        except TokenError as e:
            # TokenError no es APIException: sin esto un refresh inválido o en
            # blacklist (ej. replay de una cookie robada) sale como 500.
            raise InvalidToken(e.args[0])
        response = Response(serializer.validated_data, status = status.HTTP_200_OK)
        if from_cookie:
            remember = _remember_of(request)
            if remember:
                _set_remember_cookie(response)
            rotated = response.data.pop('refresh', None)
            if remember and rotated:
                #El rotado sale con la vida estándar de 7d: se vuelve a
                #extender a REMEMBER_LIFETIME para no degradar la sesión.
                token = RefreshToken(rotated)
                token.set_exp(lifetime = REMEMBER_LIFETIME)
                rotated = str(token)
            _set_refresh_cookie(response, rotated or refresh, remember)
            _set_csrf_cookie(response, remember)
        return response


class TokenLogoutView(APIView):
    """
    Cierre de sesión web: blacklist del refresh de la cookie (si existe y es
    válido) y borra ambas cookies. Idempotente: sin cookie responde 200 igual.
    """
    permission_classes = [AllowAny]
    throttle_classes   = [LogoutRateThrottle]

    def post(self, request):
        refresh = request.COOKIES.get(REFRESH_COOKIE)
        if refresh:
            _require_csrf(request)
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                pass  # token inválido/expirado: las cookies se limpian igual
        response = Response({'Exito': 'Sesión cerrada'}, status = status.HTTP_200_OK)
        _clear_session_cookies(response)
        return response


# Respuesta única del request de reseteo: nunca revela si el correo existe
# (anti-enumeración de usuarios — el mail solo sale si la cuenta existe).
RESET_RESPONSE  =   'Si el correo está registrado, te va a llegar un enlace para restablecer tu contraseña.'

class PasswordResetRequestView(APIView):
    """
    POST /api/password-reset/ {email}: genera uid+token firmados y manda el
    mail con el link al frontend. Siempre responde 200 con mensaje genérico.
    """
    permission_classes  =   [AllowAny]
    throttle_classes    =   [PasswordResetRateThrottle]

    def post(self, request):
        serializer  =   PasswordResetRequestSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        RequestPasswordResetQuery(serializer.validated_data['email'])
        return Response({'Exito': RESET_RESPONSE}, status = status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    POST /api/password-reset/confirm/ {uid, token, new_password, confirm_password}:
    valida el token (vencimiento = PASSWORD_RESET_TIMEOUT), aplica la policy de
    contraseñas, setea la clave y blacklista todos los refresh del usuario —
    cierra todas sus sesiones abiertas.
    """
    permission_classes  =   [AllowAny]
    throttle_classes    =   [PasswordResetRateThrottle]

    def post(self, request):
        serializer  =   PasswordResetConfirmSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        ConfirmPasswordResetQuery(serializer.validated_data['user'], serializer.validated_data['new_password'])
        return Response({'Exito': 'Tu contraseña se actualizó. Ya podés iniciar sesión con la clave nueva.'}, status = status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """
    GET /api/verify-email/?uid=&token=: el link del correo de verificación
    apunta al backend (firma del token), marca email_verified en el perfil y
    redirige al frontend con el resultado. Idempotente.
    """
    permission_classes  =   [AllowAny]

    def get(self, request):
        ok      =   VerifyEmailQuery(
            request.query_params.get('uid', ''),
            request.query_params.get('token', ''),
        )
        return HttpResponseRedirect(f"{FRONTEND_URL}/verificar-email?status={'ok' if ok else 'error'}")


class VerifyEmailResendView(APIView):
    """
    POST /api/verify-email/resend/: reenvía el correo de verificación al
    usuario autenticado. Throttle por usuario (scope email_verification).
    """
    permission_classes  =   [IsAuthenticated]
    throttle_classes    =   [VerifyEmailRateThrottle]

    def post(self, request):
        profile =   getattr(request.user, 'profile', None)
        if profile and profile.email_verified:
            return Response({'Exito': 'Tu correo ya está verificado.'}, status = status.HTTP_200_OK)
        SendVerificationEmailQuery(request.user)
        return Response({'Exito': 'Te reenviamos el correo de verificación. Revisá tu casilla (y el spam).'}, status = status.HTTP_200_OK)


#=================================
# PHONE VERIFICATION (Firebase Phone Auth — costo $0)
#=================================
# El usuario recibe un SMS de Firebase (plan Spark: 10/día gratis, sin
# tarjeta), confirma el código en el frontend con el SDK de Firebase y nos
# manda el idToken resultante — acá se valida contra Identity Toolkit y se
# compara el phoneNumber verificado por Google con profile.phone.
class VerifyPhoneConfirmView(APIView):
    """
    POST /api/verify-phone/ {id_token}: marca phone_verified si el número
    verificado por Firebase coincide con el celular del perfil.
    """
    permission_classes  =   [IsAuthenticated]
    throttle_classes    =   [VerifyPhoneRateThrottle]

    def post(self, request):
        profile =   getattr(request.user, 'profile', None)
        if not profile or not profile.phone:
            return Response({'detail': 'Cargá tu número de celular en tu perfil primero.'}, status = status.HTTP_400_BAD_REQUEST)
        if profile.phone_verified:
            return Response({'Exito': 'Tu celular ya está verificado.'}, status = status.HTTP_200_OK)
        if not FIREBASE_API_KEY:
            return Response({'detail': 'La verificación por SMS no está disponible por el momento.'}, status = status.HTTP_503_SERVICE_UNAVAILABLE)
        if not ConfirmPhoneVerificationQuery(profile, request.data.get('id_token', '')):
            return Response({'detail': 'El código no es válido o ya venció. Pedí un SMS nuevo.'}, status = status.HTTP_400_BAD_REQUEST)
        return Response({'Exito': 'Tu celular quedó verificado.'}, status = status.HTTP_200_OK)


class VerifyPhoneStatusView(APIView):
    """
    GET /api/verify-phone/status/: consulta liviana del flag — devuelve solo
    el booleano, no el perfil entero.
    """
    permission_classes  =   [IsAuthenticated]

    def get(self, request):
        profile =   getattr(request.user, 'profile', None)
        return Response({'phone_verified': bool(profile and profile.phone_verified)}, status = status.HTTP_200_OK)


#=================================
# SOCIAL LOGIN (Google + Facebook — token exchange)
#=================================
# El frontend completa el consent del provider y manda la credencial; el
# backend la verifica contra el provider (services/social.py) y emite la
# MISMA sesión del login por contraseña: access en body + refresh en cookie
# httpOnly + CSRF doble-submit. Sin env vars configuradas responde 503.
def _social_session_response(request, user, is_new):
    #Misma salida que CustomTokenObtainPairView: el refresh se setea como
    #cookie y solo viaja a /api/token/. 'remember' respeta el mismo flag del
    #login (cookie persistente 30d vs cookie de sesión del navegador).
    remember    =   _remember_requested(request)
    refresh     =   RefreshToken.for_user(user)
    if remember:
        refresh.set_exp(lifetime = REMEMBER_LIFETIME)
    profile     =   getattr(user, 'profile', None)
    response    =   Response({
        'access'            :   str(refresh.access_token),
        'is_new'            :   is_new,
        #El alta social no pide celular: el frontend lleva al usuario a
        #completarlo antes de seguir (el claim de la web lo exige).
        'requires_phone'    :   not bool(getattr(profile, 'phone', None)),
    }, status = status.HTTP_200_OK)
    if remember:
        _set_remember_cookie(response)
    _set_refresh_cookie(response, str(refresh), remember)
    _set_csrf_cookie(response, remember)
    return response


def _social_error(e : SocialAuthError, provider : str) -> Response:
    if e.code == 'no_email':
        detail  =   f'Tu cuenta de {provider} no comparte un email. Vinculá un correo en tu cuenta o registrate con el formulario.'
    else:
        detail  =   f'No pudimos verificar tu cuenta de {provider}. Intentá de nuevo.'
    return Response({'detail': detail}, status = status.HTTP_400_BAD_REQUEST)


class GoogleAuthView(APIView):
    """
    POST /api/auth/google/ {credential}: el ID token del botón oficial de
    Google Identity Services se verifica contra tokeninfo (aud + email
    verificado) y abre sesión DAVENT. Alta nueva si el email no existe.
    """
    permission_classes  =   [AllowAny]
    throttle_classes    =   [SocialAuthRateThrottle]

    def post(self, request):
        if not GOOGLE_CLIENT_ID:
            return Response({'detail': 'El ingreso con Google no está disponible por el momento.'}, status = status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            info            =   VerifyGoogleCredentialQuery(request.data.get('credential', ''))
            user, is_new    =   SocialLoginQuery(info)
        except SocialAuthError as e:
            logger.warning('Login Google rechazado (code=%s ip=%s)', e.code, _client_ip(request))
            return _social_error(e, 'Google')
        return _social_session_response(request, user, is_new)


class FacebookAuthView(APIView):
    """
    POST /api/auth/facebook/ {access_token}: el user token de FB.login se
    valida con debug_token (app_id propio + vigente) y /me con
    appsecret_proof. Sin email en la cuenta Meta se responde 400 explícito.
    """
    permission_classes  =   [AllowAny]
    throttle_classes    =   [SocialAuthRateThrottle]

    def post(self, request):
        if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
            return Response({'detail': 'El ingreso con Facebook no está disponible por el momento.'}, status = status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            info            =   VerifyFacebookTokenQuery(request.data.get('access_token', ''))
            user, is_new    =   SocialLoginQuery(info)
        except SocialAuthError as e:
            logger.warning('Login Facebook rechazado (code=%s ip=%s)', e.code, _client_ip(request))
            return _social_error(e, 'Facebook')
        return _social_session_response(request, user, is_new)
