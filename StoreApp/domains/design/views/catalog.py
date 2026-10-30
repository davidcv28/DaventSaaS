from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.throttling import PublicReadThrottle
from StoreApp.domains.design.models import DesignIconStyle, DesignPattern, DesignStyle
from StoreApp.domains.design.serializers import (
    DesignIconStyleSerializer,
    DesignPatternListSerializer,
    DesignPatternSerializer,
    DesignStyleListSerializer,
    DesignStyleSerializer,
)

"""

/api/design/catalog/ — catálogo completo en una sola llamada.

Devuelve el patrón y el estilo predeterminados (los que aplica la web
pública cuando la tienda no eligió nada) más las listas activas, para que
el front no tenga presets propios: todo el diseño sale de la base.

"""
#=========================================
# DEFAULT HELPERS
#=========================================
def default_pattern():
    return DesignPattern.objects.filter(is_default = True, is_active = True).first()

def default_style():
    return DesignStyle.objects.filter(is_default = True, is_active = True).first()

def default_icon_style():
    return DesignIconStyle.objects.filter(is_default = True, is_active = True).first()

#=========================================
# DESIGN CATALOG VIEW
#=========================================
class DesignCatalogView(APIView):
    permission_classes  =   [AllowAny]
    #Lectura pública (la piden la web del cliente y el Studio en cada carga):
    #scope 'public_read' y no el anon global de 100/día, que se agota por
    #CGNAT y deja el catálogo vacío con 429.
    throttle_classes    =   [PublicReadThrottle]

    def get(self, request):
        pattern     =   default_pattern()
        style       =   default_style()
        response    =   Response({
            'pattern':  DesignPatternSerializer(pattern).data if pattern else None,
            'style':    DesignStyleSerializer(style).data if style else None,
            'patterns': DesignPatternListSerializer(
                DesignPattern.objects.filter(is_active = True), many = True
            ).data,
            'styles':   DesignStyleListSerializer(
                DesignStyle.objects.filter(is_active = True), many = True
            ).data,
            'icon_styles': DesignIconStyleSerializer(
                DesignIconStyle.objects.filter(is_active = True), many = True
            ).data,
            'default_icon_style': DesignIconStyleSerializer(default_icon_style()).data
                if default_icon_style() else None,
        })
        # El catálogo cambia cuando el staff edita la base: nunca se sirve
        # desde caché del navegador/proxy.
        response['Cache-Control'] = 'no-store'
        return response
