from django.db import migrations, models


def _seed_previews(apps, schema_editor):
    """Keys de preview para las apps ya sembradas (la imagen vive en R2
    como 'pos/apps/<slug>/preview.webp' — el archivo se sube con
    storage.put_object, fuera de la migración)."""
    PosApp  =   apps.get_model('pos', 'PosApp')
    for row in PosApp.objects.filter(preview_key = ''):
        row.preview_key =   f'pos/apps/{row.slug}/preview.webp'
        row.save(update_fields = ['preview_key'])


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0002_seed_pos_apps'),
    ]

    operations = [
        migrations.AddField(
            model_name='posapp',
            name='preview_key',
            field=models.CharField(blank=True, max_length=255, verbose_name='Vista previa (key en R2)'),
        ),
        migrations.RunPython(_seed_previews, migrations.RunPython.noop),
    ]
