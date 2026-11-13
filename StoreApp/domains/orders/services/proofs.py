"""
Ciclo de vida del comprobante de pago (PaymentProof).

- Subida: views/public.py (WebP normalizado → R2 privado → cuota del
  plan vía storage_used_bytes).
- Liberación: pedidos que cierran SIN pago (EXPIRED por el cron,
  CANCELLED por el dueño) — el comprobante queda sin función (el pedido
  ya no admite acreditación) y sus bytes vuelven a la cuota de la
  tienda. Pedidos pagos/reembolsados CONSERVAN el comprobante: es la
  evidencia de la operación.

`release_proof` debe llamarse DENTRO del atomic que ya bloqueó el
pedido y la tienda, en ese orden (Store → Order, igual que el upload
de comprobantes y checkout — nunca al revés, para no deadlockear).
"""
import logging

from StoreApp.domains.orders.models import PaymentProof
from StoreApp.domains.stores.services.storage import _consume_quota, _delete_object

logger  =   logging.getLogger(__name__)


def release_proof(order, *, locked_store):
    """
    Borra el comprobante de un pedido cerrado sin pago: fila + objeto
    R2 (best-effort) + devolución de bytes a storage_used_bytes.
    `locked_store` es la fila de Store ya bloqueada con select_for_update
    en el mismo atomic. Devuelve el PaymentProof eliminado o None.
    """
    proof   =   PaymentProof.objects.filter(order = order).first()
    if proof is None:
        return None
    key, size    =   proof.image_key, proof.size
    proof.delete()
    if size:
        _consume_quota(locked_store, max(0, locked_store.storage_used_bytes - size))
    _delete_object(key)
    logger.info('Comprobante liberado: order=%s store=%s bytes=%s', order.pk, order.store_id, size)
    return proof
