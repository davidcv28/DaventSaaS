from rest_framework import serializers
from AdminApp.domains.suscriptions.models import SuscriptionPlan
from SuscriptionApp.domains.benefits.models import Benefit
"""

Serializers del dominio benefits.
PlanCatalogSerializer arma la tarjeta pública de cada plan:
datos base de SuscriptionPlan + copy de PlanPresentation +
beneficios como dict {code: valor} listo para el frontend.

"""
#=========================================
# PLAN CATALOG SERIALIZER (tarjeta pública del plan)
#=========================================
class PlanCatalogSerializer(serializers.ModelSerializer):
    slug                        =   serializers.CharField(source = 'presentation.slug', read_only = True)
    tagline                     =   serializers.CharField(source = 'presentation.tagline', read_only = True)
    cta_label                   =   serializers.CharField(source = 'presentation.cta_label', read_only = True)
    bullets                     =   serializers.JSONField(source = 'presentation.bullets', read_only = True)
    featured                    =   serializers.BooleanField(source = 'presentation.featured', read_only = True)
    display_order               =   serializers.IntegerField(source = 'presentation.display_order', read_only = True)
    benefits                    =   serializers.SerializerMethodField()
    class Meta:
        model                   =   SuscriptionPlan
        fields                  =   ['id', 'name', 'price', 'slug', 'tagline', 'cta_label', 'bullets', 'featured', 'display_order', 'benefits']
    def get_benefits(self, plan):
        out                     =   {}
        for plan_benefit in plan.benefits.all():
            out[plan_benefit.benefit.code]  =   plan_benefit.value if plan_benefit.benefit.kind == Benefit.LIMIT else plan_benefit.enabled
        return out
