"""
Viewsets del dominio Invoices.
"""
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
