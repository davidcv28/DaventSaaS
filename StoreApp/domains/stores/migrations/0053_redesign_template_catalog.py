#Rediseño de plantillas por rubro (fase 1): el catálogo público pasa de 6
#diseños + 2 patrones de IA + 20 retirados a solo 3, uno por nivel de plan:
#   raiz     (base,     generalista / retail / servicios)
#   trama    (plus,     indumentaria / moda)
#   circuito (advanced, tecnología / electrónica)
#Este RunPython remapea `template` y `template_draft` de TODAS las filas
#por afinidad de rubro (TEMPLATE_RETIRED_MAP del modelo) para que ninguna
#tienda existente pierda su web, y después ajusta choices/default de los
#dos campos. Idempotente: correrlo dos veces deja el mismo resultado; el
#reverse es no-op (los ids viejos ya no existen en el catálogo).
from django.db import migrations, models

#Espejo de StoreCustomization.TEMPLATE_RETIRED_MAP (fuente única en el
#modelo): claros/neutros -> raiz, editoriales/moda -> trama, oscuros/
#técnicos -> circuito.
RETIRED_MAP = {
    'classic': 'raiz', 'duo': 'raiz', 'minimal': 'raiz', 'calma': 'raiz',
    'mercado': 'raiz', 'studio': 'raiz', 'arena': 'raiz',
    'proceso': 'raiz', 'carta': 'raiz', 'terra': 'raiz', 'bloque': 'raiz',
    'shop': 'raiz',
    'atelier': 'trama', 'lookbook': 'trama', 'boutique': 'trama',
    'signature': 'trama', 'cobre': 'trama', 'vitrina': 'trama',
    'street': 'trama', 'riso': 'trama', 'promo': 'trama',
    'aurora': 'trama',
    'perspective': 'circuito', 'circuit': 'circuito',
    'terminal': 'circuito', 'lab': 'circuito',
    'ai_lumen': 'circuito', 'ai_pulse': 'trama',
}
CHOICES = [
    ('raiz', 'Raíz'),
    ('trama', 'Trama'),
    ('circuito', 'Circuito'),
]


def _remap(model, field):
    for old, new in RETIRED_MAP.items():
        model.objects.filter(**{field: old}).update(**{field: new})


def forwards(apps, schema_editor):
    StoreCustomization = apps.get_model('stores', 'StoreCustomization')
    _remap(StoreCustomization, 'template')
    _remap(StoreCustomization, 'template_draft')


def backwards(apps, schema_editor):
    #No-op: el catálogo viejo no se restaura (los ids retirados ya no son
    #válidos para los campos con choices nuevos).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0052_ai_design_v4_templates_and_fonts'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='storecustomization',
            name='template',
            field=models.CharField(choices=CHOICES, default='raiz', max_length=12, verbose_name='Diseño de la web'),
        ),
        migrations.AlterField(
            model_name='storecustomization',
            name='template_draft',
            field=models.CharField(choices=CHOICES, default='raiz', max_length=12, verbose_name='Diseño de la web (borrador)'),
        ),
    ]
