"""
Vistas del carrito del comprador (e-commerce DAVENT).

Auth: `CustomerJWTAuthentication` + `IsCustomer` (track A) — el carrito
es del COMPRADOR (request.customer), nunca del usuario DAVENT dueño.
Gate de venta: `services.cart.sellable_store` exige tienda publicada,
no bloqueada y `orders_enabled` (ecommerce + fiscal completo) → 404 si
no, igual que cualquier endpoint público de pedido.

Endpoints:
- GET/POST /api/cart/<slug>/                 → get-or-create + payload con precios
- POST/PATCH/DELETE /api/cart/<slug>/items/   → alta upsert / bulk upsert / vaciar
- PATCH/DELETE /api/cart/<slug>/items/<id>/  → qty / borrar línea
"""
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.cart.models import Cart
from StoreApp.domains.cart.serializers import (
    CartItemInputSerializer,
    CartItemPatchSerializer,
)
from StoreApp.domains.cart.services.cart import (
    add_item,
    cart_payload,
    clear_cart,
    customer_of,
    get_or_create_cart,
    purchasable_product,
    remove_item,
    sellable_store,
    update_item,
)
from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)


class _CartBaseView(APIView):
    """Base: auth de comprador + tienda vendible del slug."""
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    def _context(self, request, slug):
        """(store, customer); store=None → la tienda no vende → 404."""
        store       =   sellable_store(slug)
        customer    =   customer_of(request)
        if store is None or customer is None:
            return None, customer
        return store, customer
    def _get_cart(self, store, customer):
        """Carrito existente o None — para GET (nunca crea fila en lectura)."""
        return Cart.objects.filter(customer = customer, store = store).first()
    def _require_cart(self, request, slug):
        """(store, customer, cart) o Http404 — para las rutas de items.
        get-or-create: el primer POST a /items/ no necesita un roundtrip
        previo a /cart/ (el carrito vacío es inofensivo y único por
        customer+store)."""
        store, customer  =   self._context(request, slug)
        if store is None:
            raise Http404
        return store, customer, get_or_create_cart(customer, store)
    def _payload(self, cart, customer):
        return Response(cart_payload(cart, customer), status = status.HTTP_200_OK)
    @staticmethod
    def _empty_payload(store):
        return {
            'store'                     :   store.slug,
            'items'                     :   [],
            'item_count'                :   0,
            'items_total'               :   '0.00',
            'member_discount_percent'   :   0,
        }


class CartView(_CartBaseView):
    """
    GET  → carrito de la tienda (vacío si no existe — no se crea en GET).
    POST → get-or-create; si el body trae {product_id, qty} además suma
           la línea (atajo del front sin pegarle a /items/).
    """
    def get(self, request, slug):
        store, customer  =   self._context(request, slug)
        if store is None:
            raise Http404
        cart    =   self._get_cart(store, customer)
        if cart is None:
            return Response(self._empty_payload(store), status = status.HTTP_200_OK)
        return self._payload(cart, customer)
    def post(self, request, slug):
        store, customer  =   self._context(request, slug)
        if store is None:
            raise Http404
        cart    =   get_or_create_cart(customer, store)
        #Body opcional: {product_id, qty} → upsert de la línea en el mismo
        #request (el front del drawer no necesita un segundo roundtrip).
        data    =   request.data if isinstance(request.data, dict) else {}
        if data.get('product_id') is not None:
            serializer  =   CartItemInputSerializer(data = data)
            serializer.is_valid(raise_exception = True)
            product     =   purchasable_product(store, serializer.validated_data['product_id'], customer)
            add_item(cart, product, serializer.validated_data['qty'])
        return self._payload(cart, customer)


class CartItemsView(_CartBaseView):
    """
    POST   → {product_id, qty} upsert de línea.
    PATCH  → {product_id, qty} upsert (alias idempotente del POST).
    DELETE → vacía el carrito.
    """
    def post(self, request, slug):
        store, customer, cart  =   self._require_cart(request, slug)
        serializer  =   CartItemInputSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        product     =   purchasable_product(store, serializer.validated_data['product_id'], customer)
        add_item(cart, product, serializer.validated_data['qty'])
        return self._payload(cart, customer)
    def patch(self, request, slug):
        #Mismo contrato que POST: upsert por product_id (el id de línea es
        #un detalle interno que el front no necesita para editar).
        return self.post(request, slug)
    def delete(self, request, slug):
        _store, _customer, cart    =   self._require_cart(request, slug)
        clear_cart(cart)
        return self._payload(cart, _customer)


class CartItemView(_CartBaseView):
    """PATCH {qty} / DELETE de UNA línea por id."""
    def patch(self, request, slug, item_id):
        _store, _customer, cart    =   self._require_cart(request, slug)
        serializer  =   CartItemPatchSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        update_item(cart, item_id, serializer.validated_data['qty'])
        return self._payload(cart, _customer)
    def delete(self, request, slug, item_id):
        _store, _customer, cart    =   self._require_cart(request, slug)
        remove_item(cart, item_id)
        return self._payload(cart, _customer)
