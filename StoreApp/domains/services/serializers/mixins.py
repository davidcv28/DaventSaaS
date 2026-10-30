from rest_framework import serializers

from StoreApp.domains.stores.models import StoreCustomization

"""

Mixins de validación de los serializers del dominio Services.

"""
#==================================
# SERVICE MIXIN (nombre único por tienda + icono del catálogo cerrado)
#==================================
class ServiceMixinValidator:
    """
    Garantiza que el nombre sea único dentro de la tienda (además del
    UniqueConstraint del modelo, para devolver 400 en vez de 500) y que
    el icono sea uno del catálogo cerrado SERVICE_ICONS — nada libre.
    """
    def validate_name(self, value):
        name            =   value.strip()
        queryset        =   self.Meta.model.objects.filter(
            store           =   self.context['store'],
            name__iexact    =   name,
        )
        if self.instance:
            queryset    =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya tenés un servicio con ese nombre.')
        return name
    def validate_icon(self, value):
        icon            =   (value or '').strip().lower()
        return icon if icon in StoreCustomization.SERVICE_ICONS else 'wrench'
