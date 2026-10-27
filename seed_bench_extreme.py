"""Datos extremos (plausibles) para break-ui sobre bench-store.
Casos: nombre al tope (120), sin imagen, precio máximo (12 dígitos),
nombre mínimo, descripción al tope (600), oferta con tachado y precio $0.
Idempotente por nombre. Correr: venv/Scripts/python.exe seed_bench_extreme.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
django.setup()

from decimal import Decimal
from StoreApp.domains.stores.models import Store
from StoreApp.domains.catalog.models.models import Category, Brand, Product

store = Store.objects.get(slug='bench-store')
cat = Category.objects.filter(store=store).first()
brand = Brand.objects.filter(store=store).first()
long_brand, _ = Brand.objects.get_or_create(
    store=store, name='Distribuidora Internacional de Artículos para el Hogar')

DESC600 = (
    'Producto importado con certificación IRAM. Incluye manual en español, '
    'garantía oficial del fabricante de 12 meses extensible a 24, soporte '
    'técnico por WhatsApp de lunes a sábados y repuestos disponibles en el '
    'país. Compatible con instalaciones domiciliarias estándar. El empaque '
    'es reforzado para envíos al interior. Consultar disponibilidad de '
    'color antes de comprar; las fotos son ilustrativas y pueden variar '
    'según el lote de fabricación vigente al momento del despacho del pedido.'
)[:600]

EXTREMES = [
    dict(
        #Nombre al tope de 120 chars, real: producto + variante + edición.
        name='Juego de sábanas queen size 144 hilos 100% algodón egipcio color blanco hotelero premium edición limitada',
        price=Decimal('89999.00'), offer_price=Decimal('59999.00'),
        description=DESC600, brand=long_brand,
    ),
    dict(
        #Sin imagen + precio al tope de max_digits=12 (10 enteros + 2 decimales).
        name='Lote industrial de insumos para restaurante (pack por bulto cerrado, a convenir)',
        price=Decimal('9999999999.99'), offer_price=None, brand=long_brand,
    ),
    dict(
        #Nombre mínimo plausible.
        name='X',
        price=Decimal('1500.00'), offer_price=Decimal('900.00'), brand=brand,
    ),
    dict(
        #Token largo irrompible plausible (código de modelo en el nombre).
        name='Heladera cíclica modelo SSIBIR3100XWINVERTERNF no frost 310 litros',
        price=Decimal('2450000.00'), offer_price=None, brand=long_brand,
    ),
    dict(
        #Precio $0 (dato faltante real: el dueño no cargó precio).
        name='Consultar precio en tienda',
        price=Decimal('0'), offer_price=None, brand=None,
    ),
]

created = 0
for i, spec in enumerate(EXTREMES):
    _, was = Product.objects.get_or_create(
        store=store, name=spec['name'],
        defaults={**spec, 'category': cat, 'is_active': True})
    created += was
print(f'{created} productos extremos nuevos, {len(EXTREMES)-created} ya existían')
