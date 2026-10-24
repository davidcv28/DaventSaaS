from rest_framework import serializers
from AdminApp.domains.suscriptions.models import SuscriptionPlan, Suscription
import re
"""

Creamos los Mixins para las disintas operaciones de los serializers

"""

#==================================
# SUSCRIPTION PLAN MIXIN VALIDATOR
#==================================
class SuscriptionPlanMixinValidator:

    #VALIDATE NAME
    def validate_name(self, value):
        name_obj        =   value.strip().upper()
        queryset        =   SuscriptionPlan.objects.filter(name__iexact = name_obj)
        errors          =   []
        if self.instance:
            queryset    =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            errors.append('El nombre del plan ingresado ya existe')
        #El ^ anclado invertía el chequeo: rechazaba todo nombre que EMPIEZA
        #con letra (o sea, cualquier nombre válido). Se buscan caracteres
        #prohibidos (números/símbolos) en cualquier posición.
        if re.search(r'[^a-zA-ZñÑáéíóúÁÉÍÓÚ\s]', name_obj):
            errors.append('En este campo no se admiten números ni caracteres especiales')
        if errors:
            raise serializers.ValidationError(errors)
        return name_obj

#==================================

#==================================
# CURRENT USER PROFILE DEFAULT (HiddenField para Suscription.user)
#==================================
class CurrentUserProfileDefault:
    requires_context = True
    def __call__(self, serializer_field):
        from AdminApp.domains.users.models import UserProfile
        request = serializer_field.context.get('request')
        if not request or getattr(request.user, 'is_anonymous', True):
            raise serializers.ValidationError('Autenticación requerida.')
        try:
            return UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError('Tu usuario aún no tiene perfil comercial.')
    def __repr__(self):
        return '%s()' % self.__class__.__name__

#==================================
# SUSCRIPTION CREATE MIXIN (una sola suscripción por perfil)
#==================================
class SuscriptionCreateMixin:
    def validate(self, attrs):
        if self.instance is None:
            profile = attrs.get('user')
            if profile is not None and Suscription.objects.filter(user=profile).exists():
                raise serializers.ValidationError({
                    'plan_suscription': 'Ya tienes una suscripción activa. Usa "Cambiar plan".'
                })
        return attrs

