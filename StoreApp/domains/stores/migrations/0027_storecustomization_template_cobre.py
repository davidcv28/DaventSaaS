from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0026_alter_storecustomization_template'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storecustomization',
            name='template',
            field=models.CharField(choices=[('classic', 'Clásico'), ('perspective', 'Perspectiva'), ('promo', 'Publicidad'), ('street', 'Urbano'), ('terminal', 'Terminal'), ('lookbook', 'Lookbook'), ('shop', 'Tienda Pro'), ('cobre', 'Cobre')], default='classic', max_length=12, verbose_name='Diseño de la web'),
        ),
    ]
