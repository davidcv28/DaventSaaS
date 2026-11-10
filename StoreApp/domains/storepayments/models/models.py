"""
Modelos del dominio storepayments (cobros de las tiendas DAVENT).

MpPayment registra cada intento/cobro de Mercado Pago del VENDEDOR
(preferencia emitida y payment notificado por webhook). NO guarda tokens:
las credenciales viven en StoreMpAccount (stores, cifradas con el vault).

StoreMpWebhookConfig guarda el webhook secret de la app MP del vendedor
(cifrado con el vault): la firma x-signature de cada notificación se
valida contra ESE secret, no contra uno global de DAVENT.

NOTA DE CONTRATO (track B, orders — en desarrollo paralelo): Order aún no
existe como modelo, así que MpPayment NO lleva FK a orders.Order. Se
denormalizan `order_id` (PK del pedido) y `tracking_token` (identificador
público) para trazabilidad y lookups. Cuando orders aterrice, una
migración puede promover order_id a ForeignKey sin cambiar la lógica.
"""

from django.db import models
from django.utils import timezone

from AdminApp.domains.invoices.services.vault import decrypt_secret, encrypt_secret
from StoreApp.domains.stores.models import Store


#=========================================
# MP PAYMENT (intento/cobro MP de un pedido de tienda)
#=========================================
class MpPayment(models.Model):
    """
    Un registro por intento de cobro MP del comprador:
    - La preferencia (Checkout Pro) crea la fila con `preference_id` y
      `mp_payment_id` NULL.
    - El webhook `/api/webhooks/store-mp/<slug>/` la adopta por
      `mp_payment_id` (único) o crea una fila nueva si el pago llegó sin
      preferencia registrada.
    `amount_mismatch` marca cobros cuyo transaction_amount no coincide
    con order.total: NO se acredita el pedido automáticamente (queda
    OrderEvent 'amount_mismatch' para revisión del dueño).
    """
    class Status(models.TextChoices):
        CREATED     =   'created',     'Preferencia creada'
        PENDING     =   'pending',     'Pendiente'
        APPROVED    =   'approved',    'Aprobado'
        REJECTED    =   'rejected',    'Rechazado'
        REFUNDED    =   'refunded',    'Reembolsado'
        CANCELLED   =   'cancelled',   'Cancelado'
    store                   =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'mp_payments', db_index = False)
    #PK del Order (track B) — ver nota de contrato en el docstring del módulo.
    order_id                =   models.BigIntegerField(null = True, blank = True, db_index = True, verbose_name = 'ID del pedido')
    tracking_token          =   models.CharField(max_length = 128, db_index = True, verbose_name = 'Token público del pedido')
    preference_id           =   models.CharField(max_length = 64, blank = True, default = '', verbose_name = 'Preferencia de MP')
    #Único por payment de MP; NULL hasta que el webhook lo conoce (Postgres
    #trata los NULL como distintos: varias preferencias pueden coexistir).
    mp_payment_id           =   models.CharField(max_length = 64, unique = True, null = True, blank = True, verbose_name = 'ID de pago de MP')
    status                  =   models.CharField(max_length = 20, choices = Status.choices, default = Status.CREATED, verbose_name = 'Estado')
    amount                  =   models.DecimalField(max_digits = 12, decimal_places = 2, verbose_name = 'Monto')
    currency                =   models.CharField(max_length = 3, default = 'ARS', verbose_name = 'Moneda')
    live_mode               =   models.BooleanField(null = True, blank = True, verbose_name = 'Cobro real (live) de Mercado Pago')
    mp_status_detail        =   models.CharField(max_length = 255, blank = True, default = '', verbose_name = 'Detalle de estado de Mercado Pago')
    amount_mismatch         =   models.BooleanField(default = False, verbose_name = 'Monto distinto al del pedido')
    created_at              =   models.DateTimeField(auto_now_add = True)
    updated_at              =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'storepayments'
        verbose_name            =   'Pago MP de tienda'
        verbose_name_plural     =   'Pagos MP de tiendas'
        indexes                 =   [
            models.Index(fields = ['store', 'created_at'], name = 'idx_storemp_store_created'),
            models.Index(fields = ['tracking_token'], name = 'idx_storemp_token'),
        ]
        constraints             =   [
            models.CheckConstraint(
                condition       =   models.Q(amount__gte = 0),
                name            =   'storemp_amount_non_negative',
            ),
        ]
    def __str__(self):
        return f'{self.store.slug} · {self.mp_payment_id or self.preference_id or self.pk} · {self.status}'
#=========================================
# STORE MP WEBHOOK CONFIG (secreto de firma del webhook del vendedor)
#=========================================
class StoreMpWebhookConfig(models.Model):
    """
    Webhook secret de la app de Mercado Pago DEL VENDEDOR. MP firma cada
    notificación con el secret configurado en SU aplicación; como las
    credenciales pegadas son las del vendedor, el secret también es suyo
    y viaja cifrado por el vault (purpose por tienda, igual que los tokens
    de StoreMpAccount — un blob de la tienda A no sirve en la B).

    El dueño lo pega en POST /api/store-payments/mp/connect/ (campo
    opcional `webhook_secret`); re-enviar connect actualiza el secret sin
    tocar los tokens.
    """
    PURPOSE_SECRET          =   'StoreMpWebhookConfig.webhook_secret'
    store                   =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'mp_webhook_config')
    webhook_secret_enc      =   models.TextField(blank = True, verbose_name = 'Webhook secret (cifrado)')
    updated_at              =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'storepayments'
        verbose_name            =   'Webhook MP de tienda'
        verbose_name_plural     =   'Webhooks MP de tiendas'
    def __str__(self):
        return f'mp-webhook:{self.store.slug}'
    @property
    def has_secret(self):
        return bool(self.webhook_secret_enc)
    def _purpose(self):
        #AAD por tienda: mismo criterio que StoreMpAccount._purpose.
        return f'{self.PURPOSE_SECRET}:{self.store_id}'
    def set_webhook_secret(self, secret):
        self.webhook_secret_enc =   encrypt_secret(secret.encode(), self._purpose()) if secret else ''
        self.updated_at         =   timezone.now()
    def get_webhook_secret(self):
        if not self.webhook_secret_enc:
            return ''
        return decrypt_secret(self.webhook_secret_enc, self._purpose()).decode()
    def clear_secret(self):
        self.set_webhook_secret('')
