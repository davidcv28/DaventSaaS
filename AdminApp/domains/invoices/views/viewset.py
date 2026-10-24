"""
Viewsets del dominio Invoices.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from AdminApp.domains.invoices.services import RequestCaeQuery, afip_enabled
from AdminApp.domains.invoices.views.viewset_base import InvoiceBaseViewSet
from AdminApp.domains.invoices.views.viewset_config import InvoiceUserConfig, InvoiceAdminConfig
#=========================================
# INVOICE VIEWSET
#=========================================
class InvoiceViewSet(InvoiceBaseViewSet):
    config_view = InvoiceUserConfig

#=========================================
# INVOICE ADMIN VIEWSET
#=========================================
class InvoiceAdminViewSet(InvoiceBaseViewSet):
    config_view = InvoiceAdminConfig

    #=========================================
    # RETRY CAE ACTION (reintenta el pedido a ARCA de una factura en error)
    #=========================================
    @action(detail = True, methods = ['post'], url_path = 'retry-cae')
    def retry_cae(self, request, pk = None):
        invoice     =   self.get_object()
        if invoice.cae:
            return Response({'detail': 'La factura ya tiene CAE otorgado.'}, status = status.HTTP_400_BAD_REQUEST)
        if not afip_enabled():
            return Response(
                {'detail': 'La integración con ARCA está apagada (AFIP_ENABLED/AFIP_CUIT/AFIP_CERT/AFIP_KEY).'},
                status = status.HTTP_503_SERVICE_UNAVAILABLE)
        RequestCaeQuery(invoice)
        invoice.refresh_from_db()
        return Response(self.get_serializer(invoice).data, status = status.HTTP_200_OK)
