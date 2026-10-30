from rest_framework.decorators import action
from rest_framework.response import Response

from StoreApp.domains.design.models import DesignIconStyle, DesignPattern, DesignStyle
from StoreApp.domains.design.serializers import (
    DesignIconStyleSerializer,
    DesignPatternListSerializer,
    DesignPatternSerializer,
    DesignStyleListSerializer,
    DesignStyleSerializer,
)

from .viewset_base import DesignCatalogViewSet


#=========================================
# DESIGN STYLE VIEWSET (/api/design/styles/)
#=========================================
class DesignStyleViewSet(DesignCatalogViewSet):
    queryset            =   DesignStyle.objects.all()
    list_serializer     =   DesignStyleListSerializer
    write_serializer    =   DesignStyleSerializer

    #ESTILO BASE (el que aplica la web si la tienda no eligió uno)
    @action(detail = False, methods = ['get'], url_path = 'default')
    def default(self, request):
        style = self.get_queryset().filter(is_default = True, is_active = True).first()
        if not style:
            return Response({'detail': 'No hay estilo predeterminado.'}, status = 404)
        return Response(DesignStyleSerializer(style).data)

#=========================================
# DESIGN PATTERN VIEWSET (/api/design/patterns/)
#=========================================
class DesignPatternViewSet(DesignCatalogViewSet):
    queryset            =   DesignPattern.objects.select_related('style')
    list_serializer     =   DesignPatternListSerializer
    write_serializer    =   DesignPatternSerializer

    #PATRÓN BASE (el que aplica la web si la tienda no eligió uno)
    @action(detail = False, methods = ['get'], url_path = 'default')
    def default(self, request):
        pattern = self.get_queryset().filter(is_default = True, is_active = True).first()
        if not pattern:
            return Response({'detail': 'No hay patrón predeterminado.'}, status = 404)
        return Response(DesignPatternSerializer(pattern).data)

#=========================================
# DESIGN ICON STYLE VIEWSET (/api/design/icon-styles/)
#=========================================
class DesignIconStyleViewSet(DesignCatalogViewSet):
    queryset            =   DesignIconStyle.objects.all()
    list_serializer     =   DesignIconStyleSerializer
    write_serializer    =   DesignIconStyleSerializer

    #SET BASE (el que hereda un diseno sin set propio)
    @action(detail = False, methods = ['get'], url_path = 'default')
    def default(self, request):
        icon_style = self.get_queryset().filter(is_default = True, is_active = True).first()
        if not icon_style:
            return Response({'detail': 'No hay estilo de iconos predeterminado.'}, status = 404)
        return Response(DesignIconStyleSerializer(icon_style).data)
