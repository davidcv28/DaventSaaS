from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.cache_utils import cache_get, cache_set
from DaventProject.throttling import PublicReadThrottle
from StoreApp.domains.design.models import DesignIconStyle, DesignPattern, DesignStyle
from StoreApp.domains.design.serializers import (
    DesignIconStyleSerializer,
    DesignPatternListSerializer,
    DesignPatternSerializer,
    DesignStyleListSerializer,
    DesignStyleSerializer,
)
from StoreApp.domains.stores.public_cache import public_cache_stamp

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

#TTL del cache server-side del payload serializado. Corto a propósito: la
#key ya lleva la época pública (bump_public_epoch corre en cada save/delete
#del catálogo vía signals.py), así el TTL solo cubre el caso de un bump
#perdido con Redis caído — nunca sirve un catálogo viejo por minutos.
_CATALOG_CACHE_TTL  =   300


def _catalog_epoch():
    #La época pública cambia con CADA edición del catálogo (signals.py): es
    #la invalidación gratis del cache server-side de estos payloads.
    return public_cache_stamp(0)[0]


def catalog_cached(key_suffix, produce):
    """Cache server-side fail-open keyed por época pública."""
    key     =   f'design:catalog:v1:{_catalog_epoch()}:{key_suffix}'
    data    =   cache_get(key)
    if data is None:
        data    =   produce()
        if data is not None:
            cache_set(key, data, timeout = _CATALOG_CACHE_TTL)
    return data

#=========================================
# DESIGN CATALOG VIEW
#=========================================
class DesignCatalogView(APIView):
    permission_classes  =   [AllowAny]
    #Lectura pública (la piden la web del cliente y el Studio en cada carga):
    #scope 'public_read' y no el anon global de 100/día, que se agota por
    #CGNAT y deja el catálogo vacío con 429.
    throttle_classes    =   [PublicReadThrottle]

    def _build(self):
        pattern     =   default_pattern()
        style       =   default_style()
        return {
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
        }

    def get(self, request):
        response    =   Response(catalog_cached('all', self._build))
        # El caché es server-side keyed por época: el navegador/proxy sigue
        # sin guardar nada (una edición staff se ve al instante).
        response['Cache-Control'] = 'no-store'
        return response
