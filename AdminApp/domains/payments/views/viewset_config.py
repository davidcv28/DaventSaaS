from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

from AdminApp.domains.payments.models import DailyRevenue, MonthlyRevenue, Payment
from AdminApp.domains.payments.serializers.serializers import (
    DailyRevenueSerializer,
    MonthlyRevenueSerializer,
    PaymentSerializer,
    PaymentSerializerList,
)

"""

Configuración de los viewsets del dominio Payments.
Cada key (create, update, get) contiene su serializer, queryset y permissions.

"""

#=========================================
# PAYMENT CONFIGS
#=========================================
PaymentConfigs = {
    'create': {
        'serializer' :   PaymentSerializer,
        'queryset'   :   Payment.objects.select_related('suscription__plan_suscription'),
        'permissions':   [IsAuthenticated],
        'message'    :   'Pago registrado correctamente'
    },
    'update': {
        'serializer' :   PaymentSerializer,
        'queryset'   :   Payment.objects.select_related('suscription__plan_suscription'),
        'permissions':   [IsAdminUser],
        'message'    :   'Pago actualizado correctamente'
    },
    'get': {
        'serializer'    :   PaymentSerializerList,
        'queryset'      :   lambda view : Payment.objects.select_related('suscription__plan_suscription', 'user__user').all().order_by('-created_at')
                            if view.request.user.is_staff
                            else Payment.objects.select_related('suscription__plan_suscription', 'user__user').filter(user__user = view.request.user).order_by('-created_at'),
        'permissions'   :   [IsAuthenticated],
    },
    'checkout': {
        'serializer'    :   PaymentSerializerList,
        'queryset'      :   Payment.objects.all(),
        'permissions'   :   [IsAuthenticated],
    },
    'sync': {
        'serializer'    :   PaymentSerializerList,
        'queryset'      :   Payment.objects.all(),
        'permissions'   :   [IsAuthenticated],
    },
    'subscription': {
        'serializer'    :   PaymentSerializerList,
        'queryset'      :   Payment.objects.all(),
        'permissions'   :   [IsAuthenticated],
    },
    'cancel_renewal': {
        'serializer'    :   PaymentSerializerList,
        'queryset'      :   Payment.objects.all(),
        'permissions'   :   [IsAuthenticated],
    },
    'admin_summary': {
        'serializer'    :   PaymentSerializerList,
        'queryset'      :   Payment.objects.all(),
        'permissions'   :   [IsAdminUser],
    },
    'webhook': {
        'serializer'    :   PaymentSerializerList,
        'queryset'      :   Payment.objects.all(),
        'permissions'   :   [AllowAny],
    },
}
#=========================================
# DAILY REVENUE CONFIGS (solo lectura, admin)
#=========================================
DailyRevenueConfigs = {
    'create': {
        'serializer' :   DailyRevenueSerializer,
        'queryset'   :   DailyRevenue.objects.none(),
        'permissions':   [IsAdminUser],
        'message'    :   'Operación no permitida'
    },
    'update': {
        'serializer' :   DailyRevenueSerializer,
        'queryset'   :   DailyRevenue.objects.none(),
        'permissions':   [IsAdminUser],
        'message'    :   'Operación no permitida'
    },
    'get': {
        'serializer'    :   DailyRevenueSerializer,
        'queryset'      :   DailyRevenue.objects.all(),
        'permissions'   :   [IsAdminUser],
    },
}
#=========================================
# MONTHLY REVENUE CONFIGS (solo lectura, admin)
#=========================================
MonthlyRevenueConfigs = {
    'create': {
        'serializer' :   MonthlyRevenueSerializer,
        'queryset'   :   MonthlyRevenue.objects.none(),
        'permissions':   [IsAdminUser],
        'message'    :   'Operación no permitida'
    },
    'update': {
        'serializer' :   MonthlyRevenueSerializer,
        'queryset'   :   MonthlyRevenue.objects.none(),
        'permissions':   [IsAdminUser],
        'message'    :   'Operación no permitida'
    },
    'get': {
        'serializer'    :   MonthlyRevenueSerializer,
        'queryset'      :   MonthlyRevenue.objects.all(),
        'permissions'   :   [IsAdminUser],
    },
}
