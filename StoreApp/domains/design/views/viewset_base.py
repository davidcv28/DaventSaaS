from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

from DaventProject.throttling import PublicReadThrottle

"""

Viewsets del dominio Design.

Catálogo de patrones y estilos: lectura para cualquier usuario
autenticado, escritura solo staff. El visitante solo ve lo activo; el
staff ve todo y puede filtrar por categoría, tag o texto (q).

"""
#=========================================
# DESIGN BASE VIEWSET
#=========================================
class DesignCatalogViewSet(viewsets.ModelViewSet):
    permission_classes  =   [IsAuthenticated]
    lookup_field        =   'slug'
    lookup_value_regex  =   '[^/]+'
    list_serializer     =   None
    write_serializer    =   None

    def get_throttles(self):
        #El default es público (lo consume la web del cliente): scope
        #'public_read' en vez del anon global de 100/día.
        if self.action == 'default':
            return [PublicReadThrottle()]
        return super().get_throttles()

    def get_permissions(self):
        if self.action == 'default':
            return [AllowAny()]
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'list':
            return self.list_serializer
        return self.write_serializer

    def get_queryset(self):
        qs          =   super().get_queryset()
        params      =   self.request.query_params
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs      =   qs.filter(is_active = True)
        categoria   =   params.get('categoria', '').strip()
        if categoria:
            qs      =   qs.filter(categoria__iexact = categoria)
        tag         =   params.get('tag', '').strip()
        if tag:
            qs      =   qs.filter(tags__contains = [tag])
        query       =   params.get('q', '').strip()
        if query:
            qs      =   qs.filter(
                Q(slug__icontains = query)
                | Q(nombre__icontains = query)
                | Q(categoria__icontains = query)
            )
        return qs
