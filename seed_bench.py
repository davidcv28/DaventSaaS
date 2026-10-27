"""Seed de QA para bench-store: catálogo rico para probar el rediseño de filtros.
Correr: venv/Scripts/python.exe seed_bench.py  (idempotente: borra y recrea)
"""
import os, io, random
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from PIL import Image, ImageDraw
from StoreApp.domains.stores.models import Store
from StoreApp.domains.catalog.models.models import Category, Brand, Product, Discount
from StoreApp.domains.stores.services.storage import upload_product_image

random.seed(7)
store = Store.objects.get(slug='bench-store')

# Limpieza idempotente
Product.objects.filter(store=store).delete()
Category.objects.filter(store=store).delete()
Brand.objects.filter(store=store).delete()
Discount.objects.filter(store=store).delete()

PALETTES = [
    ((49, 62, 110), (96, 116, 186)), ((110, 49, 80), (186, 96, 140)),
    ((38, 90, 75), (80, 160, 130)), ((120, 82, 40), (190, 140, 80)),
    ((60, 60, 66), (120, 122, 132)), ((84, 52, 110), (150, 110, 190)),
]

def make_image(name, i):
    a, b = PALETTES[i % len(PALETTES)]
    img = Image.new('RGB', (900, 1150), a)
    d = ImageDraw.Draw(img)
    for y in range(1150):
        t = y / 1150
        c = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
        d.line([(0, y), (900, y)], fill=c)
    # círculo decorativo + inicial
    d.ellipse([300, 400, 600, 700], outline=(255, 255, 255), width=10)
    initial = name.strip()[:1].upper()
    d.text((435, 505), initial, fill=(255, 255, 255), anchor='mm')
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=82)
    buf.seek(0)
    return SimpleUploadedFile(f'{i}.jpg', buf.read(), content_type='image/jpeg')

CATS = [
    ('Indumentaria', ['Talle', 'Color', 'Material']),
    ('Calzado', ['Talle', 'Color', 'Material']),
    ('Celulares', ['Marca', 'Modelo', 'Almacenamiento', 'Color']),
    ('Hogar', ['Material', 'Color']),
    ('Accesorios', ['Color']),
    ('Belleza', ['Color']),
]
BRANDS = ['Urbania', 'Nordika', 'Pampa', 'Aluvia', 'Distrito', 'Kero', 'Montana', 'Orbe']

cats = {}
for i, (name, schema) in enumerate(CATS):
    cats[name] = Category.objects.create(store=store, name=name, feature_schema=schema, position=i)
brands = {n: Brand.objects.create(store=store, name=n, position=i) for i, n in enumerate(BRANDS)}

TALLES_ROPA = 'XS, S, M, L, XL, XXL'.split(', ')
TALLES_CALZ = [str(n) for n in range(35, 46)]
COLORES = ['Rojo', 'Azul', 'Verde', 'Negro', 'Blanco', 'Rosa', 'Amarillo', 'Violeta', 'Gris', 'Marrón']
MATERIALES = ['Algodón', 'Cuero', 'Lona', 'Sintético', 'Madera', 'Metal', 'Vidrio', 'Tela', 'Lino']

PRODUCTS = [
    # (nombre, cat, brand, price, offer, features, img)
    ('Remera oversize estampada edición limitada con gráfico de autor', 'Indumentaria', 'Urbania', 32999, None,
        {'Talle': 'S, M, L, XL', 'Color': 'Negro, Blanco', 'Material': 'Algodón'}, 1),
    ('Remera básica lisa pack x2', 'Indumentaria', 'Pampa', 24999, 18999,
        {'Talle': 'XS, S, M, L, XL, XXL', 'Color': 'Blanco, Negro, Gris', 'Material': 'Algodón'}, 1),
    ('Jean mom fit tiro alto', 'Indumentaria', 'Distrito', 58999, None,
        {'Talle': '36, 38, 40, 42, 44', 'Color': 'Azul', 'Material': 'Algodón'}, 1),
    ('Campera de jean con corderoy', 'Indumentaria', 'Montana', 89999, 71999,
        {'Talle': 'S, M, L', 'Color': 'Azul, Negro', 'Material': 'Algodón'}, 1),
    ('Vestido midi estampado floral con volados y espalda abierta', 'Indumentaria', 'Aluvia', 64999, None,
        {'Talle': 'XS, S, M', 'Color': 'Rosa, Amarillo, Verde', 'Material': 'Lino'}, 1),
    ('Buzo canguro fleece', 'Indumentaria', 'Urbania', 54999, 43999,
        {'Talle': 'S, M, L, XL, XXL', 'Color': 'Negro, Gris, Violeta', 'Material': 'Algodón'}, 1),
    ('Camisa lino manga larga', 'Indumentaria', 'Nordika', 62999, None,
        {'Talle': 'S, M, L, XL', 'Color': 'Blanco, Azul', 'Material': 'Lino'}, 1),
    ('Pollera plisada midi', 'Indumentaria', 'Aluvia', 45999, None,
        {'Talle': 'XS, S, M, L', 'Color': 'Negro, Marrón', 'Material': 'Tela'}, 1),
    ('Zapatillas runner mesh', 'Calzado', 'Kero', 94999, 75999,
        {'Talle': '38, 39, 40, 41, 42, 43, 44', 'Color': 'Negro, Blanco, Rojo', 'Material': 'Sintético'}, 1),
    ('Botas de cuero con hebilla lateral y suela de goma antideslizante', 'Calzado', 'Montana', 129999, None,
        {'Talle': '35, 36, 37, 38, 39, 40', 'Color': 'Marrón, Negro', 'Material': 'Cuero'}, 1),
    ('Ojotas de goma premium', 'Calzado', 'Pampa', 18999, 14999,
        {'Talle': '35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45', 'Color': 'Negro, Azul, Verde', 'Material': 'Sintético'}, 1),
    ('Mocasines urbanos', 'Calzado', 'Orbe', 79999, None,
        {'Talle': '38, 39, 40, 41, 42', 'Color': 'Negro, Marrón', 'Material': 'Cuero'}, 1),
    ('Sandalias plataforma', 'Calzado', 'Aluvia', 55999, 41999,
        {'Talle': '35, 36, 37, 38, 39', 'Color': 'Blanco, Rosa', 'Material': 'Sintético'}, 1),
    ('Celular X200 5G 256GB', 'Celulares', 'Distrito', 459999, 429999,
        {'Marca': 'Samsung', 'Modelo': 'X200', 'Almacenamiento': '256GB', 'Color': 'Negro, Azul'}, 1),
    ('Celular Lite 128GB', 'Celulares', 'Kero', 289999, None,
        {'Marca': 'Xiaomi', 'Modelo': 'Lite', 'Almacenamiento': '128GB', 'Color': 'Azul, Verde'}, 1),
    ('Celular Pro Max 512GB cámara triple 200MP edición titanio', 'Celulares', 'Distrito', 899999, None,
        {'Marca': 'Apple', 'Modelo': 'Pro Max', 'Almacenamiento': '512GB', 'Color': 'Negro, Gris'}, 1),
    ('Celular Basic 64GB', 'Celulares', 'Pampa', 149999, 129999,
        {'Marca': 'Motorola', 'Modelo': 'Basic', 'Almacenamiento': '64GB', 'Color': 'Negro'}, 1),
    ('Funda antishock transparente', 'Accesorios', 'Kero', 9999, None,
        {'Color': 'Blanco, Negro, Rosa'}, 1),
    ('Mochila urbana 20L', 'Accesorios', 'Montana', 49999, 39999,
        {'Color': 'Negro, Verde, Gris'}, 1),
    ('Riñonera deportiva', 'Accesorios', 'Kero', 19999, None,
        {'Color': 'Negro, Rojo, Amarillo'}, 1),
    ('Cartera de cuero genuino con bolsillos internos y cierre magnético', 'Accesorios', 'Orbe', 84999, None,
        {'Color': 'Marrón, Negro'}, 1),
    ('Lámpara de pie nórdica', 'Hogar', 'Nordika', 74999, 59999,
        {'Material': 'Madera, Metal', 'Color': 'Blanco, Negro'}, 1),
    ('Espejo redondo 60cm', 'Hogar', 'Orbe', 45999, None,
        {'Material': 'Vidrio, Madera', 'Color': 'Marrón'}, 1),
    ('Set de vasos x6', 'Hogar', 'Nordika', 22999, 17999,
        {'Material': 'Vidrio', 'Color': 'Blanco'}, 1),
    ('Manta tejida a mano', 'Hogar', 'Pampa', 38999, None,
        {'Material': 'Lana, Algodón', 'Color': 'Gris, Blanco, Rosa'}, 1),
    ('Perfume floral 100ml', 'Belleza', 'Aluvia', 67999, 52999,
        {'Color': 'Rosa'}, 1),
    ('Set de skincare completo', 'Belleza', 'Nordika', 89999, None,
        {'Color': 'Blanco, Verde'}, 1),
    ('Producto sin foto ni categoría', None, 'Pampa', 15999, None, {}, 0),
    ('Producto sin foto con categoría', 'Accesorios', 'Kero', 11999, 8999, {'Color': 'Negro'}, 0),
    ('Gorra trucker regulable', 'Accesorios', 'Urbania', 16999, None, {'Color': 'Negro, Rojo, Azul, Verde, Amarillo, Rosa, Violeta, Gris'}, 1),
]

created = []
for i, (name, cat, brand, price, offer, feats, has_img) in enumerate(PRODUCTS):
    p = Product.objects.create(
        store=store, name=name, price=price, offer_price=offer,
        category=cats.get(cat) if cat else None,
        brand=brands.get(brand),
        features=feats, is_active=True,
        description='Descripción de prueba para QA visual del catálogo público.',
    )
    # desfasar created_at para que "novedades" tenga mezcla
    Product.objects.filter(pk=p.pk).update(created_at=timezone.now() - timedelta(days=i * 3))
    if has_img:
        try:
            upload_product_image(p, make_image(name, i))
        except Exception as e:
            print('img fail', p.name, e)
    created.append(p)

# Descuento vigente en Calzado (banner de promo)
Discount.objects.create(
    store=store, name='Semana del calzado', percent=15, scope='category',
    category=cats['Calzado'], starts_at=timezone.now() - timedelta(days=1), ends_at=None, is_active=True,
)

# Customization sane defaults para QA (template se rota a mano)
from StoreApp.domains.stores.models import StoreCustomization
c, _ = StoreCustomization.objects.get_or_create(store=store)
c.show_catalog = True
c.show_reviews = True
c.display_name = 'Bench Store'
c.save()

print(f'OK: {len(created)} productos, {len(cats)} categorías, {len(brands)} marcas en bench-store')
