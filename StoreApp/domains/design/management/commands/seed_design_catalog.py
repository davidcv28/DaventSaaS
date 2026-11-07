import json
import re
from pathlib import Path

from django.core.management import BaseCommand
from django.db import transaction

from StoreApp.domains.design.models import (
    DesignCategory,
    DesignIconStyle,
    DesignPattern,
    DesignStyle,
)
from StoreApp.domains.design.seed import (
    BASE_STYLE,
    CATEGORIES,
    DEFAULT_PATTERN,
    DEFAULT_RUBRO,
    DEFAULT_STYLE,
    build_markup,
    style_rubro,
)
from StoreApp.domains.design.services.source_document import load_source

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
            self._categories()
            style_count     =   self._styles(styles)
            pattern_count   =   self._patterns(patterns)
            #Vínculo explícito al diseño (slug de DesignPattern) declarado en
            #el seed: se resuelve después de cargar los patrones porque el
            #diseño puede no existir todavía en la primera corrida.
            for style in styles:
                if style.get('pattern'):
                    DesignStyle.objects.filter(slug = style['slug']).update(
                        pattern = DesignPattern.objects.filter(slug = style['pattern']).first()
                    )
            self._link_styles()
            self._mark_defaults(styles, patterns)
        self.stdout.write(self.style.SUCCESS(
            f'Estilos: {style_count} · Patrones: {pattern_count} · '
            f'default: {DEFAULT_STYLE}/{DEFAULT_PATTERN}'
        ))

    #CATEGORÍAS (rubros compartidos)
    def _categories(self):
        for position, category in enumerate(CATEGORIES):
            DesignCategory.objects.update_or_create(
                slug = category['slug'],
                defaults = {
                    'nombre'    :   category['nombre'],
                    'position'  :   position,
                    'is_active' :   True,
                },
            )
        return len(CATEGORIES)

    #Rubro del estilo: el seed trae descriptores ("Tienda de moda
    #nocturna") que STYLE_RUBRO pliega al rubro; BASE_STYLE ya es 'general'.
    @staticmethod
    def _style_category(categoria):
        return DesignCategory.objects.filter(slug = style_rubro(categoria)).first()

    #Rubro del patrón: el seed ya trae el slug; si llegara un descriptor
    #viejo se pliega igual que en estilos.
    @staticmethod
    def _pattern_category(categoria):
        slug = str(categoria or '').strip() or DEFAULT_RUBRO
        row = DesignCategory.objects.filter(slug = slug).first()
        if row is None:
            row = DesignCategory.objects.filter(slug = style_rubro(slug)).first()
        return row or DesignCategory.objects.filter(slug = DEFAULT_RUBRO).first()

    #ESTILOS
    def _styles(self, styles):
        for position, style in enumerate(styles):
            DesignStyle.objects.update_or_create(
                slug = style['slug'],
                defaults = {
                    'nombre'        :   style['nombre'],
                    'categoria'     :   self._style_category(style.get('categoria')),
                    'descripcion'   :   style.get('descripcion', ''),
                    'tier'          :   style.get('tier', 'base'),
                    'template'      :   style.get('template', ''),
                    'layout'        :   style.get('layout') or {},
                    'layout_spec'   :   style.get('layout_spec') or {},
                    'page_theme'    :   style.get('page_theme', 'light'),
                    'tokens'        :   style.get('tokens') or {},
                    'effects'       :   style.get('effects') or {},
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
            variables = pattern.get('variables') or {}
            #La fuente editable (`sources/<slug>.html`) manda sobre el JSON:
            #el markup se parte en html/css/js y las variables declaradas se
            #derivan de los placeholders que el diseño usa de verdad.
            source = load_source(pattern['slug'])
            if source is not None:
                html, css, js, variables = source
            defaults = {
                'nombre'        :   pattern['nombre'],
                'categoria'     :   self._pattern_category(pattern.get('categoria')),
                #`dynamic` marca si el diseño es animado: explícito en el
                #seed o detectado en el markup (keyframes/animation/rAF).
                'dynamic'       :   pattern.get('dynamic', self._animated(css, js)),
                'descripcion'   :   pattern.get('descripcion', ''),
                'tier'          :   pattern.get('tier', 'base'),
                'template'      :   pattern.get('template', ''),
                'layout'        :   pattern.get('layout') or {},
                'html'          :   html,
                'css'           :   css,
                'js'            :   js,
                #Contrato de datos del patrón: sin `variables` el
                #markup es demo estático y la web sigue con la
                #plantilla Vue (ver services/pattern_render.py).
                'variables'     :   variables,
                'supports_dark_mode': pattern.get('supports_dark_mode', True),
                'tokens'        :   pattern.get('tokens') or {},
                'tags'          :   pattern.get('tags') or [],
                'preview'       :   pattern.get('preview', ''),
                #Estilo firma del patrón (FK opcional): permite que el
                #documento use `data-ds-style` aun sin estilo elegido.
                'style'         :   DesignStyle.objects.filter(slug = pattern.get('style')).first() if pattern.get('style') else None,
                'position'      :   position,
            }
            #Set de iconos propio del patrón (slug de DesignIconStyle): si no
            #lo declara, conserva el que ya tenga (o el default de la app).
            if pattern.get('icon_style'):
                defaults['icon_style'] = DesignIconStyle.objects.filter(slug = pattern['icon_style']).first()
            DesignPattern.objects.update_or_create(slug = pattern['slug'], defaults = defaults)
        return len(patterns)

    #ANIMADO: keyframes/propiedad animation en el CSS o rAF en el JS.
    _ANIM_RE    =   re.compile(r'@keyframes|animation(-[\w-]+)?\s*:', re.IGNORECASE)

    @classmethod
    def _animated(cls, css, js):
        return bool(cls._ANIM_RE.search(css or '') or 'requestAnimationFrame' in (js or ''))

    #ESTILOS PROPIOS DE CADA DISEÑO (FK DesignStyle.pattern)
    def _link_styles(self):
        #El vínculo explícito (patrón que ya usa el estilo) manda; si no,
        #cae en el patrón de la misma plantilla y por último en el default.
        #Nunca pisa un vínculo ya asignado a mano.
        for style in DesignStyle.objects.filter(pattern__isnull = True):
            pattern = (
                DesignPattern.objects.filter(style = style).order_by('-is_default', 'position').first()
                or DesignPattern.objects.filter(template = style.template).order_by('-is_default', 'position').first()
                or DesignPattern.objects.filter(is_default = True).first()
            )
            if pattern is not None:
                DesignStyle.objects.filter(pk = style.pk).update(pattern = pattern)

    #DEFAULTS (uno solo por tabla)
    def _mark_defaults(self, styles, patterns):
        if styles:
            DesignStyle.objects.filter(is_default = True).exclude(slug = DEFAULT_STYLE).update(is_default = False)
            DesignStyle.objects.filter(slug = DEFAULT_STYLE).update(is_default = True)
        if patterns:
            DesignPattern.objects.filter(is_default = True).exclude(slug = DEFAULT_PATTERN).update(is_default = False)
            DesignPattern.objects.filter(slug = DEFAULT_PATTERN).update(is_default = True)
