import json
import re
from pathlib import Path

from django.db import migrations

"""

Siembra el patrón `boutique` (vitrina premium: moda, joyería y deco) en la
base ya migrada.

El catálogo se carga de fábrica en `0003_seed_design_catalog`, pero un
diseño nuevo con fuente propia (`sources/<slug>.html`) no llega a Neon ni a
ningún entorno sin shell con solo tocar el JSON. Esta migración lo deja
aplicado con `manage.py migrate`, que es lo que corre el entrypoint antes de
servir tráfico; `seed_design_catalog` y `sync_design_neon --slug boutique`
siguen siendo el camino para re-sincronizar a mano.

Idempotente por slug: re-aplicar no duplica ni pisa el default del catálogo.
"""

SEED_FILE       =   Path(__file__).resolve().parents[1] / 'seed_data.json'
SOURCE_FILE     =   Path(__file__).resolve().parents[1] / 'sources' / 'boutique.html'
SLUG            =   'boutique'

STYLE_RE        =   re.compile(r'<style[^>]*>(.*?)</style>', re.S | re.I)
SCRIPT_RE       =   re.compile(r'<script[^>]*>(.*?)</script>', re.S | re.I)
BODY_RE         =   re.compile(r'<body[^>]*>(.*?)</body>', re.S | re.I)
HEAD_RE         =   re.compile(r'<(title|meta)\b[^>]*>.*?</\1>|<(title|meta)\b[^>]*/?>', re.S | re.I)
ASSET_RE        =   re.compile(r'<script\b[^>]*\bsrc=[^>]*>\s*</script>|<link\b[^>]*>', re.S | re.I)
VAR_RE          =   re.compile(r'\{\{\s*([a-z][a-z0-9_]{0,39})\s*\}\}')


#Contrato de variables del diseño, congelado acá: una migración no debe
#depender de que `pattern_render.PATTERN_VARIABLES` siga igual. El `defaults`
#del catálogo solo usa el subconjunto que el markup pinta de verdad.
VARIABLES = {
    'store_name':         {'type': 'text',   'label': 'Nombre del negocio'},
    'store_initial':      {'type': 'text',   'label': 'Inicial del negocio'},
    'store_tagline':      {'type': 'text',   'label': 'Titular'},
    'store_description':  {'type': 'text',   'label': 'Descripción'},
    'store_about':        {'type': 'text',   'label': 'Sobre nosotros'},
    'store_location':     {'type': 'text',   'label': 'Ciudad y provincia'},
    'store_address':      {'type': 'text',   'label': 'Dirección'},
    'store_phone':        {'type': 'text',   'label': 'Teléfono / WhatsApp'},
    'store_whatsapp_url': {'type': 'text',   'label': 'Link de WhatsApp'},
    'store_email':        {'type': 'text',   'label': 'Email de contacto'},
    'store_hours':        {'type': 'text',   'label': 'Horarios'},
    'store_instagram_url': {'type': 'text',  'label': 'Instagram'},
    'store_facebook_url': {'type': 'text',   'label': 'Facebook'},
    'store_tiktok_url':   {'type': 'text',   'label': 'TikTok'},
    'store_logo':         {'type': 'image',  'label': 'Logo'},
    'store_cover':        {'type': 'image',  'label': 'Portada'},
    'store_accent':       {'type': 'color',  'label': 'Color de acento'},
    'year':               {'type': 'number', 'label': 'Año'},
    'products':           {'type': 'list',   'label': 'Productos'},
    'categories':         {'type': 'list',   'label': 'Categorías'},
    'services':           {'type': 'list',   'label': 'Servicios'},
    'gallery':            {'type': 'list',   'label': 'Galería'},
}

def split_document(document):
    """`(html, css, js)` del archivo único — mismo corte que `source_document`."""
    css = '\n'.join(m.group(1).strip() for m in STYLE_RE.finditer(document)).strip()
    js = '\n'.join(m.group(1).strip() for m in SCRIPT_RE.finditer(document)).strip()
    body = BODY_RE.search(document)
    markup = body.group(1) if body else document
    for pattern in (STYLE_RE, SCRIPT_RE, HEAD_RE, ASSET_RE):
        markup = pattern.sub('', markup)
    assets = '\n'.join(m.group(0) for m in ASSET_RE.finditer(document))
    if assets:
        markup = f'{assets}\n{markup}'
    return markup.strip(), css, js


def load_pattern():
    """
    `(pattern, position, html, css, js, variables)` desde el JSON y la fuente
    editable, o `None` si el patrón no está en el seed.
    """
    data = json.loads(SEED_FILE.read_text(encoding = 'utf-8'))
    for position, pattern in enumerate(data.get('patterns', [])):
        if pattern.get('slug') != SLUG:
            continue
        #Las variables se derivan de los placeholders que el diseño usa de
        #verdad, igual que `source_document.variables_from_markup`.
        html, css, js = split_document(SOURCE_FILE.read_text(encoding = 'utf-8'))
        used = set(VAR_RE.findall(html)) | set(VAR_RE.findall(css)) | set(VAR_RE.findall(js))
        variables = {
            name: dict(spec)
            for name, spec in VARIABLES.items()
            if name in used
        }
        return pattern, position, html, css, js, variables
    return None


def seed_boutique(apps, schema_editor):
    DesignPattern = apps.get_model('design', 'DesignPattern')
    loaded = load_pattern()
    if loaded is None:
        return
    pattern, position, html, css, js, variables = loaded
    DesignPattern.objects.update_or_create(
        slug = SLUG,
        defaults = {
            'nombre'            :   pattern['nombre'],
            'categoria'         :   pattern['categoria'],
            'descripcion'       :   pattern.get('descripcion', ''),
            'tier'              :   pattern.get('tier', 'base'),
            'template'          :   pattern.get('template', ''),
            'layout'            :   pattern.get('layout') or {},
            'html'              :   html,
            'css'               :   css,
            'js'                :   js,
            'variables'         :   variables,
            'supports_dark_mode':   pattern.get('supports_dark_mode', True),
            'tokens'            :   pattern.get('tokens') or {},
            'tags'              :   pattern.get('tags') or [],
            'preview'           :   pattern.get('preview', ''),
            'is_active'         :   True,
            'position'          :   position,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('design', '0006_prune_design_catalog'),
    ]

    operations = [
        migrations.RunPython(seed_boutique, migrations.RunPython.noop),
    ]
