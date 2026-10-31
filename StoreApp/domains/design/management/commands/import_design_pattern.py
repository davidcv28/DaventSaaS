import re
from pathlib import Path

from django.core.management import BaseCommand, CommandError
from django.db import transaction

from StoreApp.domains.design.models import DesignPattern, DesignStyle
from StoreApp.domains.design.services.source_document import split_document

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
    manage.py import_design_pattern --file "Mi Diseño.html" \
        --slug mi-diseno --nombre "Mi Diseño" \
        --style mi-diseno --accent "#2D4A3E" \
        --fonts hanken-grotesk,bricolage-grotesque

"""

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
        parser.add_argument('--palette', default = '', help = 'Paleta clave:#hex separada por coma (bg,surface,text,muted,border,accent,primary,secondary)')
        parser.add_argument('--typography', default = '', help = 'Tipografía clave:valor separada por coma (body,heading)')
        parser.add_argument('--descripcion', default = '', help = 'Descripción del patrón (hereda del estilo)')
        parser.add_argument('--tags', default = '', help = 'Etiquetas separadas por coma')
        parser.add_argument('--position', type = int, default = 0, help = 'Orden en el catálogo')
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

        palette = self._pairs(options['palette'], hex_only = True)
        if palette:
            tokens['palette'] = {**tokens.get('palette', {}), **palette}
        typography = self._pairs(options['typography'])
        if typography:
            tokens['typography'] = {**tokens.get('typography', {}), **typography}

        defaults = {
            'nombre'        :   options['nombre'],
            'categoria'     :   options['categoria'] or (style.categoria if style else 'general'),
            'descripcion'   :   options['descripcion'] or (style.descripcion if style else ''),
            'tier'          :   options['tier'] or (style.tier if style else 'base'),
            'template'      :   options['template'] or (style.template if style else 'raiz'),
            'layout'        :   (style.layout if style else {}) or {},
            'html'          :   html,
            'css'           :   css,
            'js'            :   js,
            'tokens'        :   tokens,
            'tags'          :   [t.strip() for t in options['tags'].split(',') if t.strip()],
            'position'      :   options['position'],
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
            if style and not style.pattern_id:
                style.pattern = pattern
                style.save(update_fields = ['pattern'])

        self.stdout.write(self.style.SUCCESS(
            f'{"Creado" if created else "Actualizado"} patrón {pattern.slug} · '
            f'html {len(html)} · css {len(css)} · js {len(js)}'
        ))

    #=========================================
    # PARES CLAVE:VALOR
    #=========================================
    def _pairs(self, raw, hex_only = False):
        pairs = {}
        for chunk in (raw or '').split(','):
            key, _, value = chunk.partition(':')
            key, value = key.strip(), value.strip()
            if not key or not value:
                continue
            if hex_only and not re.fullmatch(r'#[0-9a-fA-F]{3,8}', value):
                raise CommandError(f'Color inválido para {key}: {value}')
            pairs[key] = value
        return pairs

    #=========================================
    # SPLIT DEL DOCUMENTO
    #=========================================
    def _split(self, document):
        return split_document(document)
