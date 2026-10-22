"""
Base de los viewsets del dominio Invoices.
"""
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated

#=========================================
# INVOICE BASE VIEWSET
#=========================================
class InvoiceBaseViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    config_view = {}
    
    def get_queryset(self):
        return self.config_view['queryset'](self)
    
    def get_serializer_class(self):
        return self.config_view['serializer'](self)
    
    def get_permissions(self):
        #Sin 'permissions' en la config se cae a IsAuthenticated (fail-closed).
        permissions = self.config_view.get('permissions', [IsAuthenticated])
        return [permission() for permission in permissions]
