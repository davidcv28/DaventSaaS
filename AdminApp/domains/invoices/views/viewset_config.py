"""
Configuración de los viewsets del dominio Invoices.
queryset y serializer se pasan como lambda view: ... y se ejecutan en la base.
"""
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from AdminApp.domains.invoices.models import Invoice
from AdminApp.domains.invoices.serializers import InvoiceSerializer

_INVOICE_RELATED = (
    'user', 'user__province', 'user__city', 'user__user',
    'payment', 'payment__suscription', 'payment__suscription__plan_suscription',
)

#=========================================
# INVOICE CONFIGS
#=========================================
InvoiceUserConfig = {
    # Solo las facturas del usuario autenticado (nunca las de terceros).
    'queryset'      :   lambda view : Invoice.objects.select_related(*_INVOICE_RELATED)
                            .filter(user__user = view.request.user)
                            .order_by('-issued_at', '-number'),
    'serializer'    :   lambda view : InvoiceSerializer,
    'permissions'   :   [IsAuthenticated]
}
#=========================================
# INVOICE ADMIN CONFIGS
#=========================================
InvoiceAdminConfig = {
    'queryset'      :   lambda view : Invoice.objects.select_related(*_INVOICE_RELATED)
                            .all().order_by('-issued_at', '-number'),
    'serializer'    :   lambda view : InvoiceSerializer,
    'permissions'   :   [IsAuthenticated, IsAdminUser]
}
