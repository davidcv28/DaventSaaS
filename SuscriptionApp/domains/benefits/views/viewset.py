from DaventProject.throttling import PublicReadThrottle

from .viewset_base import BenefitBaseViewSet
from .viewset_config import PlanCatalogConfigs

"""

Viewsets del dominio Benefits.

"""
#=========================================
# PLAN CATALOG VIEWSET (tarjetas públicas: plan + beneficios)
#=========================================
class PlanCatalogViewSet(BenefitBaseViewSet):
    viewset_config      =   PlanCatalogConfigs
    throttle_classes    =   [PublicReadThrottle]
