from rest_framework import serializers

from StoreApp.domains.cart.services.cart import MAX_QTY

"""

Serializers del dominio cart — solo validan FORMA (ids y cantidades);
pertenencia a la tienda, estado activo, exclusividad y stock los
resuelve services.cart contra la base (nunca confiar en el payload).

"""
#=========================================
# CART ITEM INPUT (POST/PATCH /items/)
#=========================================
class CartItemInputSerializer(serializers.Serializer):
    """Alta/upsert de una línea: {product_id, qty}."""
    product_id              =   serializers.IntegerField(min_value = 1)
    qty                     =   serializers.IntegerField(min_value = 1, max_value = MAX_QTY)
class CartItemPatchSerializer(serializers.Serializer):
    """Cambio de cantidad de una línea existente: {qty}."""
    qty                     =   serializers.IntegerField(min_value = 1, max_value = MAX_QTY)
