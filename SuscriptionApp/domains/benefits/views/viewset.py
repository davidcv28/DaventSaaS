from .viewset_base   import BenefitBaseViewSet
from .viewset_config import PlanCatalogConfigs
from DaventProject.throttling import PublicReadThrottle
"""

Viewsets del dominio Benefits.

"""
#=========================================
# PLAN CATALOG VIEWSET (tarjetas públicas: plan + beneficios)
#=========================================
class PlanCatalogViewSet(BenefitBaseViewSet):
    viewset_config      =   PlanCatalogConfigs
    throttle_classes    =   [PublicReadThrottle]
