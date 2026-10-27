"""Contenido rico para bench-store: bloques de marketing + servicios.
Idempotente: solo rellena campos vacíos (no pisa datos existentes) y los
StoreService se crean por get_or_create(store, name).

Correr: venv/Scripts/python.exe seed_bench_content.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
django.setup()

from StoreApp.domains.stores.models import Store
from StoreApp.domains.services.models.models import StoreService

store = Store.objects.get(slug='bench-store')
c = store.customization

filled = []
def fill(field, value):
    if not getattr(c, field):
        setattr(c, field, value)
        filled.append(field)

fill('headline', 'Todo lo que tu casa necesita, en un solo lugar')
fill('description', 'Somos una tienda de barrio con envíos a todo el país.')
fill('about_title', 'Quiénes somos')
fill('about_text', 'Desde 2012 acercamos productos de calidad con atención personalizada. Creemos en el trato directo y en cumplir lo que prometemos.')
fill('about_years', 12)
fill('about_mission', 'Producto honesto, precio claro y envío a tiempo.')
fill('about_specialties', 'Importación propia, garantía escrita y cambio sin vueltas.')
fill('stats', [
    {'value': '12', 'label': 'años de trayectoria'},
    {'value': '4.9', 'label': 'valoración promedio'},
    {'value': '1200', 'label': 'pedidos entregados'},
    {'value': '48h', 'label': 'despacho promedio'},
])
fill('testimonials', [
    {'name': 'María G.', 'detail': 'Cliente hace 3 años', 'text': 'Compré varias veces y siempre llegó todo perfecto. Atención de diez.'},
    {'name': 'Julián R.', 'detail': 'Compra online', 'text': 'El envío fue rapidísimo y el producto mejor de lo esperado.'},
    {'name': 'Carla P.', 'detail': 'Cliente frecuente', 'text': 'Cuando tuve un problema lo resolvieron el mismo día. Muy recomendable.'},
])
fill('faqs', [
    {'q': '¿Hacen envíos?', 'a': 'Sí, a todo el país por correo. Despachamos en 24/48 hs hábiles.'},
    {'q': '¿Qué medios de pago aceptan?', 'a': 'Mercado Pago, transferencia y efectivo en el local.'},
    {'q': '¿Tienen garantía los productos?', 'a': 'Todos los productos tienen 6 meses de garantía escrita.'},
    {'q': '¿Puedo cambiar un producto?', 'a': 'Sí, dentro de los 30 días con el empaque original.'},
])
fill('hours', [
    {'label': 'Lunes a viernes', 'value': '9 a 18 hs'},
    {'label': 'Sábados', 'value': '9 a 13 hs'},
    {'label': 'Domingos', 'value': 'Cerrado'},
])
fill('benefits', [
    {'icon': 'shield-check', 'title': 'Garantía escrita', 'text': '6 meses en todos los productos.'},
    {'icon': 'truck', 'title': 'Envío rápido', 'text': 'Despacho en 24/48 hs a todo el país.'},
    {'icon': 'package', 'title': 'Cambio fácil', 'text': '30 días para cambios sin costo.'},
    {'icon': 'check', 'title': 'Stock real', 'text': 'Lo que ves publicado está disponible.'},
])
fill('timeline', [
    {'label': '2012', 'text': 'Abrimos el local del barrio con 20 productos.'},
    {'label': '2016', 'text': 'Llegamos a 1000 clientes y sumamos envíos.'},
    {'label': '2021', 'text': 'Lanzamos la tienda online.'},
    {'label': 'Hoy', 'text': 'Más de 300 productos y envíos a todo el país.'},
])
fill('team', [
    {'name': 'Andrea', 'role': 'Fundadora'},
    {'name': 'Marcos', 'role': 'Compras'},
    {'name': 'Lucía', 'role': 'Atención al cliente'},
])
fill('announcements', [
    {'icon': 'truck', 'text': 'Envío gratis en compras desde $50.000'},
    {'icon': 'shield-check', 'text': 'Garantía escrita de 6 meses en todo'},
])
fill('service_steps', [
    {'icon': 'check', 'title': 'Reservá', 'text': 'Elegí el servicio y escribinos por WhatsApp.'},
    {'icon': 'package', 'title': 'Coordinamos', 'text': 'Confirmamos día, hora y dirección.'},
    {'icon': 'wrench', 'title': 'Realizamos', 'text': 'El equipo hace el trabajo en tu domicilio.'},
    {'icon': 'shield-check', 'title': 'Garantía', 'text': 'Queda todo cubierto por 30 días.'},
])
fill('service_days', ['Lunes a viernes', 'Sábados por la mañana'])
fill('service_slots', ['9 a 13 hs', '14 a 18 hs'])
fill('cta_title', '¿Te ayudamos a elegir?')
fill('cta_text', 'Escribinos por WhatsApp y te asesoramos sin compromiso.')
fill('cta_label', 'Escribir ahora')
fill('whatsapp', '5491100000000')

if filled:
    c.save()
print('customization rellenada:', ', '.join(filled) or 'nada (ya estaba llena)')

SERVICES = [
    ('wrench', 'Instalación a domicilio', 'Dejamos todo funcionando y te explicamos el uso.', 15000, '1 a 2 hs'),
    ('truck', 'Retiro y entrega', 'Buscamos el equipo, lo reparamos y lo devolvemos.', 5000, '48 hs'),
    ('package', 'Armado de pedidos', 'Preparamos tu compra para retirar sin espera.', None, '2 hs'),
    ('shield-check', 'Service de mantenimiento', 'Revisión completa con informe y presupuesto.', 20000, '3 hs'),
]
created = 0
for i, (icon, name, desc, price, dur) in enumerate(SERVICES):
    _, was = StoreService.objects.get_or_create(
        store=store, name=name,
        defaults={'icon': icon, 'description': desc, 'price': price, 'duration': dur, 'position': i})
    created += was
print(f'servicios: {created} nuevos, {len(SERVICES)-created} ya existían')
