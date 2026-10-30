from django.core.management import BaseCommand

from McpApp.domains.skills.models import DesignModelMcp
from McpApp.domains.skills.seed_data import build_styles

"""
Carga/actualiza el catálogo base de estilos de diseño (idempotente).

Uso:
    manage.py seed_design_styles
    manage.py seed_design_styles --only cyberpunk-dark,minimal-nordic
"""

#=========================================
# SEED DESIGN STYLES
#=========================================
class Command(BaseCommand):
    help    =   'Carga/actualiza los estilos de diseño gratuitos por slug.'

    def add_arguments(self, parser):
        parser.add_argument('--only', default = '', help = 'Lista de slugs separados por coma (default: todos)')

    def handle(self, *args, **options):
        only        =   {s.strip() for s in options['only'].split(',') if s.strip()}
        created     =   0
        updated     =   0
        for style in build_styles():
            if only and style['slug'] not in only:
                continue
            _, was_created =   DesignModelMcp.objects.update_or_create(
                slug    =   style['slug'],
                defaults =  {
                    'nombre'            :   style['nombre'],
                    'categoria'         :   style['categoria'],
                    'html_componentes'  :   style['html_componentes'],
                    'tokens_diseno'     :   style['tokens_diseno'],
                    'tags'              :   style['tags'],
                },
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
        self.stdout.write(self.style.SUCCESS(f'ESTILOS DE DISEÑO: {created} creados, {updated} actualizados'))
