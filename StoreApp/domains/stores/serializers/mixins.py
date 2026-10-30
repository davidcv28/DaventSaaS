from rest_framework import serializers

from StoreApp.domains.stores.models import Store

from .validators import RESERVED_SLUGS, validate_slug_format

"""

Mixins de validación de los serializers del dominio Stores.

"""
#==================================
# STORE MIXIN VALIDATOR
#==================================
class StoreMixinValidator:

    #VALIDATE SLUG
    def validate_slug(self, value):
        slug            =   value.strip().lower()
        errors          =   []
        if not validate_slug_format(slug):
            errors.append('El link solo admite letras minúsculas, números y guiones (sin guiones al principio ni al final)')
        if slug in RESERVED_SLUGS:
            errors.append('Ese link está reservado por la plataforma. Elegí otro')
        queryset        =   Store.objects.filter(slug = slug)
        if self.instance:
            queryset    =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            errors.append('Ese link ya está en uso. Elegí otro')
        if errors:
            raise serializers.ValidationError(errors)
        return slug
#==================================
# STORE CREATE MIXIN (una sola tienda por perfil)
#==================================
class StoreCreateMixin:
    def validate(self, attrs):
        if self.instance is None:
            profile = attrs.get('user')
            if profile is not None and Store.objects.filter(user = profile).exists():
                raise serializers.ValidationError({
                    'slug': 'Ya tenés tu link público. Podés renombrarlo desde tu tienda.'
                })
        return attrs
