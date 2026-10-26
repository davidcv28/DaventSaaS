from django.db import models
from StoreApp.domains.stores.models import Store
"""

Servicios de la web del cliente (dominio Services): cuelgan de Store y
pueblan la página "Servicios" de la web pública (site_templates). La
página nunca persiste pedidos, reservas ni pagos: la selección del
visitante viaja en un mensaje de WhatsApp al dueño y el pago se hace
en persona. El precio es orientativo (None = "a convenir").

"""
#=========================================
# STORE SERVICE MODEL
#=========================================
class StoreService(models.Model):
    """
    Servicio ofrecido en la página "Servicios" de la web pública. El
    visitante marca los que le interesan y arma su presupuesto
    orientativo; el dueño los gestiona desde "Mis servicios" del panel.
    is_active apaga la visibilidad sin borrarlo. El cupo es un tope
    defensivo fijo (SERVICES_MAX del servicio), no un beneficio de plan.
    """
    NAME_MAX                =   80
    DESCRIPTION_MAX         =   160
    DURATION_MAX            =   40
    store                   =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'service_items', db_index = False)
    name                    =   models.CharField(max_length = NAME_MAX, verbose_name = 'Nombre')
    description             =   models.CharField(max_length = DESCRIPTION_MAX, blank = True, verbose_name = 'Descripción corta')
    #Precio orientativo: la web lo rotula como tal y el total se calcula
    #del lado del cliente. None = "a convenir" (no entra al subtotal).
    price                   =   models.DecimalField(max_digits = 12, decimal_places = 2, null = True, blank = True, verbose_name = 'Precio orientativo')
    duration                =   models.CharField(max_length = DURATION_MAX, blank = True, verbose_name = 'Duración estimada')
    #Icono del catálogo cerrado StoreCustomization.SERVICE_ICONS.
    icon                    =   models.CharField(max_length = 30, default = 'wrench', verbose_name = 'Icono')
    is_active               =   models.BooleanField(default = True, verbose_name = 'Visible')
    position                =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at              =   models.DateTimeField(auto_now_add = True)
    updated_at              =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label           =   'services'
        verbose_name        =   'Servicio'
        verbose_name_plural =   'Servicios'
        ordering            =   ['position', 'id']
        indexes             =   [
            models.Index(fields = ['store', 'is_active'], name = 'idx_service_store_active'),
        ]
        constraints         =   [
            models.UniqueConstraint(fields = ['store', 'name'], name = 'uq_service_store_name'),
            models.CheckConstraint(condition = models.Q(price__isnull = True) | models.Q(price__gte = 0), name = 'ck_service_price_gte_0'),
        ]
    def __str__(self):
        return f'{self.name} ({self.store.slug})'
