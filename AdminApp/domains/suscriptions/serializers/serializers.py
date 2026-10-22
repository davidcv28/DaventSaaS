from pyexpat import model
from attr import fields
from django.core import validators
from django.db.models import constraints
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.validators import UniqueTogetherValidator
from .config_fields import SuscriptionsPlanFields, SuscriptionsFields
from .mixins        import SuscriptionPlanMixinValidator, SuscriptionCreateMixin
from AdminApp.domains.suscriptions.models import SuscriptionPlan, Suscription
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

"""

Creamos los serializadores para validar los datos ingresados

"""


#=========================================
# SUSCRIPTION PLAN SERIALIZER
#=========================================
class SuscriptionPlanSerializer(SuscriptionPlanMixinValidator, serializers.ModelSerializer):
    id                  =   serializers.ReadOnlyField()
    name                =   serializers.CharField(**SuscriptionsPlanFields['name'])
    price               =   serializers.DecimalField(**SuscriptionsPlanFields['price'])
    class Meta:
        model           =   SuscriptionPlan
        fields          =   ['id', 'name', 'price']


#=========================================
# SUSCRIPCION SERIALIZER
#=========================================
class SuscriptionSerializer(SuscriptionCreateMixin, serializers.ModelSerializer):
    id                  =    serializers.ReadOnlyField()
    user                =    serializers.HiddenField(**SuscriptionsFields['user'])
    plan_suscription    =    serializers.PrimaryKeyRelatedField(**SuscriptionsFields['plan_suscription'])
    start_date          =    serializers.ReadOnlyField()
    end_date            =    serializers.ReadOnlyField()
    class Meta:
        model           =   Suscription
        fields          =   ['id', 'user', 'plan_suscription', 'start_date', 'end_date']
        validators      =   [
            UniqueTogetherValidator(
                queryset    =   Suscription.objects.all(),
                fields      =   ['user', 'plan_suscription'],
                message     =   'Solo se admite una suscripción por usuario'  
            )
        ]
    def update(self, instance, validated_data):
        #Cambio directo de plan (sin pasarela): descarta cualquier plan pendiente de pago
        if 'plan_suscription' in validated_data:
            validated_data['pending_plan_suscription']  =   None
            if instance.status == 'Pendiente de pago':
                now                                 =   timezone.now()
                validated_data['status']            =   'Suscripción activa'
                validated_data['start_date']        =   now
                validated_data['end_date']          =   now + timedelta(days = 30)
        return super().update(instance, validated_data)

#=========================================
# SUSCRIPCION SERIALIZER LIST
#=========================================
class SuscriptionSerializerList(serializers.ModelSerializer):
    auth_user_id        =   serializers.IntegerField(source = 'user.user_id', read_only = True)
    plan_name           =   serializers.CharField(source = 'plan_suscription.name', read_only = True)
    plan_price          =   serializers.DecimalField(source = 'plan_suscription.price', max_digits = 12, decimal_places = 2, read_only = True)
    is_trial            =   serializers.BooleanField(source = 'plan_suscription.is_trial', read_only = True)
    pending_plan_name   =   serializers.CharField(source = 'pending_plan_suscription.name', read_only = True)
    user_name           =   serializers.CharField(source = 'user.user.username', read_only = True)
    user_email          =   serializers.CharField(source = 'user.user.email', read_only = True)
    business_name       =   serializers.CharField(source = 'user.business_name', read_only = True)
    status              =   serializers.CharField(read_only = True)
    auto_renew          =   serializers.BooleanField(read_only = True)
    cancelled_at        =   serializers.DateTimeField(read_only = True)
    access_until        =   serializers.SerializerMethodField()
    has_preapproval     =   serializers.SerializerMethodField()
    is_current          =   serializers.SerializerMethodField()
    class Meta:
        model           =   Suscription
        fields          =   ['id', 'user', 'auth_user_id', 'user_name', 'user_email', 'business_name', 'plan_suscription', 'plan_name', 'plan_price', 'is_trial', 'pending_plan_name', 'start_date', 'end_date', 'status', 'auto_renew', 'cancelled_at', 'access_until', 'has_preapproval', 'is_current']
    def get_access_until(self, obj):
        return obj.access_until()
    def get_has_preapproval(self, obj):
        return bool(obj.preapproval_id)
    def get_is_current(self, obj):
        return obj.grants_access()