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

from .catalog import catalog_cached
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
        def _produce():
            style   =   self.get_queryset().filter(is_default = True, is_active = True).first()
            return DesignStyleSerializer(style).data if style else None
        data    =   catalog_cached('style:default', _produce)
        if data is None:
            return Response({'detail': 'No hay estilo predeterminado.'}, status = 404)
        return Response(data)

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
        def _produce():
            pattern =   self.get_queryset().filter(is_default = True, is_active = True).first()
            return DesignPatternSerializer(pattern).data if pattern else None
        data    =   catalog_cached('pattern:default', _produce)
        if data is None:
            return Response({'detail': 'No hay patrón predeterminado.'}, status = 404)
        return Response(data)

    #VISTA PREVIA CON DATOS DE EJEMPLO (modal "Ver este diseño")
    @action(detail = True, methods = ['get'], url_path = 'preview')
    def preview(self, request, slug = None):
        from StoreApp.domains.design.services.pattern_preview import preview_pattern
        pattern = self.get_object()
        if not (pattern.html or '').strip():
            return Response({'detail': 'El patrón no tiene markup propio.'}, status = 404)
        style_slug = (request.query_params.get('style') or '').strip()
        style = DesignStyle.objects.filter(slug = style_slug).first() if style_slug else None
        return Response(preview_pattern(
            pattern,
            theme = request.query_params.get('theme') or 'light',
            accent = (request.query_params.get('accent') or '').strip(),
            style = style,
        ))

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
        def _produce():
            icon    =   self.get_queryset().filter(is_default = True, is_active = True).first()
            return DesignIconStyleSerializer(icon).data if icon else None
        data    =   catalog_cached('icon-style:default', _produce)
        if data is None:
            return Response({'detail': 'No hay estilo de iconos predeterminado.'}, status = 404)
        return Response(data)
