# live_mode/mp_status_detail: trazabilidad del origen del cobro en MP.
# live_mode=False identifica un pago hecho con credenciales TEST — en
# producción ese cobro se rechaza antes de acreditar el plan (ver
# payments.services._reject_test_payment).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_alter_payment_suscription_alter_payment_user_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name = 'payment',
            name = 'live_mode',
            field = models.BooleanField(blank = True, null = True, verbose_name = 'Cobro real (live) de Mercado Pago'),
        ),
        migrations.AddField(
            model_name = 'payment',
            name = 'mp_status_detail',
            field = models.CharField(blank = True, default = '', max_length = 255, verbose_name = 'Detalle de estado de Mercado Pago'),
        ),
    ]
