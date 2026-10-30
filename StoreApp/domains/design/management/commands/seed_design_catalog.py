import json
from pathlib import Path

from django.core.management import BaseCommand
from django.db import transaction

from StoreApp.domains.design.models import DesignPattern, DesignStyle
from StoreApp.domains.design.seed import (
    BASE_STYLE,
    DEFAULT_PATTERN,
    DEFAULT_STYLE,
    build_markup,
)

"""

Carga/actualiza el catálogo de diseño en la base (idempotente).

Fuente: `StoreApp/domains/design/seed_data.json` — export del catálogo del
front (22 estilos del Studio + 8 patrones de plantilla). Deja marcado el
estilo `base` y el patrón `raiz` como predeterminados de la plataforma.

Uso:
    manage.py seed_design_catalog
    manage.py seed_design_catalog --styles-only
    manage.py seed_design_catalog --patterns-only

"""
SEED_FILE   =   Path(__file__).resolve().parents[2] / 'seed_data.json'

#=========================================
# SEED DESIGN CATALOG
#=========================================
class Command(BaseCommand):
    help    =   'Carga/actualiza los estilos y patrones de diseño por slug.'

    def add_arguments(self, parser):
        parser.add_argument('--styles-only', action = 'store_true', help = 'Solo estilos')
        parser.add_argument('--patterns-only', action = 'store_true', help = 'Solo patrones')

    def handle(self, *args, **options):
        data        =   json.loads(SEED_FILE.read_text(encoding = 'utf-8'))
        styles      =   [] if options['patterns_only'] else [BASE_STYLE, *data.get('styles', [])]
        patterns    =   [] if options['styles_only'] else data.get('patterns', [])
        with transaction.atomic():
            style_count     =   self._styles(styles)
            pattern_count   =   self._patterns(patterns)
            self._mark_defaults(styles, patterns)
        self.stdout.write(self.style.SUCCESS(
            f'Estilos: {style_count} · Patrones: {pattern_count} · '
            f'default: {DEFAULT_STYLE}/{DEFAULT_PATTERN}'
        ))

    #ESTILOS
    def _styles(self, styles):
        for position, style in enumerate(styles):
            DesignStyle.objects.update_or_create(
                slug = style['slug'],
                defaults = {
                    'nombre'        :   style['nombre'],
                    'categoria'     :   style['categoria'],
                    'descripcion'   :   style.get('descripcion', ''),
                    'tier'          :   style.get('tier', 'base'),
                    'template'      :   style.get('template', ''),
                    'layout'        :   style.get('layout') or {},
                    'layout_spec'   :   style.get('layout_spec') or {},
                    'page_theme'    :   style.get('page_theme', 'light'),
                    'tokens'        :   style.get('tokens') or {},
                    'tags'          :   style.get('tags') or [],
                    'position'      :   position,
                },
            )
        return len(styles)

    #PATRONES
    def _patterns(self, patterns):
        for position, pattern in enumerate(patterns):
            #Un patrón puede traer su markup propio en el seed (diseño
            #hecho a mano); si no, se arma el esqueleto por bloque.
            html, css, js = build_markup(pattern)
            html = pattern.get('html') or html
            css = pattern.get('css') or css
            js = pattern.get('js') or js
            DesignPattern.objects.update_or_create(
                slug = pattern['slug'],
                defaults = {
                    'nombre'        :   pattern['nombre'],
                    'categoria'     :   pattern['categoria'],
                    'descripcion'   :   pattern.get('descripcion', ''),
                    'tier'          :   pattern.get('tier', 'base'),
                    'template'      :   pattern.get('template', ''),
                    'layout'        :   pattern.get('layout') or {},
                    'html'          :   html,
                    'css'           :   css,
                    'js'            :   js,
                    'tokens'        :   pattern.get('tokens') or {},
                    'tags'          :   pattern.get('tags') or [],
                    'position'      :   position,
                },
            )
        return len(patterns)

    #DEFAULTS (uno solo por tabla)
    def _mark_defaults(self, styles, patterns):
        if styles:
            DesignStyle.objects.filter(is_default = True).exclude(slug = DEFAULT_STYLE).update(is_default = False)
            DesignStyle.objects.filter(slug = DEFAULT_STYLE).update(is_default = True)
        if patterns:
            DesignPattern.objects.filter(is_default = True).exclude(slug = DEFAULT_PATTERN).update(is_default = False)
            DesignPattern.objects.filter(slug = DEFAULT_PATTERN).update(is_default = True)
