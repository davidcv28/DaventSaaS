from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0059_customization_icon_style'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storecustomization',
            name='template',
            field=models.CharField(choices=[('raiz', 'Raíz'), ('alimentos', 'Alimentos'), ('trama', 'Trama'), ('indumentaria', 'Indumentaria'), ('boutique', 'Boutique'), ('atelier', 'Atelier'), ('mercado', 'Mercado'), ('clasico', 'Clásico'), ('circuito', 'Circuito'), ('seguridad', 'Seguridad')], default='raiz', max_length=12, verbose_name='Diseño de la web'),
        ),
        migrations.AlterField(
            model_name='storecustomization',
            name='template_draft',
            field=models.CharField(choices=[('raiz', 'Raíz'), ('alimentos', 'Alimentos'), ('trama', 'Trama'), ('indumentaria', 'Indumentaria'), ('boutique', 'Boutique'), ('atelier', 'Atelier'), ('mercado', 'Mercado'), ('clasico', 'Clásico'), ('circuito', 'Circuito'), ('seguridad', 'Seguridad')], default='raiz', max_length=12, verbose_name='Diseño de la web (borrador)'),
        ),
    ]
