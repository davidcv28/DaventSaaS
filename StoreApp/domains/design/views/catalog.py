from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.design.models import DesignPattern, DesignStyle
from StoreApp.domains.design.serializers import (
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

#=========================================
# DESIGN CATALOG VIEW
#=========================================
class DesignCatalogView(APIView):
    permission_classes  =   [AllowAny]

    def get(self, request):
        pattern     =   default_pattern()
        style       =   default_style()
        return Response({
            'pattern':  DesignPatternSerializer(pattern).data if pattern else None,
            'style':    DesignStyleSerializer(style).data if style else None,
            'patterns': DesignPatternListSerializer(
                DesignPattern.objects.filter(is_active = True), many = True
            ).data,
            'styles':   DesignStyleListSerializer(
                DesignStyle.objects.filter(is_active = True), many = True
            ).data,
        })
