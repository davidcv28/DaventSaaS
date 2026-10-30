import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from StoreApp.domains.design.models import DesignIconStyle, DesignPattern, clean_icon_set

"""
Carga (idempotente) el catálogo de estilos de iconos de los controles de
menú desde icon_seed.json.

    manage.py seed_icon_styles [--reset]

`--reset` desactiva los sets que no están en el archivo. El set marcado
`is_default` se asigna a los patrones que no tengan uno propio.
"""
SEED_FILE = Path(__file__).resolve().parents[2] / 'icon_seed.json'


class Command(BaseCommand):
    help = 'Carga el catálogo de estilos de iconos de controles de menú.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help = 'Desactiva los sets ausentes del archivo.')

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(SEED_FILE.read_text(encoding = 'utf-8'))
        rows = data.get('icon_styles') or []
        slugs = set()
        default = None
        for position, row in enumerate(rows):
            slug = str(row.get('slug') or '').strip()
            if not slug:
                continue
            slugs.add(slug)
            icon_style, _ = DesignIconStyle.objects.update_or_create(
                slug = slug,
                defaults = {
                    'nombre': row.get('nombre') or slug.title(),
                    'descripcion': row.get('descripcion') or '',
                    'categoria': row.get('categoria') or 'menu',
                    'icons': clean_icon_set(row.get('icons') or {}),
                    'stroke_width': row.get('stroke_width', 1.6),
                    'preview': row.get('preview') or '',
                    'is_active': True,
                    'position': row.get('position', position),
                },
            )
            if row.get('is_default'):
                default = icon_style
        if default:
            DesignIconStyle.objects.exclude(pk = default.pk).update(is_default = False)
            default.is_default = True
            default.save(update_fields = ['is_default'])
        if options.get('reset'):
            DesignIconStyle.objects.exclude(slug__in = slugs).update(is_active = False)
        if default:
            DesignPattern.objects.filter(icon_style__isnull = True).update(icon_style = default)
        self.stdout.write(self.style.SUCCESS(f'{len(slugs)} estilos de iconos cargados.'))
