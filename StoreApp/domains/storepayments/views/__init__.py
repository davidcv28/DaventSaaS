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
from .integrations import (
    FiscalProfileView,
    OAuthConfigView,
    StorageConfigView,
    StorageGuideView,
)
from .mp import (
    MpConnectView,
    MpDisconnectView,
    MpRefundView,
    MpStatusView,
)
from .webhook import StoreMpWebhookView

__all__   =   [
    'FiscalProfileView',
    'MpConnectView',
    'MpDisconnectView',
    'MpRefundView',
    'MpStatusView',
    'OAuthConfigView',
    'PublicOrderPayView',
    'StoreMpWebhookView',
    'StorePaymentConfigView',
    'StorageConfigView',
    'StorageGuideView',
]
