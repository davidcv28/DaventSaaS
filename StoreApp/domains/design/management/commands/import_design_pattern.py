import re
from pathlib import Path

from django.core.management import BaseCommand, CommandError
from django.db import transaction

from StoreApp.domains.design.models import DesignPattern, DesignStyle

"""

Importa un diseño HTML de archivo único como DesignPattern.

El archivo se parte en las tres capas del modelo:
  - `css`  : contenido de todos los <style>…</style>
  - `js`   : contenido de todos los <script>…</script>
  - `html` : cuerpo del documento, sin <style>/<script> (y sin <title>/<meta>
             sueltos que algunos exports dejan dentro del body)

El `layout`, la plantilla y el tier se heredan del DesignStyle indicado en
`--style` (si existe), así el patrón queda combinable con el resto del
catálogo. `--accent` y `--fonts` arman los tokens del patrón.

Uso:
    manage.py import_design_pattern --file "Atelier Otoño.html" \
        --slug atelier-otono --nombre "Atelier Otoño" \
        --style atelier-otono --accent "#2D4A3E" \
        --fonts hanken-grotesk,bricolage-grotesque

"""
STYLE_RE    =   re.compile(r'<style[^>]*>(.*?)</style>', re.S | re.I)
SCRIPT_RE   =   re.compile(r'<script[^>]*>(.*?)</script>', re.S | re.I)
BODY_RE     =   re.compile(r'<body[^>]*>(.*?)</body>', re.S | re.I)
HEAD_RE     =   re.compile(r'<(title|meta)\b[^>]*>.*?</\1>|<(title|meta)\b[^>]*/?>', re.S | re.I)

#=========================================
# IMPORT DESIGN PATTERN
#=========================================
class Command(BaseCommand):
    help    =   'Importa un diseño HTML como patrón (html + css + js).'

    def add_arguments(self, parser):
        parser.add_argument('--file', required = True, help = 'Ruta del archivo HTML')
        parser.add_argument('--slug', required = True, help = 'Slug del patrón')
        parser.add_argument('--nombre', required = True, help = 'Nombre visible')
        parser.add_argument('--categoria', default = '', help = 'Categoría (hereda del estilo)')
        parser.add_argument('--template', default = '', help = 'Plantilla del front (hereda del estilo)')
        parser.add_argument('--tier', default = '', choices = ['', 'base', 'plus', 'advanced'], help = 'Nivel de plan')
        parser.add_argument('--style', default = '', help = 'Slug del DesignStyle del que hereda layout/plantilla')
        parser.add_argument('--accent', default = '', help = 'Color de acento (#RRGGBB) para los tokens')
        parser.add_argument('--fonts', default = '', help = 'Fuentes separadas por coma: cuerpo,cabecera')
        parser.add_argument('--preview', default = '', help = 'Miniatura/URL opcional')
        parser.add_argument('--inactive', action = 'store_true', help = 'Crear el patrón desactivado')

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            raise CommandError(f'No existe el archivo: {path}')

        html, css, js = self._split(path.read_text(encoding = 'utf-8'))
        style = None
        if options['style']:
            style = DesignStyle.objects.filter(slug = options['style']).first()
            if not style:
                raise CommandError(f'No existe el estilo: {options["style"]}')

        fonts = [f.strip() for f in options['fonts'].split(',') if f.strip()]
        tokens = {}
        if fonts:
            tokens['fonts'] = fonts
        if options['accent']:
            tokens['accent'] = options['accent']
        if style and isinstance(style.tokens, dict):
            tokens = {**style.tokens, **tokens}

        defaults = {
            'nombre'        :   options['nombre'],
            'categoria'     :   options['categoria'] or (style.categoria if style else 'general'),
            'tier'          :   options['tier'] or (style.tier if style else 'base'),
            'template'      :   options['template'] or (style.template if style else 'raiz'),
            'layout'        :   (style.layout if style else {}) or {},
            'html'          :   html,
            'css'           :   css,
            'js'            :   js,
            'tokens'        :   tokens,
            'preview'       :   options['preview'],
            'is_active'     :   not options['inactive'],
        }
        with transaction.atomic():
            pattern, created = DesignPattern.objects.update_or_create(
                slug = options['slug'], defaults = defaults,
            )
            if style and not pattern.style_id:
                pattern.style = style
                pattern.save(update_fields = ['style'])

        self.stdout.write(self.style.SUCCESS(
            f'{"Creado" if created else "Actualizado"} patrón {pattern.slug} · '
            f'html {len(html)} · css {len(css)} · js {len(js)}'
        ))

    #=========================================
    # SPLIT DEL DOCUMENTO
    #=========================================
    def _split(self, document):
        css = '\n'.join(m.group(1).strip() for m in STYLE_RE.finditer(document)).strip()
        js  = '\n'.join(m.group(1).strip() for m in SCRIPT_RE.finditer(document)).strip()
        body = BODY_RE.search(document)
        html = body.group(1) if body else document
        html = STYLE_RE.sub('', html)
        html = SCRIPT_RE.sub('', html)
        html = HEAD_RE.sub('', html)
        return html.strip(), css, js
