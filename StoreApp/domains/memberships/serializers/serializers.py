from decimal import Decimal

from rest_framework import serializers

from StoreApp.domains.memberships.models import StorePlan, StoreSubscription
from StoreApp.domains.memberships.services.benefits import (
    is_vigente,
    plan_benefit_codes,
    store_display_name,
)

"""

Serializers del dominio memberships.

- StorePlanSerializer (dueño): `store` JAMÁS es campo del payload — lo
  inyecta el viewset desde request.user (mass-assignment imposible).
- Los serializers de suscripción exponen solo lo que cada actor puede
  ver: el dueño ve email/nombre de SU cliente; el comprador ve su plan
  y estado, nunca datos de otros.
- `benefits` viaja como lista de códigos del contrato
  (services/benefits.MEMBER_BENEFITS) y solo cuando la suscripción está
  vigente — un pending/cancelled/vencido devuelve [].
"""
#=========================================
# STORE PLAN (escritura + lectura del dueño)
#=========================================
class StorePlanSerializer(serializers.ModelSerializer):
    #Anotados por el viewset (Count con distinct) — cero N+1 en el list.
    subscriptions_count          =   serializers.IntegerField(read_only = True)
    active_subscriptions_count   =   serializers.IntegerField(read_only = True)
    class Meta:
        model               =   StorePlan
        fields              =   [
            'id', 'name', 'price', 'period', 'period_days',
            'has_digital_card', 'has_free_shipping', 'has_exclusive_discounts',
            'discount_percent', 'has_exclusive_access', 'is_active', 'position',
            'subscriptions_count', 'active_subscriptions_count', 'created_at',
        ]
        read_only_fields    =   ['id', 'created_at', 'subscriptions_count', 'active_subscriptions_count']
    #Tope defensivo del período 'custom' (~10 años): un typo de días no
    #puede crear un plan "eterno" ni un vigente_hasta desbordado.
    CUSTOM_PERIOD_DAYS_MAX       =   3650
    def validate(self, attrs):
        instance    =   self.instance
        period      =   attrs.get('period', getattr(instance, 'period', StorePlan.PERIOD_MONTHLY))
        #Coherencia período/días: monthly=30 y yearly=365 los fija el
        #servidor SIEMPRE (se pisa el valor recibido — un period_days
        #suelto no cambia la duración de un plan mensual/anual). Solo
        #'custom' respeta el period_days del dueño.
        if period in StorePlan.PERIOD_DAYS:
            attrs['period_days']    =   StorePlan.PERIOD_DAYS[period]
        elif period == StorePlan.PERIOD_CUSTOM:
            period_days =   attrs.get('period_days', getattr(instance, 'period_days', None))
            try:
                period_days =   int(period_days)
            except (TypeError, ValueError):
                period_days =   None
            if period_days is None or not (1 <= period_days <= self.CUSTOM_PERIOD_DAYS_MAX):
                raise serializers.ValidationError({'period_days': f'El plan personalizado dura de 1 a {self.CUSTOM_PERIOD_DAYS_MAX} días.'})
            attrs['period_days']    =   period_days
        else:
            raise serializers.ValidationError({'period': 'Período inválido.'})
        #Coherencia beneficios/descuento: has_exclusive_discounts SIN un
        #porcentaje >0 no regala nada — se exige el % (decisión
        #documentada). Al apagar el flag el % se limpia a 0 para que no
        #queden restos que un cambio posterior reactive sin querer.
        has_discounts   =   attrs.get('has_exclusive_discounts', getattr(instance, 'has_exclusive_discounts', False))
        percent         =   attrs.get('discount_percent', getattr(instance, 'discount_percent', Decimal('0')))
        percent         =   Decimal(str(percent or 0))
        if percent < 0 or percent > 100:
            raise serializers.ValidationError({'discount_percent': 'El descuento de miembro va de 0 a 100%.'})
        if has_discounts:
            if percent <= 0:
                raise serializers.ValidationError({'discount_percent': 'Para ofrecer descuentos exclusivos indicá el porcentaje de miembro (1-100%).'})
        else:
            attrs['discount_percent']   =   Decimal('0')
        return attrs
#=========================================
# STORE PLAN (resumen anidado en suscripciones — sin los counts
# anotados del listado del dueño, que no existen en este contexto)
#=========================================
class StorePlanBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model                   =   StorePlan
        fields                  =   [
            'id', 'name', 'price', 'period', 'period_days',
            'has_digital_card', 'has_free_shipping', 'has_exclusive_discounts',
            'discount_percent', 'has_exclusive_access', 'is_active', 'position',
        ]
#=========================================
# STORE PLAN (catálogo público del comprador)
#=========================================
class StorePlanPublicSerializer(serializers.ModelSerializer):
    """
    Plan exhibible/contratable en la web de la tienda: precio, período
    y beneficios como códigos del contrato (nunca flags internos ni
    conteos del dueño).
    """
    benefits                    =   serializers.SerializerMethodField()
    duration_days               =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StorePlan
        fields                  =   ['id', 'name', 'price', 'period', 'period_days', 'duration_days', 'discount_percent', 'benefits']
    def get_benefits(self, plan):
        return sorted(plan_benefit_codes(plan))
    def get_duration_days(self, plan):
        return plan.duration_days()
#=========================================
# SUSCRIPCIÓN — helpers compartidos
#=========================================
def _benefits_of(subscription):
    #Los beneficios viajan SOLO si la suscripción otorga algo ahora
    #mismo (is_vigente = status active + vigente_hasta>now): un pending
    #muestra [] aunque el plan tenga flags.
    return sorted(plan_benefit_codes(subscription.plan)) if is_vigente(subscription) else []
#=========================================
# STORE SUBSCRIPTION (lectura del dueño — SU cliente)
#=========================================
class StoreSubscriptionOwnerSerializer(serializers.ModelSerializer):
    plan                        =   StorePlanBriefSerializer(read_only = True)
    customer_email              =   serializers.EmailField(source = 'membership.customer.email', read_only = True)
    customer_first_name         =   serializers.CharField(source = 'membership.customer.first_name', read_only = True)
    customer_last_name          =   serializers.CharField(source = 'membership.customer.last_name', read_only = True)
    is_vigente                  =   serializers.SerializerMethodField()
    benefits                    =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StoreSubscription
        fields                  =   [
            'id', 'status', 'plan', 'payment_method', 'payment_ref', 'public_token',
            'started_at', 'vigente_hasta', 'is_vigente', 'benefits',
            'customer_email', 'customer_first_name', 'customer_last_name',
            'created_at', 'updated_at',
        ]
        read_only_fields        =   fields
    def get_is_vigente(self, subscription):
        return is_vigente(subscription)
    def get_benefits(self, subscription):
        return _benefits_of(subscription)
#=========================================
# STORE SUBSCRIPTION (lectura del comprador — SU plan/estado)
#=========================================
class StoreSubscriptionCustomerSerializer(serializers.ModelSerializer):
    plan                        =   StorePlanPublicSerializer(read_only = True)
    store_slug                  =   serializers.CharField(source = 'membership.store.slug', read_only = True)
    store_name                  =   serializers.SerializerMethodField()
    is_vigente                  =   serializers.SerializerMethodField()
    benefits                    =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StoreSubscription
        fields                  =   [
            'id', 'status', 'plan', 'store_slug', 'store_name', 'payment_method',
            'public_token', 'started_at', 'vigente_hasta', 'is_vigente', 'benefits',
            'created_at', 'updated_at',
        ]
        read_only_fields        =   fields
    def get_store_name(self, subscription):
        return store_display_name(subscription.membership.store)
    def get_is_vigente(self, subscription):
        return is_vigente(subscription)
    def get_benefits(self, subscription):
        return _benefits_of(subscription)
#=========================================
# MEMBERSHIP CARD (tarjeta digital — misma forma para el dueño del
# token autenticado y para el endpoint público por public_token)
#=========================================
class MembershipCardSerializer(serializers.Serializer):
    """
    Datos mínimos para renderizar la tarjeta digital del miembro.
    NUNCA expone email, teléfono ni documento del cliente — solo
    nombre + inicial del apellido, nombre de la tienda, plan, vigencia
    y beneficios activos.
    """
    store_slug                  =   serializers.SerializerMethodField()
    store_name                  =   serializers.SerializerMethodField()
    member_name                 =   serializers.SerializerMethodField()
    plan_name                   =   serializers.SerializerMethodField()
    vigente_hasta               =   serializers.DateTimeField(read_only = True)
    benefits                    =   serializers.SerializerMethodField()
    def _store(self, subscription):
        return subscription.membership.store
    def _membership(self, subscription):
        return subscription.membership
    def get_store_slug(self, subscription):
        return self._store(subscription).slug
    def get_store_name(self, subscription):
        return store_display_name(self._store(subscription))
    def get_member_name(self, subscription):
        #Nombre + inicial del apellido ("María P.") — patron del review
        #público: alcanza para el staff del comercio sin exponer la
        #identidad completa. NUNCA cae al email (es PII en una tarjeta
        #pública): sin nombre cargado queda 'Miembro'.
        customer        =   self._membership(subscription).customer
        first           =   (customer.first_name or '').strip()
        last            =   (customer.last_name or '').strip()
        if first and last:
            return f'{first} {last[0]}.'
        if first:
            return first
        if last:
            return f'{last[0]}.'
        return 'Miembro'
    def get_plan_name(self, subscription):
        plan    =   subscription.plan
        return plan.name if plan else ''
    def get_benefits(self, subscription):
        return sorted(plan_benefit_codes(subscription.plan)) if is_vigente(subscription) else []
