from StoreApp.domains.design.models import DesignPattern, DesignStyle
from StoreApp.domains.design.serializers import (
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

#=========================================
# DESIGN PATTERN VIEWSET (/api/design/patterns/)
#=========================================
class DesignPatternViewSet(DesignCatalogViewSet):
    queryset            =   DesignPattern.objects.select_related('style')
    list_serializer     =   DesignPatternListSerializer
    write_serializer    =   DesignPatternSerializer
