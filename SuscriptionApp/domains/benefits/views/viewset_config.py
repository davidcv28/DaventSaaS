from rest_framework.permissions import AllowAny
from AdminApp.domains.suscriptions.models                    import SuscriptionPlan
from SuscriptionApp.domains.benefits.serializers.serializers import PlanCatalogSerializer
"""

Configuración de los viewsets del dominio Benefits.

"""
#=========================================
# PLAN CATALOG CONFIGS (catálogo público con beneficios)
#=========================================
PlanCatalogConfigs = {
    'get': {
        'serializer' :   PlanCatalogSerializer,
        'queryset'   :   SuscriptionPlan.objects.select_related('presentation').prefetch_related('benefits__benefit').order_by('presentation__display_order', 'price'),
        'permissions':   [AllowAny],
    },
}
