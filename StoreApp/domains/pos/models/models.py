import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from StoreApp.domains.stores.models import Store

"""
Dominio `pos` — POS federado (PLAN_POS).

PosApp es el catálogo de apps federadas que ofrece el plan (hoy solo
'mostrador'). PosDevice es un dispositivo vinculado por código (la app
de escritorio nunca pide email/password: el código es la única llave).
PosPairingCode es el código de un solo uso que genera el dueño desde su
panel — expira en 10 minutos y quema a los anteriores sin usar.
"""

#=========================================
# POS APP MODEL (catálogo de apps federadas)
#=========================================
class PosApp(models.Model):
    slug                =   models.SlugField(max_length = 60, unique = True, db_index = True, verbose_name = 'Slug')
    nombre              =   models.CharField(max_length = 120, verbose_name = 'Nombre')
    descripcion         =   models.TextField(blank = True, verbose_name = 'Descripción')
    #Slugs de DesignCategory (rubros compartidos del catálogo de diseño):
    #la app es visible si el rubro de la tienda intersecta o si trae
    #'general' (fallback — no se penaliza la indecisión del diseño).
    rubros              =   ArrayField(
        models.CharField(max_length = 60),
        default = list,
        blank = True,
        verbose_name = 'Rubros',
    )
    #Plan mínimo (slug de PlanPresentation: basico/estandar/premium/
    #ecommerce). Hoy solo 'ecommerce'.
    tier_min            =   models.CharField(max_length = 20, default = 'ecommerce', verbose_name = 'Plan mínimo')
    version             =   models.CharField(max_length = 20, blank = True, verbose_name = 'Versión')
    #Key del instalador en R2 (la descarga firmada es fase 3).
    download_key        =   models.CharField(max_length = 255, blank = True, verbose_name = 'Instalador (key en R2)')
    is_active           =   models.BooleanField(default = True, db_index = True, verbose_name = 'Activa')
    position            =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at          =   models.DateTimeField(auto_now_add = True)
    updated_at          =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label           =   'pos'
        verbose_name        =   'App federada'
        verbose_name_plural =   'Apps federadas'
        ordering            =   ['position', 'id']

    def __str__(self):
        return f'{self.nombre} ({self.slug})'
#=========================================
# POS DEVICE MODEL (dispositivo vinculado a una tienda)
#=========================================
class PosDevice(models.Model):
    store               =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'pos_devices', verbose_name = 'Tienda')
    device_id           =   models.UUIDField(default = uuid.uuid4, unique = True, editable = False, verbose_name = 'ID del dispositivo')
    name                =   models.CharField(max_length = 120, verbose_name = 'Nombre')
    paired_at           =   models.DateTimeField(default = timezone.now, verbose_name = 'Vinculado')
    #Lo toca cada /license/ exitoso (la app renueva la licencia en cada
    #conexión — last_seen_at es el pulso del dispositivo).
    last_seen_at        =   models.DateTimeField(null = True, blank = True, verbose_name = 'Última conexión')
    #"Desvincular esta PC" desde el dashboard: el device_token sigue
    #siendo un JWT válido pero el endpoint lo rechaza por revoked_at.
    revoked_at          =   models.DateTimeField(null = True, blank = True, verbose_name = 'Desvinculado')
    created_at          =   models.DateTimeField(auto_now_add = True)

    class Meta:
        app_label           =   'pos'
        verbose_name        =   'Dispositivo POS'
        verbose_name_plural =   'Dispositivos POS'
        indexes             =   [
            models.Index(fields = ['store', '-paired_at'], name = 'idx_pos_device_store'),
        ]

    def __str__(self):
        return f'{self.name} ({self.device_id})'
#=========================================
# POS PAIRING CODE MODEL (código de vinculación de un solo uso)
#=========================================
class PosPairingCode(models.Model):
    store               =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'pos_pairing_codes', verbose_name = 'Tienda')
    #8 chars alfanuméricos sin ambiguos (sin 0/O/1/I/L): el usuario lo
    #tipea a mano en la app. Se guarda en mayúsculas.
    code                =   models.CharField(max_length = 8, db_index = True, verbose_name = 'Código')
    expires_at          =   models.DateTimeField(verbose_name = 'Vence')
    used_at             =   models.DateTimeField(null = True, blank = True, verbose_name = 'Usado')
    created_by          =   models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'pos_pairing_codes', verbose_name = 'Creado por')
    created_at          =   models.DateTimeField(auto_now_add = True)

    class Meta:
        app_label           =   'pos'
        verbose_name        =   'Código de vinculación POS'
        verbose_name_plural =   'Códigos de vinculación POS'
        indexes             =   [
            models.Index(fields = ['store', '-created_at'], name = 'idx_pos_paircode_store'),
        ]

    def __str__(self):
        return f'{self.code} ({self.store.slug})'
