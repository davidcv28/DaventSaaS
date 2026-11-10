import secrets

from django.db import models
from django.db.models import Q

from AdminApp.domains.users.models.fields import EncryptedCharField
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.customers.models import Customer
from StoreApp.domains.stores.models import Store

"""

Pedidos de las webs de tienda (e-commerce DAVENT).

Reglas de diseño (PLAN_ECOMMERCE Fase 1 + PROMPT_MAESTRO §3):

- El contrato de compraventa es COMPRADOR ↔ DUEÑO DE TIENDA: DAVENT no
  cobra ni factura — los totales y snapshots son datos del pedido, no
  asientos contables de la plataforma.
- `Order.customer` es PROTECT: un pedido no puede perder a su comprador
  (la cuenta usa soft-delete `is_active`, nadie borra Customers en la
  práctica; si algún día se borra, el pedido queda como registro).
- Snapshot inmutable del comprador y de los items: nombre, email,
  teléfono, documento, dirección y precios se congelan AL CREAR — un
  cambio posterior del perfil o del catálogo no reescribe pedidos
  emitidos (mismo criterio que Invoice).
- PII: `customer_phone` y `customer_document` viajan CIFRADOS en reposo
  (EncryptedCharField del vault, un aad por campo — el dueño los lee en
  claro por el ORM porque el campo descifra transparente; la API pública
  de seguimiento NUNCA los expone). El documento solo se usa para
  facturar/entregar — se pide en el checkout y queda para el vendedor.
- `tracking_token` es el ÚNICO identificador público del pedido
  (secrets.token_urlsafe(24)): anti-IDOR — el id numérico jamás sale en
  endpoints públicos.
- `idempotency_key` por (store, key): el retry del cliente devuelve el
  MISMO pedido (UniqueConstraint parcial cuando no está vacía).
- Stock NO se descuenta acá: ocurre en orders.services.payments
  .mark_order_paid (al confirmar el pago, nunca al crear el pedido).
"""
#=========================================
# ORDER SEQUENCE (numerador legible por tienda: PED-0001)
#=========================================
class OrderSequence(models.Model):
    """
    Contador de pedidos por tienda. `create_order` lo incrementa dentro
    del atomic con la fila de Store bloqueada (select_for_update) — la
    numeración queda serializada por tienda y sin huecos por rollback
    (un número solo se consume cuando el pedido commitea).
    """
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'order_sequence')
    last_number                 =   models.PositiveIntegerField(default = 0, verbose_name = 'Último número asignado')
    class Meta:
        app_label               =   'orders'
        verbose_name            =   'Secuencia de pedidos'
        verbose_name_plural     =   'Secuencias de pedidos'
    def __str__(self):
        return f'orders:{self.store.slug} → {self.last_number}'
#=========================================
# ORDER (el pedido)
#=========================================
class Order(models.Model):
    """
    Pedido de una tienda. Los totales son Decimal(12,2) calculados
    server-side en services.checkout.create_order:
      - `subtotal`       = Σ line_total de los items YA con descuentos
                           (precio de lista − ofertas − dto. membresía).
      - `discount_total` = ahorro total vs precio de lista
                           (Σ (list_price − unit_price) × qty) — informativo.
      - `shipping_cost`  = 0 en MVP (no hay config de envío: se coordina
                           por WhatsApp; el campo ya existe para la fase
                           de envíos por zona).
      - `total`          = subtotal + shipping_cost.
    """
    class Status(models.TextChoices):
        PENDING_PAYMENT =   'PENDING_PAYMENT', 'Pendiente de pago'
        PAID            =   'PAID',            'Pagado'
        PACKING         =   'PACKING',         'Preparando'
        SHIPPED         =   'SHIPPED',         'Enviado'
        DELIVERED       =   'DELIVERED',       'Entregado'
        EXPIRED         =   'EXPIRED',         'Vencido'
        CANCELLED       =   'CANCELLED',       'Cancelado'
        REFUNDED        =   'REFUNDED',        'Reembolsado'
    class PaymentMethod(models.TextChoices):
        TRANSFER    =   'transfer',    'Transferencia / depósito'
        WHATSAPP    =   'whatsapp',    'Coordinar por WhatsApp'
        CASH        =   'cash',        'Efectivo / pago en persona'
        MP          =   'mp',          'Mercado Pago'
    class ShippingMethod(models.TextChoices):
        HOME        =   'home',        'Envío a domicilio'
        PICKUP      =   'pickup',      'Retiro en el local'
    #Máquina de estados (tabla permitida — la verdad vive acá y la
    #validan payments.advance_order/cancel_order/mark_order_*):
    #  PENDING_PAYMENT → PAID | EXPIRED | CANCELLED
    #  PAID            → PACKING | REFUNDED        (PAID ya cobró: no se cancela, se reembolsa)
    #  PACKING         → SHIPPED | REFUNDED
    #  SHIPPED         → DELIVERED | REFUNDED
    #  DELIVERED / EXPIRED / CANCELLED / REFUNDED → terminales
    TRANSITIONS               =   {
        Status.PENDING_PAYMENT :   {Status.PAID, Status.EXPIRED, Status.CANCELLED},
        Status.PAID            :   {Status.PACKING, Status.REFUNDED},
        Status.PACKING         :   {Status.SHIPPED, Status.REFUNDED},
        Status.SHIPPED         :   {Status.DELIVERED, Status.REFUNDED},
        Status.DELIVERED       :   set(),
        Status.EXPIRED         :   set(),
        Status.CANCELLED       :   set(),
        Status.REFUNDED        :   set(),
    }
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'orders', db_index = False)
    number                      =   models.PositiveIntegerField(verbose_name = 'Número interno')
    tracking_token              =   models.CharField(max_length = 64, unique = True, verbose_name = 'Token público de seguimiento')
    customer                    =   models.ForeignKey(Customer, on_delete = models.PROTECT, related_name = 'orders', db_index = False)
    #===== SNAPSHOT DEL COMPRADOR (inmutable al crear) =====
    customer_first_name         =   models.CharField(max_length = 150, blank = True, verbose_name = 'Nombre')
    customer_last_name          =   models.CharField(max_length = 150, blank = True, verbose_name = 'Apellido')
    customer_email              =   models.EmailField(max_length = 254, verbose_name = 'Email')
    #Teléfono y documento cifrados en reposo (EncryptedCharField: el
    #ciphertext nunca es igual dos veces; el dueño los lee descifrados).
    #El documento es opcional — el checkout lo pide solo si el vendedor
    #lo necesita para facturar (queda como dato fiscal del comprador).
    customer_phone              =   EncryptedCharField(aad = 'Order.customer_phone', max_length = 24, blank = True, verbose_name = 'Teléfono')
    customer_document_type      =   models.CharField(max_length = 4, blank = True, verbose_name = 'Tipo de documento')
    customer_document           =   EncryptedCharField(aad = 'Order.customer_document', max_length = 11, blank = True, verbose_name = 'Documento')
    #Dirección de envío snapshot (JSON: {label, line1, line2, city,
    #province, postal_code, country}) — para 'pickup' viaja {} y el
    #retiro se coordina con los datos de contacto de la tienda.
    shipping_address            =   models.JSONField(default = dict, blank = True, verbose_name = 'Dirección de envío (snapshot)')
    #===== ENVÍO / PAGO =====
    shipping_method             =   models.CharField(max_length = 10, choices = ShippingMethod.choices, default = ShippingMethod.HOME, verbose_name = 'Método de entrega')
    payment_method              =   models.CharField(max_length = 10, choices = PaymentMethod.choices, verbose_name = 'Método de pago')
    payment_ref                 =   models.CharField(max_length = 120, blank = True, verbose_name = 'Referencia de pago')
    #Lo completa el webhook de MP (track C) cuando el pago se acredita.
    mp_payment_id               =   models.CharField(max_length = 64, blank = True, db_index = True, verbose_name = 'ID de pago de Mercado Pago')
    #===== TOTALES (server-side) =====
    subtotal                    =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0, verbose_name = 'Subtotal (con descuentos)')
    discount_total              =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0, verbose_name = 'Descuentos aplicados')
    shipping_cost               =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0, verbose_name = 'Costo de envío')
    total                       =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0, verbose_name = 'Total')
    #===== CICLO DE VIDA =====
    status                      =   models.CharField(max_length = 20, choices = Status.choices, default = Status.PENDING_PAYMENT, verbose_name = 'Estado')
    expires_at                  =   models.DateTimeField(verbose_name = 'Vence el pago')
    paid_at                     =   models.DateTimeField(null = True, blank = True, verbose_name = 'Pagado el')
    idempotency_key             =   models.CharField(max_length = 80, blank = True, default = '', verbose_name = 'Clave de idempotencia')
    #Nº de factura/CAE REAL que el vendedor emite en ARCA por fuera y
    #carga después — NO es un comprobante fiscal de DAVENT.
    invoice_ref                 =   models.CharField(max_length = 80, blank = True, verbose_name = 'Nº de factura del vendedor')
    #Snapshot de payment_config.require_payment_proof al crear: el
    #comprador puede subir comprobante en métodos manuales aunque el
    #dueño no lo exija (services/checkout lo documenta).
    proof_required              =   models.BooleanField(default = False, verbose_name = 'Comprobante de pago requerido')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'orders'
        verbose_name            =   'Pedido'
        verbose_name_plural     =   'Pedidos'
        ordering                =   ['-created_at', '-id']
        indexes                 =   [
            #Bandeja del dueño: filtro por estado + orden por fecha.
            models.Index(fields = ['store', 'status', 'created_at'], name = 'idx_order_store_status_date'),
        ]
        constraints             =   [
            models.UniqueConstraint(fields = ['store', 'number'], name = 'uq_order_store_number'),
            #Idempotencia del checkout: una clave = un pedido por tienda.
            #Parcial (solo cuando no está vacía) para no bloquear los
            #pedidos creados sin clave.
            models.UniqueConstraint(
                fields          =   ['store', 'idempotency_key'],
                condition       =   ~Q(idempotency_key = ''),
                name            =   'uq_order_store_idempotency',
            ),
        ]
    def __str__(self):
        return f'{self.code} ({self.store.slug})'
    @property
    def code(self):
        """Número legible del pedido (PED-0001) — display, no PK."""
        return f'PED-{self.number:04d}'
    @property
    def is_terminal(self):
        return self.status in (self.Status.DELIVERED, self.Status.EXPIRED, self.Status.CANCELLED, self.Status.REFUNDED)
#=========================================
# ORDER ITEM (snapshot inmutable de la línea)
#=========================================
class OrderItem(models.Model):
    """
    Línea del pedido con precio/nombre/imagen CONGELADOS al crear — si el
    producto se edita o borra después, el pedido emitido no cambia.
    `product` es SET_NULL: el historial sobrevive al borrado del catálogo
    (el snapshot ya tiene todo lo necesario para mostrar/cobrar).
    """
    order                       =   models.ForeignKey(Order, on_delete = models.CASCADE, related_name = 'items', db_index = False)
    product                     =   models.ForeignKey(Product, on_delete = models.SET_NULL, related_name = 'order_items', null = True, blank = True, db_index = False)
    name                        =   models.CharField(max_length = 160, verbose_name = 'Nombre (snapshot)')
    list_price                  =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0, verbose_name = 'Precio de lista (snapshot)')
    unit_price                  =   models.DecimalField(max_digits = 12, decimal_places = 2, verbose_name = 'Precio unitario cobrado (snapshot)')
    qty                         =   models.PositiveIntegerField(verbose_name = 'Cantidad')
    line_total                  =   models.DecimalField(max_digits = 12, decimal_places = 2, verbose_name = 'Total de línea')
    image_key                   =   models.CharField(max_length = 200, blank = True, verbose_name = 'Imagen (key en R2, snapshot)')
    class Meta:
        app_label               =   'orders'
        verbose_name            =   'Item de pedido'
        verbose_name_plural     =   'Items de pedido'
        ordering                =   ['id']
        indexes                 =   [
            models.Index(fields = ['order'], name = 'idx_orderitem_order'),
        ]
    def __str__(self):
        return f'{self.qty}x {self.name} (order {self.order_id})'
#=========================================
# ORDER EVENT (bitácora append-only del pedido)
#=========================================
class OrderEvent(models.Model):
    """
    Evento de la línea de tiempo del pedido. APPEND-ONLY por contrato:
    nunca se actualiza ni se borra (no hay endpoints de escritura fuera
    de services.events.append_event — el único punto de creación; el
    track F engancha acá mails/notificaciones).
    """
    class Actor(models.TextChoices):
        CUSTOMER    =   'customer',    'Comprador'
        OWNER       =   'owner',       'Dueño de la tienda'
        SYSTEM      =   'system',      'Sistema'
        MP          =   'mp',          'Mercado Pago'
    order                       =   models.ForeignKey(Order, on_delete = models.CASCADE, related_name = 'events', db_index = False)
    kind                        =   models.CharField(max_length = 40, verbose_name = 'Tipo de evento')
    status_from                 =   models.CharField(max_length = 20, blank = True, default = '', verbose_name = 'Estado anterior')
    status_to                   =   models.CharField(max_length = 20, blank = True, default = '', verbose_name = 'Estado nuevo')
    actor                       =   models.CharField(max_length = 10, choices = Actor.choices, default = Actor.SYSTEM, verbose_name = 'Actor')
    note                        =   models.CharField(max_length = 300, blank = True, verbose_name = 'Nota')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'orders'
        verbose_name            =   'Evento de pedido'
        verbose_name_plural     =   'Eventos de pedidos'
        ordering                =   ['created_at', 'id']
        indexes                 =   [
            models.Index(fields = ['order', 'created_at'], name = 'idx_orderevent_order_date'),
        ]
    def __str__(self):
        return f'{self.kind} order={self.order_id}'
#=========================================
# PAYMENT PROOF (comprobante de pago subido por el comprador)
#=========================================
class PaymentProof(models.Model):
    """
    Comprobante de transferencia/depósito que el comprador adjunta al
    pedido. OneToOne: re-subir REEMPLAZA la imagen (el service borra el
    objeto viejo de R2). `image_key` apunta a un WebP normalizado
    (normalize_image → put_object, carpeta stores/<id>/proofs/).
    """
    order                       =   models.OneToOneField(Order, on_delete = models.CASCADE, related_name = 'proof')
    image_key                   =   models.CharField(max_length = 200, verbose_name = 'Imagen (key en R2)')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'orders'
        verbose_name            =   'Comprobante de pago'
        verbose_name_plural     =   'Comprobantes de pago'
    def __str__(self):
        return f'proof:order={self.order_id}'
#=========================================
# TRACKING TOKEN (generación centralizada)
#=========================================
def new_tracking_token():
    """Identificador público anti-IDOR del pedido (~43 chars urlsafe)."""
    return secrets.token_urlsafe(24)
