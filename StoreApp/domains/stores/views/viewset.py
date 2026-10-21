from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from StoreApp.domains.stores.models                  import Store, StoreCustomization
from StoreApp.domains.stores.serializers.serializers import StorePublicSerializer, StoreCustomizationSerializer
from StoreApp.domains.stores.serializers.validators  import (
    RESERVED_SLUGS,
    validate_slug_format,
    validate_slug_available,
)
from StoreApp.domains.stores.services                import profile_has_benefit
from .viewset_base   import StoreBaseViewSet
from .viewset_config import StoreConfigs
"""

Viewsets del dominio Stores.

"""
#=========================================
# STORE VIEWSET
#=========================================
class StoreViewSet(StoreBaseViewSet):
    viewset_config  =   StoreConfigs

    def get_permissions(self):
        if self.action == 'public':
            return [AllowAny()]
        return super().get_permissions()
    #=========================================
    # SLUG AVAILABLE (check de disponibilidad para el onboarding)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = 'slug-available')
    def slug_available(self, request):
        slug        =   (request.query_params.get('slug') or '').strip().lower()
        if not validate_slug_format(slug):
            return Response({'slug': slug, 'available': False, 'reason': 'invalid'}, status = status.HTTP_200_OK)
        if slug in RESERVED_SLUGS:
            return Response({'slug': slug, 'available': False, 'reason': 'reserved'}, status = status.HTTP_200_OK)
        available   =   validate_slug_available(slug)
        return Response({'slug': slug, 'available': available, 'reason': None if available else 'taken'}, status = status.HTTP_200_OK)
    #=========================================
    # PUBLIC (resolución pública del link, sin auth)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)')
    def public(self, request, slug = None):
        store       =   get_object_or_404(
            Store.objects.select_related('user__city', 'user__province', 'customization'),
            slug = slug, is_published = True,
        )
        serializer  =   StorePublicSerializer(store)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # CUSTOMIZATION (diseño de la web pública, gated por el plan)
    #=========================================
    @action(detail = False, methods = ['get', 'put', 'patch'], url_path = 'customization')
    def customization(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if request.method != 'GET' and not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web está disponible en el Plan premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        if request.method == 'GET':
            return Response(StoreCustomizationSerializer(customization).data, status = status.HTTP_200_OK)
        serializer        =   StoreCustomizationSerializer(customization, data = request.data, partial = (request.method == 'PATCH'))
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {'Exito': 'El diseño de tu web se actualizó correctamente', 'customization': serializer.data},
            status = status.HTTP_200_OK,
        )
