# Generated manually — seed del catálogo POS (PLAN_POS §1).
from django.db import migrations

"""
Primera entrada del catálogo: 'mostrador' (mercados, almacenes,
autoservicios → rubro 'retail', plan mínimo 'ecommerce'). Idempotente:
update_or_create por slug.
"""

MOSTRADOR   =   {
    'nombre'        :   'DAVENT Mostrador',
    'descripcion'   :   'App de punto de venta para tu local: ventas en mostrador con sync a tu tienda. Incluida en el plan Ecommerce (requiere plan activo).',
    'rubros'        :   ['retail'],
    'tier_min'      :   'ecommerce',
    'version'       :   '1.0.0',
    'download_key'  :   '',
    'is_active'     :   True,
    'position'      :   0,
}


def seed_pos_apps(apps, schema_editor):
    PosApp  =   apps.get_model('pos', 'PosApp')
    PosApp.objects.update_or_create(slug = 'mostrador', defaults = MOSTRADOR)


def unseed_pos_apps(apps, schema_editor):
    PosApp  =   apps.get_model('pos', 'PosApp')
    PosApp.objects.filter(slug = 'mostrador').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_pos_apps, unseed_pos_apps),
    ]
