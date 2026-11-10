from django.db import models

from StoreApp.domains.catalog.models import Product
from StoreApp.domains.customers.models import Customer
from StoreApp.domains.stores.models import Store

"""

Carrito de compras del comprador (e-commerce DAVENT).

Un `Cart` por (customer, store): el mismo comprador puede tener un
carrito en cada web de tienda donde compra. `CartItem` guarda SOLO
referencias (product + qty) — los precios NUNCA se congelan acá: se
resuelven al leer contra `effective_pricing_of` + el descuento de
membresía vigente (services.cart.cart_payload), igual que en el pedido.

Decisiones:
- `CartItem.product` es CASCADE (no PROTECT ni SET_NULL): si el dueño
  borra el producto, la línea del carrito desaparece — un carrito con
  items rotos no sirve y el pedido usa su propio snapshot inmutable.
- NO hay reserva de stock en el carrito: el descuento ocurre recién al
  confirmar el pago del pedido (select_for_update en orders.payments).
- qty acotada a MAX_QTY (100) en service — el serializer también la
  valida; la constraint es la segunda capa anti-abuso.

"""
#=========================================
# CART (uno por comprador y tienda)
#=========================================
class Cart(models.Model):
    customer                    =   models.ForeignKey(Customer, on_delete = models.CASCADE, related_name = 'carts', db_index = False)
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'carts', db_index = False)
    created_at                  =   models.DateTimeField(auto_now_add = True)
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'cart'
        verbose_name            =   'Carrito'
        verbose_name_plural     =   'Carritos'
        constraints             =   [
            #El unique (customer, store) ya indexa la tupla en el orden
            #del checkout; no hacen falta índices extra.
            models.UniqueConstraint(fields = ['customer', 'store'], name = 'uq_cart_customer_store'),
        ]
    def __str__(self):
        return f'cart:{self.customer_id}@{self.store_id}'
#=========================================
# CART ITEM (referencia viva — precio resuelto al leer)
#=========================================
class CartItem(models.Model):
    """
    Línea del carrito. Unique (cart, product): re-agregar el mismo
    producto actualiza qty en vez de duplicar la fila.
    """
    cart                        =   models.ForeignKey(Cart, on_delete = models.CASCADE, related_name = 'items', db_index = False)
    product                     =   models.ForeignKey(Product, on_delete = models.CASCADE, related_name = 'cart_items', db_index = False)
    qty                         =   models.PositiveIntegerField(default = 1, verbose_name = 'Cantidad')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'cart'
        verbose_name            =   'Item de carrito'
        verbose_name_plural     =   'Items de carrito'
        ordering                =   ['created_at', 'id']
        constraints             =   [
            models.UniqueConstraint(fields = ['cart', 'product'], name = 'uq_cartitem_cart_product'),
            models.CheckConstraint(condition = models.Q(qty__gte = 1, qty__lte = 100), name = 'ck_cartitem_qty_range'),
        ]
        indexes                 =   [
            models.Index(fields = ['cart'], name = 'idx_cartitem_cart'),
        ]
    def __str__(self):
        return f'{self.qty}x {self.product_id} (cart {self.cart_id})'
