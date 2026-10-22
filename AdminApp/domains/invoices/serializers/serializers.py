"""
INVOICES SERIALIZERS
"""
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers
from AdminApp.domains.invoices.models import Invoice

# Los precios de los planes ya traen el IVA 21% incluido: el neto se obtiene
# dividiendo el total por 1.21 y el IVA es la diferencia.
_IVA_DIVISOR    =   Decimal('1.21')
_CENTS          =   Decimal('0.01')

class InvoiceSerializer(serializers.ModelSerializer):
    # Campos derivados (solo lectura) que necesita el comprobante imprimible.
    comprobante             = serializers.SerializerMethodField()
    type_display            = serializers.CharField(source = 'get_type_display', read_only = True)
    plan_name               = serializers.CharField(source = 'payment.suscription.plan_suscription.name', read_only = True)
    paid_at                 = serializers.DateTimeField(source = 'payment.paid_at', read_only = True)
    currency                = serializers.CharField(source = 'payment.currency', read_only = True)
    customer_name           = serializers.SerializerMethodField()
    document                = serializers.CharField(source = 'user.document', read_only = True)
    type_document           = serializers.CharField(source = 'user.type_document', read_only = True)
    tax_condition_display   = serializers.CharField(source = 'user.get_tax_condition_display', read_only = True)
    address                 = serializers.CharField(source = 'user.address', read_only = True)
    city_name               = serializers.CharField(source = 'user.city.name_city', read_only = True)
    province_name           = serializers.CharField(source = 'user.province.name_province', read_only = True)
    net_amount              = serializers.SerializerMethodField()
    iva_amount              = serializers.SerializerMethodField()

    def get_comprobante(self, obj):
        return f'{obj.pos:04d}-{obj.number:08d}'

    def get_net_amount(self, obj):
        return (obj.total / _IVA_DIVISOR).quantize(_CENTS, rounding = ROUND_HALF_UP)

    def get_iva_amount(self, obj):
        return obj.total - self.get_net_amount(obj)

    def get_customer_name(self, obj):
        u = obj.user
        return u.business_name or f'{u.first_name} {u.last_name}'.strip()

    class Meta:
        model = Invoice
        fields = [
            'id', 'user', 'payment', 'type', 'type_display', 'pos', 'number',
            'comprobante', 'total', 'net_amount', 'iva_amount', 'issued_at',
            'plan_name', 'paid_at', 'currency',
            'customer_name', 'document', 'type_document', 'tax_condition_display',
            'address', 'city_name', 'province_name',
        ]
