from django.db import migrations

"""
Limpia el catálogo de diseño y deja solo los diseños en uso.

- Patrones: `mercado` (Bazar) y `circuito` (reservado para después).
- Estilos: `base` (default de la plataforma) y `mercado` (Bazar).

Los registros de estilos/patrones retirados se eliminan también de las
bases ya migradas; sin esto, un deploy seguía mostrando el catálogo viejo
aunque `seed_data.json` ya no los tuviera.
"""

KEEP_PATTERNS = ('mercado', 'circuito')
KEEP_STYLES = ('base', 'mercado')
DEFAULT_PATTERN = 'mercado'
DEFAULT_STYLE = 'base'


def prune_catalog(apps, schema_editor):
    DesignPattern = apps.get_model('design', 'DesignPattern')
    DesignStyle = apps.get_model('design', 'DesignStyle')
    DesignPattern.objects.exclude(slug__in = KEEP_PATTERNS).delete()
    DesignStyle.objects.exclude(slug__in = KEEP_STYLES).delete()
    DesignPattern.objects.exclude(slug = DEFAULT_PATTERN).update(is_default = False)
    DesignPattern.objects.filter(slug = DEFAULT_PATTERN).update(is_default = True)
    DesignStyle.objects.exclude(slug = DEFAULT_STYLE).update(is_default = False)
    DesignStyle.objects.filter(slug = DEFAULT_STYLE).update(is_default = True)


class Migration(migrations.Migration):

    dependencies = [
        ('design', '0005_designstyle_pattern'),
    ]

    operations = [
        migrations.RunPython(prune_catalog, migrations.RunPython.noop),
    ]
