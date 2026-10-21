from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    """
    Throttle personalizado para el endpoint de login.
    Limita las peticiones según el scope 'login' definido en settings.py.
    """
    scope = 'login'

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para el login utilizando JWT que incluye control de concurrencia/fuerza bruta.
    """
    throttle_classes = [LoginRateThrottle]

