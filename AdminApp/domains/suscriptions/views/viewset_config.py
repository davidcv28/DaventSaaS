from ast import Lambda

from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

from AdminApp.domains.suscriptions.models                   import SuscriptionPlan, Suscription
from AdminApp.domains.suscriptions.serializers.serializers  import (
    SuscriptionPlanSerializer,
    SuscriptionSerializer,
    SuscriptionSerializerList
)

"""

Configuración de los viewsets del dominio Suscriptions.
Cada key (create, update, get) contiene su serializer, queryset y permissions.

"""

#=========================================
# SUSCRIPTION CONFIGS
#=========================================
SuscriptionConfigs = {
    'create': {
        'serializer' :   SuscriptionSerializer,
        'queryset'   :   Suscription.objects.all(),
        'permissions':   [IsAuthenticated],
        'message'    :   'Registro de suscripción exitoso'
    },
    'update': {
        'serializer' :   SuscriptionSerializer,
        'queryset'   :   lambda view : Suscription.objects.select_related('plan_suscription').filter(user__user = view.request.user),
        'permissions':   [IsAuthenticated],
        'message'    :   'El plan quedó seleccionado: se aplica cuando se acredite el pago'
    },
    'get': {
        'serializer'    :   SuscriptionSerializerList,
        'queryset'      :   lambda view : Suscription.objects.select_related('plan_suscription', 'pending_plan_suscription', 'user__user').all().order_by('-start_date')
                            if view.request.user.is_staff
                            else Suscription.objects.select_related('plan_suscription', 'pending_plan_suscription', 'user__user').filter(user__user = view.request.user),
        'permissions'   :   [IsAuthenticated],
    },
}

#=========================================
# SUSCRIPTION PLAN CONFIGS (catálogo público)
#=========================================
SuscriptionPlanConfigs = {
    'create': {
        'serializer' :   SuscriptionPlanSerializer,
        'queryset'   :   SuscriptionPlan.objects.all(),
        'permissions':   [IsAdminUser],
        'message'    :   'Plan creado correctamente'
    },
    'update': {
        'serializer' :   SuscriptionPlanSerializer,
        'queryset'   :   SuscriptionPlan.objects.all(),
        'permissions':   [IsAdminUser],
        'message'    :   'Plan actualizado correctamente'
    },
    'get': {
        'serializer'    :   SuscriptionPlanSerializer,
        #Sin planes de prueba: no son elegibles (ni desde el admin al asignar)
        'queryset'      :   SuscriptionPlan.objects.filter(is_trial = False).order_by('price'),
        'permissions'   :   [AllowAny],
    },
}

