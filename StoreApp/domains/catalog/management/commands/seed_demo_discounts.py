from decimal import Decimal, ROUND_HALF_UP

from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from StoreApp.domains.catalog.models import Brand, Category, Discount, Product, SpecialOfferCampaign
from StoreApp.domains.stores.models import Store

"""

Seed de descuentos de demostración para probar la tarjeta del catálogo
(precio tachado, badge de descuento, filtro de eventos). Crea ≥4
Discount vigentes HOY con name prefijado 'DEMO ·' — el prefijo permite
borrarlos con --clear sin tocar los descuentos reales de la tienda.

También varía offer_price manual (~20% de los productos) y stock
(0 / 3 / NULL en ciclo) para cubrir las combinaciones de la tarjeta:
≥1 producto con todo (oferta manual + descuento programado + stock) y
≥1 solo con descuento programado.

Idempotente: los descuentos se hacen update_or_create por (store, name)
y las mutaciones de producto son determinísticas (orden por id).

Uso:
    manage.py seed_demo_discounts --store <slug> --dry-run
    manage.py seed_demo_discounts --store <slug>
    manage.py seed_demo_discounts --store <slug> --clear

"""
#=========================================
# CONFIG
#=========================================
DEMO_PREFIX       =   'DEMO ·'
DISCOUNT_SPECS    =   [
    # (sufijo del nombre, percent, scope)
    ('15% en todo el catálogo',        15, Discount.Scope.ALL),
    ('25% en una categoría',           25, Discount.Scope.CATEGORY),
    ('30% en una marca',               30, Discount.Scope.BRAND),
    ('40% en productos elegidos',      40, Discount.Scope.PRODUCTS),
]
OFFER_RATIO       =   Decimal('0.20')     # ~20% de los productos sin oferta
STOCK_PATTERN     =   (3, 0, None)        # stock variado: unidades / agotado / sin límite
DISCOUNT_DAYS     =   15                  # ends_at = hoy + 15 días
#=========================================
# HELPERS
#=========================================
def _money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding = ROUND_HALF_UP)
def _running_campaign(moment):
    """Primera SpecialOfferCampaign vigente hoy (is_running evalúa la ventana anual)."""
    for campaign in SpecialOfferCampaign.objects.filter(is_active = True):
        if campaign.is_running(moment):
            return campaign
    return None
def _discount_plan(store, products):
    """
    Specs concretos de los 4 descuentos: resuelve categoría/marca/productos
    objetivo con datos reales de la tienda. Devuelve (specs, warnings).
    """
    warnings =   []
    category    =   (
        Category.objects.filter(store = store, products__is_active = True)
        .distinct().order_by('position', 'id').first()
    )
    brand       =   (
        Brand.objects.filter(store = store, products__is_active = True)
        .distinct().order_by('position', 'id').first()
    )
    specs       =   []
    for suffix, percent, scope in DISCOUNT_SPECS:
        spec    =   {'name': f'{DEMO_PREFIX} {suffix}', 'percent': percent, 'scope': scope,
                     'category': None, 'brand': None, 'products': []}
        if scope == Discount.Scope.CATEGORY:
            spec['category']   =   category
            if category is None:
                warnings.append('Sin categoría con productos: el descuento CATEGORY queda sin alcance efectivo.')
        elif scope == Discount.Scope.BRAND:
            spec['brand']      =   brand
            if brand is None:
                warnings.append('Sin marca con productos: el descuento BRAND queda sin alcance efectivo.')
        elif scope == Discount.Scope.PRODUCTS:
            spec['products']   =   list(products[:5])
            if len(spec['products']) < 3:
                warnings.append(f'Solo {len(spec["products"])} producto(s) activo(s): el alcance PRODUCTS no llega a 3-5.')
        specs.append(spec)
    return specs, warnings
def _product_plan(products):
    """
    Mutaciones determinísticas de producto: offer_price manual al ~20%
    (mínimo 1, dejando siempre ≥1 producto sin oferta manual si hay >1)
    y stock en ciclo 3/0/NULL. Devuelve (cambios, warnings).
    """
    warnings     =   []
    changes      =   []
    n            =   len(products)
    if not n:
        warnings.append('La tienda no tiene productos activos: no hay nada que variar.')
        return changes, warnings
    n_offer      =   max(1, int(round(n * float(OFFER_RATIO)))) if n > 1 else 0
    n_offer      =   min(n_offer, n - 1) if n > 1 else 0
    for index, product in enumerate(products):
        change      =   {'product': product, 'offer_price': None, 'stock': None,
                         'stock_changed': False, 'offer_changed': False}
        if index < n_offer and product.offer_price is None and product.price and product.price > 0:
            change['offer_price']      =   _money(product.price * (Decimal(1) - OFFER_RATIO))
            change['offer_changed']   =   True
        stock                       =   STOCK_PATTERN[index % len(STOCK_PATTERN)]
        if product.stock != stock:
            change['stock']           =   stock
            change['stock_changed']   =   True
        changes.append(change)
    return changes, warnings
#=========================================
# COMMAND
#=========================================
class Command(BaseCommand):
    help    =   'Crea/borras descuentos DEMO · vigentes para probar la tarjeta del catálogo.'

    def add_arguments(self, parser):
        parser.add_argument('--store', required = True, help = 'Slug de la tienda')
        parser.add_argument('--dry-run', action = 'store_true', help = 'Muestra la tabla sin escribir')
        parser.add_argument('--clear', action = 'store_true', help = 'Borra solo los descuentos DEMO · de la tienda')

    def handle(self, *args, **options):
        store       =   Store.objects.filter(slug = options['store']).first()
        if store is None:
            raise CommandError(f'No existe la tienda "{options["store"]}".')
        demo_qs     =   Discount.objects.filter(store = store, name__startswith = DEMO_PREFIX)
        if options['clear']:
            count   =   demo_qs.count()
            if options['dry_run']:
                self.stdout.write(f'[dry-run] Se borrarían {count} descuento(s) "{DEMO_PREFIX}" de {store.slug}.')
                return
            demo_qs.delete()
            self.stdout.write(self.style.SUCCESS(f'{store.slug}: {count} descuento(s) "{DEMO_PREFIX}" borrados.'))
            return
        now         =   timezone.now()
        starts_at   =   now - timezone.timedelta(days = 1)
        ends_at     =   now + timezone.timedelta(days = DISCOUNT_DAYS)
        products    =   list(Product.objects.filter(store = store, is_active = True).order_by('id'))
        specs, warnings  =   _discount_plan(store, products)
        changes, product_warnings  =   _product_plan(products)
        warnings.extend(product_warnings)
        campaign    =   _running_campaign(now)
        # UNO de los descuentos se etiqueta con la campaña vigente (si hay).
        campaign_spec   =   specs[0] if campaign is not None else None
        #=========================================
        # TABLA (dry-run y apply comparten la misma salida)
        #=========================================
        self.stdout.write(f'Tienda: {store.slug} — ventana {starts_at:%Y-%m-%d} -> {ends_at:%Y-%m-%d}')
        if campaign is not None:
            self.stdout.write(f'Campaña vigente hoy: {campaign.slug} ({campaign.name}) -> se vincula a "{campaign_spec["name"]}".')
        else:
            self.stdout.write(self.style.WARNING('Sin SpecialOfferCampaign vigente hoy: los descuentos quedan sin campaña.'))
        for spec in specs:
            target  =   spec['category'].name if spec['category'] else spec['brand'].name if spec['brand'] else \
                        ', '.join(p.name for p in spec['products']) or '—'
            tag     =   f'  [campaña: {campaign.slug}]' if spec is campaign_spec else ''
            self.stdout.write(
                f'  {spec["name"]:<38} -{spec["percent"]:>2}%  scope={spec["scope"]:<8} '
                f'alcance={target}{tag}'
            )
        for change in changes:
            p           =   change['product']
            parts       =   []
            if change['offer_changed']:
                parts.append(f'offer_price {p.offer_price} -> {change["offer_price"]}')
            if change['stock_changed']:
                parts.append(f'stock {p.stock} -> {change["stock"]}')
            if parts:
                self.stdout.write(f'  producto #{p.id} {p.name[:40]:<40} ' + ' | '.join(parts))
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f'  ! {warning}'))
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('[dry-run] No se escribió nada.'))
            return
        #=========================================
        # APPLY
        #=========================================
        with transaction.atomic():
            for spec in specs:
                discount, created   =   Discount.objects.update_or_create(
                    store       =   store,
                    name        =   spec['name'],
                    defaults    =   {
                        'percent'    :   spec['percent'],
                        'scope'      :   spec['scope'],
                        'category'   :   spec['category'],
                        'brand'      :   spec['brand'],
                        'starts_at'  :   starts_at,
                        'ends_at'    :   ends_at,
                        'is_active'  :   True,
                        'campaign'   :   campaign if spec is campaign_spec else None,
                    },
                )
                if spec['scope'] == Discount.Scope.PRODUCTS:
                    discount.products.set(spec['products'])
                elif spec['scope'] != Discount.Scope.ALL:
                    #scope ALL no usa category/brand/products: limpiar residuos
                    #de una corrida anterior con otro alcance bajo el mismo name.
                    discount.products.clear()
                self.stdout.write(f'  {"creado" if created else "actualizado"}: {discount.name}')
            for change in changes:
                p               =   change['product']
                fields          =   []
                if change['offer_changed']:
                    p.offer_price   =   change['offer_price']
                    fields.append('offer_price')
                if change['stock_changed']:
                    p.stock         =   change['stock']
                    fields.append('stock')
                if fields:
                    p.save(update_fields = fields)
        self.stdout.write(self.style.SUCCESS(
            f'{store.slug}: {len(specs)} descuento(s) DEMO · vigentes, '
            f'{sum(1 for c in changes if c["offer_changed"])} oferta(s) manual(es), '
            f'{sum(1 for c in changes if c["stock_changed"])} stock(s) vari(normal)es.'
        ))
