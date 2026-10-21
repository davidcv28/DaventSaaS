from rest_framework import serializers
from AdminApp.domains.payments.services import CreatePaymentQuery
"""
Mixins y defaults reutilizables para los serializers del dominio Payments.
"""

#==================================
# CURRENT USER PROFILE DEFAULT
# (HiddenField para Payment.user -> UserProfile)
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
# PAYMENT CREATE MIXIN
# (la suscripción debe pertenecer al perfil autenticado)
#==================================
class PaymentCreateMixin:
    def validate(self, attrs):
        suscription     =   attrs.get('suscription')
        profile         =   attrs.get('user')
        if suscription is not None and profile is not None and suscription.user_id != profile.id:
            raise serializers.ValidationError({
                'suscription'   :   'La suscripción seleccionada no pertenece a tu usuario.'
            })
        return attrs

#==================================
# PAYMENT CREATE METHOD
#==================================
class PaymentCreateMethod:
    def create(self, validated_data):
        return CreatePaymentQuery(validated_data)
