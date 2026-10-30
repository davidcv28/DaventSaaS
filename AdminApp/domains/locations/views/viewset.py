from .viewset_base import LocationBaseViewSet
from .viewset_config import (
    CityViewSetConfig,
    ProvinceViewSetConfig,
    ZipCodeViewSetConfig,
)

"""
En este modulo simplemente asignamos la view_config para cada base viewset
"""

#=============================
# PROVINCE VIEWSET
#=============================
class ProvinceViewSet(LocationBaseViewSet):
    view_config = ProvinceViewSetConfig


#=============================
# CITY VIEWSET
#=============================
class CityViewSet(LocationBaseViewSet):
    view_config = CityViewSetConfig


#=============================
# ZIPCODE VIEWSET
#=============================
class ZipCodeViewSet(LocationBaseViewSet):
    view_config = ZipCodeViewSetConfig

