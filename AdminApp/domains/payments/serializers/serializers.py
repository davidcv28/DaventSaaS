from rest_framework import serializers
from AdminApp.domains.payments.models import Payment, DailyRevenue, MonthlyRevenue
from .config_fields import PaymentFieldsConfig, DailyRevenueFieldsConfig, MonthlyRevenueFieldsConfig
from .mixins        import PaymentCreateMixin, PaymentCreateMethod
"""

PAYMENTS SERIALIZERS
En este apartado configuramos cada serializador del dominio Payments para tareas específicas como:
-Registro de pago                (Payment)
-Lectura de pagos               (detalle + datos de la suscripción)
-Lectura de rollups             (DailyRevenue / MonthlyRevenue para dashboards)

"""

#=========================================
# PAYMENT SERIALIZER (POST - confirma un pago de Mercado Pago)
#=========================================
class PaymentSerializer(PaymentCreateMixin, PaymentCreateMethod, serializers.ModelSerializer):
    id                  =   serializers.ReadOnlyField()
    user                =   serializers.HiddenField(**PaymentFieldsConfig['user'])
    suscription         =   serializers.PrimaryKeyRelatedField(**PaymentFieldsConfig['suscription'])
    payment_id          =   serializers.IntegerField(**PaymentFieldsConfig['payment_id'])
    #DATOS VERIFICADOS DESDE LA API DE MP (solo lectura)
    amount              =   serializers.DecimalField(max_digits = 12, decimal_places = 2, read_only = True)
    currency            =   serializers.CharField(read_only = True)
    status              =   serializers.CharField(read_only = True)
    external_reference  =   serializers.CharField(read_only = True)
    paid_at             =   serializers.DateTimeField(read_only = True)
    created_at          =   serializers.ReadOnlyField()
    class Meta:
        model           =   Payment
        fields          =   ['id', 'user', 'suscription', 'payment_id', 'amount', 'currency', 'status', 'external_reference', 'paid_at', 'created_at']

#=========================================
# PAYMENT SERIALIZER LIST (GET)
#=========================================
class PaymentSerializerList(serializers.ModelSerializer):
    plan_name           =   serializers.CharField(source = 'suscription.plan_suscription.name', read_only = True)
    user_name           =   serializers.CharField(source = 'user.user.username', read_only = True)
    business_name       =   serializers.CharField(source = 'user.business_name', read_only = True)
    status_display      =   serializers.CharField(source = 'get_status_display', read_only = True)
    class Meta:
        model           =   Payment
        fields          =   ['id', 'suscription', 'user_name', 'business_name', 'plan_name', 'amount', 'currency', 'status', 'status_display', 'external_reference', 'paid_at', 'created_at']

#=========================================
# DAILY REVENUE SERIALIZER (GET)
#=========================================
class DailyRevenueSerializer(serializers.ModelSerializer):
    date                =   serializers.DateField(**DailyRevenueFieldsConfig['date'])
    total_amount        =   serializers.DecimalField(**DailyRevenueFieldsConfig['total_amount'])
    payments_count      =   serializers.IntegerField(**DailyRevenueFieldsConfig['payments_count'])
    class Meta:
        model           =   DailyRevenue
        fields          =   ['id', 'date', 'total_amount', 'payments_count']

#=========================================
# MONTHLY REVENUE SERIALIZER (GET)
#=========================================
class MonthlyRevenueSerializer(serializers.ModelSerializer):
    year                =   serializers.IntegerField(**MonthlyRevenueFieldsConfig['year'])
    month               =   serializers.IntegerField(**MonthlyRevenueFieldsConfig['month'])
    total_amount        =   serializers.DecimalField(**MonthlyRevenueFieldsConfig['total_amount'])
    payments_count      =   serializers.IntegerField(**MonthlyRevenueFieldsConfig['payments_count'])
    class Meta:
        model           =   MonthlyRevenue
        fields          =   ['id', 'year', 'month', 'total_amount', 'payments_count']
