from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from AdminApp.domains.suscriptions.models import (
    Coupon,
    CouponRedemption,
    Suscription,
    SuscriptionPlan,
)

from .config_fields import SuscriptionsFields, SuscriptionsPlanFields
from .mixins import SuscriptionCreateMixin, SuscriptionPlanMixinValidator

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
    def create(self, validated_data):
        #La suscripción nace IMPAGA: el acceso lo otorga la acreditación del
        #cobro (ApplyPendingPlanQuery), nunca el alta en sí. Sin esto el
        #default del modelo creaba una suscripción activa de 30 días gratis.
        now                                     =   timezone.now()
        validated_data['status']                =   Suscription.STATUS_PENDING_PAYMENT
        validated_data['start_date']            =   now
        validated_data['end_date']              =   now
        try:
            return super().create(validated_data)
        except IntegrityError:
            #Doble POST concurrente: el unique de user le gana al pre-check
            #del mixin — 400 en vez de 500.
            raise serializers.ValidationError({'plan_suscription': 'Ya tienes una suscripción activa. Usa "Cambiar plan".'})
    def update(self, instance, validated_data):
        #SEGURIDAD: el plan NUNCA se cambia directo desde este endpoint —
        #eso otorgaba cualquier plan pago sin pasar por el cobro.
        plan    =   validated_data.pop('plan_suscription', None)
        if plan is None:
            return instance
        if instance.status == Suscription.STATUS_PENDING_PAYMENT:
            #Suscripción impaga: el plan elegido se corrige libremente (no
            #otorga acceso hasta que el pago se acredite).
            instance.plan_suscription   =   plan
            instance.save(update_fields = ['plan_suscription'])
            return instance
        #Suscripción vigente o pagada: el cambio queda pendiente y se aplica
        #recién cuando el cobro se acredita (checkout o débito automático).
        instance.pending_plan_suscription   =   plan
        instance.save(update_fields = ['pending_plan_suscription'])
        return instance

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
    first_name          =   serializers.CharField(source = 'user.first_name', read_only = True)
    last_name           =   serializers.CharField(source = 'user.last_name', read_only = True)
    business_name       =   serializers.CharField(source = 'user.business_name', read_only = True)
    status              =   serializers.CharField(read_only = True)
    auto_renew          =   serializers.BooleanField(read_only = True)
    cancelled_at        =   serializers.DateTimeField(read_only = True)
    access_until        =   serializers.SerializerMethodField()
    has_preapproval     =   serializers.SerializerMethodField()
    is_current          =   serializers.SerializerMethodField()
    class Meta:
        model           =   Suscription
        fields          =   ['id', 'user', 'auth_user_id', 'user_name', 'user_email', 'first_name', 'last_name', 'business_name', 'plan_suscription', 'plan_name', 'plan_price', 'is_trial', 'pending_plan_name', 'start_date', 'end_date', 'status', 'auto_renew', 'cancelled_at', 'access_until', 'has_preapproval', 'is_current']
    def get_access_until(self, obj):
        return obj.access_until()
    def get_has_preapproval(self, obj):
        return bool(obj.preapproval_id)
    def get_is_current(self, obj):
        return obj.grants_access()

#=========================================
# COUPON SERIALIZER (alta/edición desde el admin)
#=========================================
class CouponSerializer(serializers.ModelSerializer):
    #El plan de prueba no es elegible para promos (no es reactivable).
    plan                =   serializers.PrimaryKeyRelatedField(queryset = SuscriptionPlan.objects.filter(is_trial = False))
    class Meta:
        model           =   Coupon
        fields          =   ['id', 'code', 'plan', 'days', 'max_uses', 'expires_at', 'is_active']
        extra_kwargs    =   {
            'max_uses'      :   {'required': False, 'allow_null': True},
            'expires_at'    :   {'required': False, 'allow_null': True},
            'is_active'     :   {'required': False},
        }
    def validate_code(self, value):
        #El canje es case-insensitive: el código se normaliza a mayúsculas
        #para que 'flyer7' y 'FLYER7' no coexistan como cupones distintos.
        code            =   str(value or '').strip().upper()
        if len(code) < 3:
            raise serializers.ValidationError('El código debe tener al menos 3 caracteres.')
        queryset        =   Coupon.objects.filter(code__iexact = code)
        if self.instance:
            queryset    =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe un cupón con ese código.')
        return code
    def validate_days(self, value):
        if value < 1:
            raise serializers.ValidationError('Los días deben ser al menos 1.')
        return value

#=========================================
# COUPON REDEMPTION SERIALIZER LIST (auditoría de canjes)
#=========================================
class CouponRedemptionSerializerList(serializers.ModelSerializer):
    user_name           =   serializers.CharField(source = 'user.user.username', read_only = True)
    user_email          =   serializers.CharField(source = 'user.user.email', read_only = True)
    business_name       =   serializers.CharField(source = 'user.business_name', read_only = True)
    class Meta:
        model           =   CouponRedemption
        fields          =   ['id', 'user_name', 'user_email', 'business_name', 'redeemed_at']

#=========================================
# MY COUPON REDEMPTION SERIALIZER (vista del cliente: sus canjes)
#=========================================
class MyCouponRedemptionSerializer(serializers.ModelSerializer):
    code                =   serializers.CharField(source = 'coupon.code', read_only = True)
    plan_name           =   serializers.CharField(source = 'coupon.plan.name', read_only = True)
    days                =   serializers.IntegerField(source = 'coupon.days', read_only = True)
    class Meta:
        model           =   CouponRedemption
        fields          =   ['id', 'code', 'plan_name', 'days', 'redeemed_at']

#=========================================
# COUPON SERIALIZER LIST (panel admin)
#=========================================
class CouponSerializerList(serializers.ModelSerializer):
    plan_name           =   serializers.CharField(source = 'plan.name', read_only = True)
    uses                =   serializers.SerializerMethodField()
    redemptions         =   CouponRedemptionSerializerList(many = True, read_only = True)
    class Meta:
        model           =   Coupon
        fields          =   ['id', 'code', 'plan', 'plan_name', 'days', 'max_uses', 'expires_at', 'is_active', 'uses', 'created_at', 'redemptions']
    def get_uses(self, obj):
        return len(obj.redemptions.all())