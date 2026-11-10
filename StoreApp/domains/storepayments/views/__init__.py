"""
Vistas del dominio storepayments.

Endpoints:
- Dueño (auth DAVENT, su tienda): mp/status, mp/connect, mp/disconnect,
  mp/refund/<order_id>, config (GET/PATCH).
- Comprador (público): stores/public/<slug>/orders/<token>/pay/.
- Webhook MP: webhooks/store-mp/<slug>/ (auth por firma x-signature).
"""
from .checkout import PublicOrderPayView
from .config import StorePaymentConfigView
from .mp import (
    MpConnectView,
    MpDisconnectView,
    MpRefundView,
    MpStatusView,
)
from .webhook import StoreMpWebhookView

__all__   =   [
    'MpConnectView',
    'MpDisconnectView',
    'MpRefundView',
    'MpStatusView',
    'PublicOrderPayView',
    'StoreMpWebhookView',
    'StorePaymentConfigView',
]
