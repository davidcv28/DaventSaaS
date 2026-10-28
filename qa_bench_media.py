"""Media de QA para bench-store: logo + portada + carrusel en R2.
Idempotente: solo sube lo que falta (logo_key/cover_key vacíos, carrusel < 2).
Correr: venv/Scripts/python.exe qa_bench_media.py
"""
import os, io
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageDraw
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services.storage import (
    upload_logo, upload_cover, upload_carousel_image
)

store = Store.objects.get(slug='bench-store')
c = store.customization


def gradient(w, h, a, b, label=''):
    img = Image.new('RGB', (w, h), a)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        col = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
        d.line([(0, y), (w, y)], fill=col)
    if label:
        d.text((w // 2, h // 2), label, fill=(255, 255, 255), anchor='mm')
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=85)
    buf.seek(0)
    return buf.read()


def upload_file(name, data):
    return SimpleUploadedFile(name, data, content_type='image/jpeg')


done = []
if not c.logo_key:
    logo = gradient(480, 480, (49, 62, 110), (150, 110, 190), 'B')
    upload_logo(c, upload_file('qa-logo.jpg', logo))
    done.append('logo')
if not c.cover_key:
    cover = gradient(1600, 700, (30, 42, 80), (190, 140, 80))
    upload_cover(c, upload_file('qa-cover.jpg', cover))
    done.append('cover')
if store.carousel_images.count() < 2:
    for i, (a, b) in enumerate([((38, 90, 75), (80, 160, 130)), ((110, 49, 80), (186, 96, 140))]):
        data = gradient(1200, 800, a, b, f'Slide {i + 1}')
        upload_carousel_image(store, upload_file(f'qa-slide{i}.jpg', data))
    done.append('carousel')
print('subido:', ', '.join(done) or 'nada (ya estaba)')
