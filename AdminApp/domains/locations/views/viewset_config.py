from rest_framework.permissions import AllowAny

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.locations.serializers import (
    CitySerializer,
    ProvinceSerializer,
    ZipCodeSerializer,
)

"""
Configuración por acción (patrón viewset_config del proyecto).
Lectura pública para que el registro (anónimo) pueda poblar selects.
Cities acepta ?province=<id> para filtrar.
"""


def city_list_queryset(view):
    province_id = view.request.query_params.get('province')
    qs = City.objects.select_related('province', 'zipcode').order_by('name_city')
    if province_id:
        return qs.filter(province_id=province_id)
    return qs


#=============================
# PROVINCE VIEWSET CONFIG
#=============================
ProvinceViewSetConfig = {
    'list': {
        'serializer': ProvinceSerializer,
        'queryset': Province.objects.all().order_by('name_province'),
        'permissions': [AllowAny],
    },
    'retrieve': {
        'serializer': ProvinceSerializer,
        'queryset': Province.objects.all(),
        'permissions': [AllowAny],
    },
}
#=============================
# CITY VIEWSET CONFIG
#=============================
CityViewSetConfig = {
    'list': {
        'serializer': CitySerializer,
        'queryset': lambda view: city_list_queryset(view),
        'permissions': [AllowAny],
    },
    'retrieve': {
        'serializer': CitySerializer,
        'queryset': City.objects.select_related('province', 'zipcode').all(),
        'permissions': [AllowAny],
    },
}
#=============================
# ZIPCODE VIEWSET CONFIG
#=============================
ZipCodeViewSetConfig = {
    'list': {
        'serializer': ZipCodeSerializer,
        'queryset': ZipCode.objects.all().order_by('zipcode'),
        'permissions': [AllowAny],
    },
    'retrieve': {
        'serializer': ZipCodeSerializer,
        'queryset': ZipCode.objects.all(),
        'permissions': [AllowAny],
    },
}

