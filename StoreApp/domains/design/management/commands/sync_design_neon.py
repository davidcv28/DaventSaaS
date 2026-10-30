import psycopg2
from decouple import config
from psycopg2.extras import Json

from django.core.management import BaseCommand, CommandError

from StoreApp.domains.design.models import DesignPattern

"""

Replica en Neon (base remota) los patrones de diseño creados/editados en la
base local. Upsert por `slug`, junto con el `DesignStyle` referenciado por FK.

Uso:
    manage.py sync_design_neon --slug mi-patron
    manage.py sync_design_neon --slug a --slug b
    manage.py sync_design_neon --all
    manage.py sync_design_neon --slug mi-patron --dry-run

"""
PATTERN_COLS    =   [
    'slug', 'nombre', 'categoria', 'descripcion', 'tier', 'template', 'layout',
    'html', 'css', 'js', 'tokens', 'tags', 'preview', 'is_default', 'is_active',
    'position', 'created_at', 'updated_at',
]
STYLE_COLS      =   [
    'slug', 'nombre', 'categoria', 'descripcion', 'tier', 'template', 'layout',
    'layout_spec', 'page_theme', 'tokens', 'tags', 'is_default', 'is_active',
    'position', 'created_at', 'updated_at',
]
JSON_COLS       =   {'layout', 'layout_spec', 'tokens'}

#=========================================
# SYNC DESIGN NEON
#=========================================
class Command(BaseCommand):
    help    =   'Registra/actualiza patrones de diseño en la base Neon (upsert por slug).'

    def add_arguments(self, parser):
        parser.add_argument('--slug', action = 'append', default = [], help = 'Slug del patrón (repetible)')
        parser.add_argument('--all', action = 'store_true', help = 'Sincroniza todos los patrones')
        parser.add_argument('--dry-run', action = 'store_true', help = 'Solo muestra lo que haría')

    def handle(self, *args, **options):
        slugs   =   options['slug']
        if not slugs and not options['all']:
            raise CommandError('Indicá --slug <slug> (repetible) o --all.')

        queryset    =   DesignPattern.objects.select_related('style')
        if slugs:
            queryset = queryset.filter(slug__in = slugs)
            missing  = set(slugs) - set(queryset.values_list('slug', flat = True))
            if missing:
                raise CommandError(f'No existen en la base local: {", ".join(sorted(missing))}')
        patterns    =   list(queryset)

        if options['dry_run']:
            for pattern in patterns:
                style = pattern.style.slug if pattern.style_id else '-'
                self.stdout.write(f'[dry-run] {pattern.slug} - template={pattern.template} - style={style}')
            return

        url = config('NEON_DATABASE_URL', default = '')
        if not url:
            raise CommandError('Falta NEON_DATABASE_URL en el entorno (.env).')

        connection  =   psycopg2.connect(url)
        try:
            with connection, connection.cursor() as cursor:
                for pattern in patterns:
                    style_id = self._style(cursor, pattern.style) if pattern.style_id else None
                    self._pattern(cursor, pattern, style_id)
                    self.stdout.write(self.style.SUCCESS(f'{pattern.slug} -> Neon'))
        finally:
            connection.close()

    #ESTILO REFERENCIADO (FK)
    def _style(self, cursor, style):
        cursor.execute('SELECT id FROM design_designstyle WHERE slug = %s', (style.slug,))
        found = cursor.fetchone()
        if found:
            return found[0]
        return self._upsert(cursor, 'design_designstyle', STYLE_COLS, self._values(style, STYLE_COLS))

    #PATRÓN
    def _pattern(self, cursor, pattern, style_id):
        values  =   self._values(pattern, PATTERN_COLS)
        values.append(style_id)
        return self._upsert(cursor, 'design_designpattern', [*PATTERN_COLS, 'style_id'], values)

    def _values(self, instance, columns):
        return [
            Json(getattr(instance, column)) if column in JSON_COLS else getattr(instance, column)
            for column in columns
        ]

    def _upsert(self, cursor, table, columns, values):
        placeholders    =   ','.join(['%s'] * len(columns))
        updates         =   ','.join(f'{column} = EXCLUDED.{column}' for column in columns if column != 'slug')
        cursor.execute(
            f'INSERT INTO {table} ({",".join(columns)}) VALUES ({placeholders}) '
            f'ON CONFLICT (slug) DO UPDATE SET {updates} RETURNING id',
            values,
        )
        return cursor.fetchone()[0]
