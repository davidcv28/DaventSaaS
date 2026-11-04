import io
import uuid
from pathlib import Path

from django.core.management import BaseCommand

from StoreApp.domains.catalog.models import SpecialOfferCampaign
from StoreApp.domains.stores.services.storage import (
    _delete_object,
    put_object,
    storage_configured,
)

"""

Carga/actualiza el calendario de ofertas especiales de Argentina
(idempotente por slug). Genera la etiqueta de cada campaña (arte propio:
banda tipográfica con la paleta de la campaña, sin logos de terceros) y
la sube a R2 bajo `system/offers/<slug>/<uuid>.webp` — no consume cuota
de ninguna tienda.

Uso:
    manage.py seed_special_offers
    manage.py seed_special_offers --force                 # regenera etiquetas
    manage.py seed_special_offers --only black-friday     # una sola campaña
    manage.py seed_special_offers --image navidad=etiqueta.png

"""
LABEL_W, LABEL_H    =   360, 96
#=========================================
# CALENDARIO AR (month/day = inicio recurrente anual, duration en días)
#=========================================
CAMPAIGNS   =   [
    {'slug': 'reyes',                'name': 'Reyes',                 'label': 'REYES',          'accent': '#7B4BD6', 'month': 1,  'day': 2,  'duration_days': 4,  'description': 'Regalos de Reyes hasta el 6 de enero.'},
    {'slug': 'san-valentin',         'name': 'San Valentín',          'label': 'VALENTÍN',       'accent': '#E23A6E', 'month': 2,  'day': 10, 'duration_days': 5,  'description': 'Semana del amor hasta el 14 de febrero.'},
    {'slug': 'vuelta-a-clases',      'name': 'Vuelta a clases',       'label': 'A CLASES',       'accent': '#1F8A5B', 'month': 2,  'day': 23, 'duration_days': 8,  'description': 'Útiles, mochilas y tecnología para arrancar el ciclo.'},
    {'slug': 'semana-santa',         'name': 'Semana Santa',          'label': 'S. SANTA',       'accent': '#8A6B3F', 'month': 3,  'day': 29, 'duration_days': 7,  'description': 'Pascuas: huevos, viajes y asados.'},
    {'slug': 'hot-sale',             'name': 'Hot Sale',              'label': 'HOT SALE',       'accent': '#E64415', 'month': 5,  'day': 12, 'duration_days': 3,  'description': 'Tres días de ofertas online.'},
    {'slug': 'dia-del-padre',        'name': 'Día del Padre',         'label': 'PAPÁ',           'accent': '#22577A', 'month': 6,  'day': 8,  'duration_days': 7,  'description': 'Semana previa al tercer domingo de junio.'},
    {'slug': 'dia-del-amigo',        'name': 'Día del Amigo',         'label': 'AMIGOS',         'accent': '#E8912D', 'month': 7,  'day': 18, 'duration_days': 3,  'description': 'Alrededor del 20 de julio.'},
    {'slug': 'dia-del-nino',         'name': 'Día del Niño',          'label': 'NIÑOS',          'accent': '#3E7CB1', 'month': 8,  'day': 10, 'duration_days': 7,  'description': 'Juguetes y regalos, tercer domingo de agosto.'},
    {'slug': 'dia-de-la-primavera',  'name': 'Día de la Primavera',   'label': 'PRIMAVERA',      'accent': '#4C956C', 'month': 9,  'day': 17, 'duration_days': 5,  'description': 'Arranca la temporada, hasta el 21 de septiembre.'},
    {'slug': 'dia-de-la-madre',      'name': 'Día de la Madre',       'label': 'MAMÁ',           'accent': '#C0526B', 'month': 10, 'day': 12, 'duration_days': 7,  'description': 'Semana previa al tercer domingo de octubre.'},
    {'slug': 'halloween',            'name': 'Halloween',             'label': 'HALLOWEEN',      'accent': '#5B2A86', 'month': 10, 'day': 28, 'duration_days': 5,  'description': 'Disfraces y dulces hasta el 1º de noviembre.'},
    {'slug': 'cybermonday',          'name': 'CyberMonday',           'label': 'CYBER',          'accent': '#0057B8', 'month': 11, 'day': 3,  'duration_days': 3,  'description': 'Tres días de ofertas online de noviembre.'},
    {'slug': 'black-friday',         'name': 'Black Friday',          'label': 'BLACK FRIDAY',   'accent': '#141414', 'month': 11, 'day': 24, 'duration_days': 4,  'description': 'Fin de semana de ofertas de fines de noviembre.'},
    {'slug': 'navidad',              'name': 'Navidad',               'label': 'NAVIDAD',        'accent': '#B3261E', 'month': 12, 'day': 18, 'duration_days': 7,  'description': 'Última semana de regalos hasta el 25.'},
    {'slug': 'ano-nuevo',            'name': 'Año Nuevo',             'label': 'AÑO NUEVO',      'accent': '#0E7C7B', 'month': 12, 'day': 28, 'duration_days': 6,  'description': 'Cruza fin de año: hasta el 2 de enero.'},
]
#=========================================
# LABEL RENDER (PIL → WebP; arte propio por campaña)
#=========================================
def _ink_for(hexcolor):
    """Tinta legible (blanco o casi negro) sobre el acento, por luminancia."""
    rgb     =   tuple(int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    lum     =   (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255
    return '#FFFFFF' if lum < 0.55 else '#111111'
def _font(size, bold = True):
    """Fuente TrueType disponible (DejaVu del venv, Arial en Windows) o default."""
    from PIL import ImageFont
    for name in ('DejaVuSans-Bold.ttf', 'arialbd.ttf', 'DejaVuSans.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()
def render_label(campaign):
    """
    Etiqueta original 360x96: banda redondeada en el acento de la campaña
    con el texto corto en tinta contrastada y una faja diagonal del color
    de fondo. Devuelve (webp_bytes, width, height).
    """
    from PIL import Image, ImageDraw
    accent      =   campaign['accent']
    ink         =   _ink_for(accent)
    scale       =   3   # supersampling: bordes suaves sin depender de fuentes
    w, h        =   LABEL_W * scale, LABEL_H * scale
    image       =   Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw        =   ImageDraw.Draw(image)
    radius      =   26 * scale
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius = radius, fill = accent)
    #Faja diagonal con la tinta al 14% (textura propia, no un logo).
    overlay     =   Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).polygon(
        [(int(w * 0.62), 0), (int(w * 0.78), 0), (w, h), (int(w * 0.84), h)],
        fill = (*tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5)), 36),
    )
    image       =   Image.alpha_composite(image, overlay)
    draw        =   ImageDraw.Draw(image)
    text        =   campaign['label']
    font        =   _font(int(h * 0.42))
    box         =   draw.textbbox((0, 0), text, font = font)
    draw.text(
        ((w - (box[2] - box[0])) / 2 - box[0], (h - (box[3] - box[1])) / 2 - box[1]),
        text, font = font, fill = ink,
    )
    image       =   image.resize((LABEL_W, LABEL_H), Image.LANCZOS)
    buffer      =   io.BytesIO()
    image.save(buffer, 'WEBP', quality = 90, method = 6)
    return buffer.getvalue(), LABEL_W, LABEL_H
def _load_image(path):
    """Etiqueta aportada por el usuario (--image): se normaliza a WebP."""
    from PIL import Image
    image   =   Image.open(path).convert('RGBA')
    image.thumbnail((720, 720), Image.LANCZOS)
    buffer  =   io.BytesIO()
    image.save(buffer, 'WEBP', quality = 90, method = 6)
    return buffer.getvalue(), image.width, image.height
#=========================================
# SEED COMMAND
#=========================================
class Command(BaseCommand):
    help    =   'Carga/actualiza el calendario de ofertas especiales y sus etiquetas en R2.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action = 'store_true', help = 'Regenera las etiquetas aunque ya existan')
        parser.add_argument('--only', default = '', help = 'Solo la campaña con ese slug')
        parser.add_argument('--image', action = 'append', default = [], metavar = 'SLUG=ARCHIVO', help = 'Usa una etiqueta propia (con licencia) en lugar de la generada')

    def handle(self, *args, **options):
        images      =   {}
        for raw in options['image']:
            slug, _, path   =   raw.partition('=')
            if not path or not Path(path).is_file():
                raise SystemExit(f'--image inválido: "{raw}" (formato slug=archivo existente)')
            images[slug.strip()]    =   path
        campaigns   =   [c for c in CAMPAIGNS if not options['only'] or c['slug'] == options['only']]
        if options['only'] and not campaigns:
            raise SystemExit(f'No existe la campaña "{options["only"]}".')
        if not storage_configured():
            self.stdout.write(self.style.WARNING('R2 no configurado: se cargan las campañas sin etiqueta.'))
        for position, data in enumerate(campaigns):
            campaign, _     =   SpecialOfferCampaign.objects.update_or_create(
                slug = data['slug'],
                defaults = {
                    'name'          :   data['name'],
                    'description'   :   data['description'],
                    'accent'        :   data['accent'],
                    'month'         :   data['month'],
                    'day'           :   data['day'],
                    'duration_days' :   data['duration_days'],
                    'position'      :   position,
                },
            )
            should_label    =   data['slug'] in images or options['force'] or not campaign.label_key
            if should_label and storage_configured():
                body, width, height   =   _load_image(images[data['slug']]) if data['slug'] in images else render_label(data)
                old_key     =   campaign.label_key
                key         =   put_object(f'system/offers/{data["slug"]}/{uuid.uuid4().hex}.webp', body, 'image/webp')
                SpecialOfferCampaign.objects.filter(pk = campaign.pk).update(
                    label_key = key, label_alt = f'Etiqueta de {data["name"]}',
                    label_width = width, label_height = height,
                )
                campaign.label_key  =   key
                if old_key:
                    _delete_object(old_key)
            self.stdout.write(f'  {campaign.slug:<22} {"con" if campaign.label_key else "sin"} etiqueta')
        self.stdout.write(self.style.SUCCESS(f'Campañas cargadas: {len(campaigns)}'))
