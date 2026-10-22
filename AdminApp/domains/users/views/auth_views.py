import secrets

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Sesión web: el REFRESH viaja en cookie httpOnly scopeada a /api/token/ — el
# JavaScript del cliente jamás lo lee (anti-robo por XSS) y solo viaja a los
# endpoints de token. El ACCESS va en el body y vive solo en memoria del tab.
# Los clientes API (Bearer en body) siguen funcionando igual que antes.
REFRESH_COOKIE = 'davent_refresh'
CSRF_COOKIE    = 'davent_csrf'
COOKIE_PATH    = '/api/token/'

class LoginRateThrottle(AnonRateThrottle):
    """
    Throttle personalizado para el endpoint de login.
    Limita las peticiones según el scope 'login' definido en settings.py.
    """
    scope = 'login'

class RefreshRateThrottle(AnonRateThrottle):
    """Scope 'token_refresh' (settings): acota el brute-force del cookie."""
    scope = 'token_refresh'


def _secure():
    # Secure solo bajo HTTPS real (prod); en dev http://localhost se omite.
    return settings.SESSION_COOKIE_SECURE

def _cookie_max_age():
    return int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())

def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        REFRESH_COOKIE, str(refresh_token),
        max_age = _cookie_max_age(), path = COOKIE_PATH,
        httponly = True, secure = _secure(), samesite = 'Lax',
    )

def _set_csrf_cookie(response):
    # Doble-submit: el frontend la lee (document.cookie) y la devuelve en
    # X-CSRFToken. Path=/ porque document.cookie solo ve cookies cuyo path
    # cubre la página actual — con /api/token/ no la leería desde /dashboard.
    response.set_cookie(
        CSRF_COOKIE, secrets.token_urlsafe(32),
        max_age = _cookie_max_age(), path = '/',
        secure = _secure(), samesite = 'Lax',
    )

def _clear_session_cookies(response):
    response.delete_cookie(REFRESH_COOKIE, path = COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path = '/')

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
        if response.status_code == 200:
            refresh = response.data.pop('refresh', None)
            if refresh:
                _set_refresh_cookie(response, refresh)
                _set_csrf_cookie(response)
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
            rotated = response.data.pop('refresh', None)
            _set_refresh_cookie(response, rotated or refresh)
            _set_csrf_cookie(response)
        return response


class TokenLogoutView(APIView):
    """
    Cierre de sesión web: blacklist del refresh de la cookie (si existe y es
    válido) y borra ambas cookies. Idempotente: sin cookie responde 200 igual.
    """
    permission_classes = [AllowAny]

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
