"""
Vence los pedidos PENDING_PAYMENT cuyo `expires_at` ya pasó:
status → EXPIRED + OrderEvent 'expired' (append-only).

Diseño batch e IDEMPOTENTE para correr por cron (cada X minutos):

- El queryset trae solo candidatos (status + expires_at < now) y cada
  pedido se re-valida y muta dentro de su propio `transaction.atomic`
  con `select_for_update` — dos corridas solapadas se serializan y la
  segunda ve el pedido ya EXPIRED (no-op, sin evento duplicado).
- No toca stock: los pedidos pendientes nunca lo reservaron (el
  descuento ocurre en mark_order_paid al confirmar el pago).
- `--dry-run` lista los candidatos sin mutar nada (para monitoreo).

Uso:  python manage.py expire_orders [--dry-run] [--batch 200]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from StoreApp.domains.orders.models import Order
from StoreApp.domains.orders.services.events import append_event
from StoreApp.domains.orders.services.proofs import release_proof
from StoreApp.domains.stores.models import Store


class Command(BaseCommand):
    help = 'Vence pedidos pendientes de pago cuyo expires_at ya pasó (batch idempotente).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action = 'store_true', help = 'Lista candidatos sin mutar nada.')
        parser.add_argument('--batch', type = int, default = 200, help = 'Máximo de pedidos por corrida.')

    def handle(self, *args, **options):
        dry_run     =   options['dry_run']
        batch       =   max(1, min(int(options['batch']), 5000))
        now         =   timezone.now()
        candidates  =   list(
            Order.objects
            .filter(status = Order.Status.PENDING_PAYMENT, expires_at__lt = now)
            .order_by('expires_at')[:batch]
        )
        if dry_run:
            self.stdout.write(f'Candidatos a vencer: {len(candidates)} (dry-run, sin cambios).')
            for order in candidates:
                self.stdout.write(f'  {order.code} store={order.store_id} vence={order.expires_at:%Y-%m-%d %H:%M}')
            return
        expired =   0
        for order in candidates:
            with transaction.atomic():
                #Store antes que Order (mismo orden de locks que el
                #upload de comprobantes): release_proof ajusta la cuota.
                locked_store    =   Store.objects.select_for_update().get(pk = order.store_id)
                locked  =   (Order.objects
                    .select_for_update()
                    .filter(pk = order.pk, status = Order.Status.PENDING_PAYMENT)
                    .first())
                if locked is None:
                    continue    # otro worker ya lo venció (o se pagó): idempotente
                locked.status   =   Order.Status.EXPIRED
                locked.save(update_fields = ['status', 'updated_at'])
                append_event(locked, 'expired', actor = 'system', status_from = Order.Status.PENDING_PAYMENT, status_to = Order.Status.EXPIRED)
                #El pedido vencido ya no admite pago: su comprobante
                #queda sin función — se libera fila + objeto + cuota.
                release_proof(locked, locked_store = locked_store)
            expired +=  1
        self.stdout.write(self.style.SUCCESS(f'Pedidos vencidos: {expired} (candidatos: {len(candidates)}).'))
