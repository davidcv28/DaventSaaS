from django.db.migrations import serializer
from yaml import serialize
from .viewset_base      import  SuscriptionBaseViewSet
from .viewset_config    import  SuscriptionConfigs, SuscriptionPlanConfigs
from rest_framework     import status
from rest_framework.response import Response
"""

Creamos los viewsets correspondientes al dominio suscriptions


"""

#=========================================
# SUSCRIPTION VIEWSET
#=========================================
class SuscriptionViewSet(SuscriptionBaseViewSet):
    viewset_config  =   SuscriptionConfigs

#=========================================
# SUSCRIPTION PLAN VIEWSET (catálogo público para el dashboard)
#=========================================
class SuscriptionPlanViewSet(SuscriptionBaseViewSet):
    viewset_config  =   SuscriptionPlanConfigs

    