from rest_framework import serializers
"""

Mixins de validación de los serializers del dominio Catalog.

"""
#==================================
# STORE TAXONOMY MIXIN (categoría/marca dentro de la tienda del usuario)
#==================================
class TaxonomyMixinValidator:
    """
    Garantiza que el nombre sea único dentro de la tienda (además del
    UniqueConstraint del modelo, para devolver 400 en vez de 500).
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
            raise serializers.ValidationError('Ya existe una con ese nombre en tu tienda.')
        return name
#==================================
# PRODUCT MIXIN (category/brand deben pertenecer a la tienda)
#==================================
class ProductMixinValidator:
    def validate(self, attrs):
        store           =   self.context['store']
        for field in ('category', 'brand'):
            related     =   attrs.get(field)
            if related is not None and related.store_id != store.id:
                raise serializers.ValidationError({field: 'No pertenece a tu tienda.'})
        return attrs
