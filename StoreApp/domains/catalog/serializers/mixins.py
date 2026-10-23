from rest_framework import serializers
from .config_fields import FeatureLimits
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
# CATEGORY SCHEMA MIXIN (plantilla de características de la categoría)
#==================================
class CategorySchemaMixinValidator:
    """
    Normaliza feature_schema: lista de nombres de atributos que la
    categoría sugiere a sus productos (ej. ['Talle', 'Material']).
    """
    def validate_feature_schema(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('La plantilla debe ser una lista de nombres.')
        if len(value) > FeatureLimits['schema_max']:
            raise serializers.ValidationError(f"La plantilla admite hasta {FeatureLimits['schema_max']} características.")
        cleaned             =   []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError('Cada característica debe ser un texto no vacío.')
            name            =   item.strip()
            if len(name) > FeatureLimits['schema_name_max']:
                raise serializers.ValidationError(f"Cada característica admite hasta {FeatureLimits['schema_name_max']} caracteres.")
            if name.lower() in [n.lower() for n in cleaned]:
                raise serializers.ValidationError(f'La característica "{name}" está repetida.')
            cleaned.append(name)
        return cleaned
#==================================
# PRODUCT MIXIN (category/brand deben pertenecer a la tienda)
#==================================
class ProductMixinValidator:
    """
    Normaliza features: objeto nombre/valor con las características del
    producto (la plantilla de la categoría las sugiere, el dueño puede
    sumar otras libres). Los valores se guardan como texto.
    """
    def validate_features(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('Las características deben ser un objeto nombre/valor.')
        if len(value) > FeatureLimits['entries_max']:
            raise serializers.ValidationError(f"El producto admite hasta {FeatureLimits['entries_max']} características.")
        cleaned             =   {}
        for raw_key, raw_val in value.items():
            key             =   raw_key.strip() if isinstance(raw_key, str) else ''
            if not key or len(key) > FeatureLimits['name_max']:
                raise serializers.ValidationError(f"Cada nombre admite entre 1 y {FeatureLimits['name_max']} caracteres.")
            if not isinstance(raw_val, (str, int, float, bool)):
                raise serializers.ValidationError(f'El valor de "{key}" debe ser un texto.')
            val             =   str(raw_val).strip()
            if not val or len(val) > FeatureLimits['value_max']:
                raise serializers.ValidationError(f"El valor de \"{key}\" admite entre 1 y {FeatureLimits['value_max']} caracteres.")
            if key.lower() in [k.lower() for k in cleaned]:
                raise serializers.ValidationError(f'La característica "{key}" está repetida.')
            cleaned[key]    =   val
        return cleaned
    def validate(self, attrs):
        store           =   self.context['store']
        for field in ('category', 'brand'):
            related     =   attrs.get(field)
            if related is not None and related.store_id != store.id:
                raise serializers.ValidationError({field: 'No pertenece a tu tienda.'})
        return attrs
