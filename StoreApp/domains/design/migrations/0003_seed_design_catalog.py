import json
from pathlib import Path

from django.db import migrations

"""
Carga inicial del catálogo de diseño (estilos + patrones) en la migración.

Antes dependía de `manage.py seed_design_catalog` a mano: un entorno recién
migrado (deploy, base nueva) quedaba con las tablas vacías y los selectores
de Diseño no mostraban nada. Esta migración deja el mismo catálogo cargado
de fábrica; el comando sigue existiendo para re-sincronizar cambios.

Idempotente por slug: no pisa filas que ya existan.
"""
SEED_FILE   =   Path(__file__).resolve().parents[1] / 'seed_data.json'

BASE_STYLE  =   {
    'slug'          :   'base',
    'nombre'        :   'Base',
    'categoria'     :   'general',
    'descripcion'   :   'Estilo neutro de la plataforma: claro, legible y sin adornos.',
    'tier'          :   'base',
    'template'      :   'raiz',
    'page_theme'    :   'light',
    'tokens'        :   {
        'palette'       :   {
            'primary'       :   '#0f766e',
            'secondary'     :   '#134e4a',
            'accent'        :   '#0f766e',
            'bg'            :   '#ffffff',
            'surface'       :   '#f8fafc',
            'text'          :   '#0f172a',
            'muted'         :   '#64748b',
            'border'        :   '#e2e8f0',
            'success'       :   '#059669',
            'danger'        :   '#dc2626',
        },
        'containers'    :   {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'typography'    :   {'heading': 'inter', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 700, 'letterSpacing': '-0.01em'},
        'buttons'       :   {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background'    :   {'type': 'solid', 'value': None, 'overlay': 'none'},
        'motion'        :   {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
        'mobile'        :   {'cardStyle': 'standard', 'heroHeight': 'standard'},
    },
    'layout'        :   {},
    'layout_spec'   :   {},
    'tags'          :   ['general', 'base', 'neutro'],
}
DEFAULT_STYLE       =   'base'
DEFAULT_PATTERN     =   'mercado'


def build_markup(pattern):
    slug        =   pattern['slug']
    accent      =   (pattern.get('tokens') or {}).get('accent') or '#0f766e'
    blocks      =   [
        b for b in (pattern.get('layout') or {}).get('landing') or []
        if b.get('enabled', True)
    ]
    sections    =   '\n'.join(
        f'  <section class="dp-block" data-block="{b["id"]}"></section>' for b in blocks
    )
    html        =   f'<div class="dp dp-{slug}" data-pattern="{slug}">\n{sections}\n</div>'
    css         =   (
        f'.dp-{slug} {{\n'
        f'  --dp-accent: {accent};\n'
        f'  display: flex;\n'
        f'  flex-direction: column;\n'
        f'}}\n'
        f'.dp-{slug} .dp-block {{ width: 100%; }}'
    )
    return html, css, ''


def load_catalog(apps, schema_editor):
    DesignStyle    =   apps.get_model('design', 'DesignStyle')
    DesignPattern  =   apps.get_model('design', 'DesignPattern')
    data           =   json.loads(SEED_FILE.read_text(encoding = 'utf-8'))
    styles         =   [BASE_STYLE, *data.get('styles', [])]
    patterns       =   data.get('patterns', [])
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
    for position, pattern in enumerate(patterns):
        html, css, js = build_markup(pattern)
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
    DesignStyle.objects.filter(is_default = True).exclude(slug = DEFAULT_STYLE).update(is_default = False)
    DesignStyle.objects.filter(slug = DEFAULT_STYLE).update(is_default = True)
    DesignPattern.objects.filter(is_default = True).exclude(slug = DEFAULT_PATTERN).update(is_default = False)
    DesignPattern.objects.filter(slug = DEFAULT_PATTERN).update(is_default = True)


class Migration(migrations.Migration):

    dependencies = [
        ('design', '0002_designpattern_is_default_designpattern_layout_and_more'),
    ]

    operations = [
        migrations.RunPython(load_catalog, migrations.RunPython.noop),
    ]
