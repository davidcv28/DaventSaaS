from django.db import models
from rest_framework import serializers
from .config_fields import FeatureLimits, DiscountLimits
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
        #La oferta existe solo si es menor que el precio de lista (en un PATCH
        #el precio puede venir del registro actual).
        if 'offer_price' in attrs or 'price' in attrs:
            offer       =   attrs.get('offer_price', getattr(self.instance, 'offer_price', None))
            price       =   attrs.get('price', getattr(self.instance, 'price', None))
            if offer is not None and price is not None and offer >= price:
                raise serializers.ValidationError({'offer_price': 'La oferta tiene que ser menor que el precio.'})
        return attrs
#==================================
# DISCOUNT MIXIN (alcance coherente + pertenencia a la tienda + ventana)
#==================================
class DiscountMixinValidator:
    """
    Reglas del descuento programado: el objetivo del alcance (categoría,
    marca o productos) debe existir y pertenecer a la tienda del dueño,
    y la ventana exige ends_at > starts_at cuando hay fin.
    """
    def validate(self, attrs):
        from StoreApp.domains.catalog.models import Discount
        store           =   self.context['store']
        scope           =   attrs.get('scope', getattr(self.instance, 'scope', Discount.Scope.ALL))
        errors          =   {}
        #Pertenencia: un id de otra tienda nunca descuenta productos ajenos.
        for field in ('category', 'brand'):
            related     =   attrs.get(field)
            if related is not None and related.store_id != store.id:
                errors[field]   =   'No pertenece a tu tienda.'
        products        =   attrs.get('products')
        if products is not None:
            if len(products) > DiscountLimits['products_max']:
                errors['products']  =   f"El descuento admite hasta {DiscountLimits['products_max']} productos."
            elif any(product.store_id != store.id for product in products):
                errors['products']  =   'Hay productos que no pertenecen a tu tienda.'
        #El alcance exige su objetivo (en un PATCH puede venir del registro).
        if scope == Discount.Scope.CATEGORY:
            category    =   attrs.get('category', getattr(self.instance, 'category', None))
            if category is None:
                errors['category']  =   'Elegí la categoría a descontar.'
        elif scope == Discount.Scope.BRAND:
            brand       =   attrs.get('brand', getattr(self.instance, 'brand', None))
            if brand is None:
                errors['brand'] =   'Elegí la marca a descontar.'
        elif scope == Discount.Scope.PRODUCTS:
            chosen      =   attrs.get(
                'products',
                list(self.instance.products.all()) if self.instance is not None else None,
            )
            if not chosen:
                errors['products']  =   'Elegí al menos un producto.'
            elif 'products' not in errors:
                #Un producto solo vive en un grupo de ofertas a la vez: si ya
                #está en otro descuento de productos vigente o programado
                #(aunque esté pausado — reactivarlo chocaría), se rechaza.
                from django.utils import timezone
                taken       =   (
                    Discount.objects
                    .filter(
                        store       =   store,
                        scope       =   Discount.Scope.PRODUCTS,
                        products__in =  chosen,
                    )
                    .filter(
                        models.Q(ends_at__isnull = True) |
                        models.Q(ends_at__gt = timezone.now())
                    )
                )
                if self.instance is not None:
                    taken   =   taken.exclude(pk = self.instance.pk)
                taken       =   list(taken.distinct()[:4])
                if taken:
                    names   =   ', '.join(f'«{d.name}»' for d in taken[:3])
                    extra   =   f' y {len(taken) - 3} más' if len(taken) > 3 else ''
                    errors['products']  =   f'Hay productos que ya están en {names}{extra}: cada producto solo puede estar en un grupo de ofertas.'
        starts          =   attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        ends            =   attrs.get('ends_at', getattr(self.instance, 'ends_at', None))
        if starts is not None and ends is not None and ends <= starts:
            errors['ends_at']   =   'El fin tiene que ser posterior al inicio.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
