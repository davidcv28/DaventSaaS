from django.db import models
from StoreApp.domains.stores.models import Store
"""

Catálogo de la web del cliente: cuelga de Store (una tienda = un
catálogo). Category y Brand agrupan los productos en el menú lateral de
la página pública; Product es la unidad vendible con imagen en
Cloudinary (misma cuota max_storage_mb que logo/carrusel).

"""
#=========================================
# CATEGORY MODEL
#=========================================
class Category(models.Model):
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'categories', db_index = False)
    name                        =   models.CharField(max_length = 60, verbose_name = 'Nombre')
    feature_schema              =   models.JSONField(default = list, blank = True, verbose_name = 'Plantilla de características')
    position                    =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'catalog'
        verbose_name            =   'Categoría'
        verbose_name_plural     =   'Categorías'
        ordering                =   ['position', 'name', 'id']
        indexes                 =   [
            models.Index(fields = ['store'], name = 'idx_category_store'),
        ]
        constraints             =   [
            models.UniqueConstraint(fields = ['store', 'name'], name = 'uq_category_store_name'),
        ]
    def __str__(self):
        return f'{self.name} ({self.store.slug})'
#=========================================
# BRAND MODEL
#=========================================
class Brand(models.Model):
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'brands', db_index = False)
    name                        =   models.CharField(max_length = 60, verbose_name = 'Nombre')
    position                    =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'catalog'
        verbose_name            =   'Marca'
        verbose_name_plural     =   'Marcas'
        ordering                =   ['position', 'name', 'id']
        indexes                 =   [
            models.Index(fields = ['store'], name = 'idx_brand_store'),
        ]
        constraints             =   [
            models.UniqueConstraint(fields = ['store', 'name'], name = 'uq_brand_store_name'),
        ]
    def __str__(self):
        return f'{self.name} ({self.store.slug})'
#=========================================
# PRODUCT MODEL
#=========================================
class Product(models.Model):
    """
    Producto publicado en la web del cliente. is_active apaga la
    visibilidad sin borrarlo. La imagen vive en R2
    (image_key = 'stores/<id>/products/<uuid>.<ext>'); ocupa cuota del plan.
    """
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'products', db_index = False)
    category                    =   models.ForeignKey(Category, on_delete = models.SET_NULL, related_name = 'products', null = True, blank = True, db_index = False)
    brand                       =   models.ForeignKey(Brand, on_delete = models.SET_NULL, related_name = 'products', null = True, blank = True, db_index = False)
    name                        =   models.CharField(max_length = 120, verbose_name = 'Nombre')
    description                 =   models.TextField(max_length = 600, blank = True, verbose_name = 'Descripción')
    price                       =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0, verbose_name = 'Precio')
    features                    =   models.JSONField(default = dict, blank = True, verbose_name = 'Características')
    image_key                   =   models.CharField(max_length = 200, blank = True, verbose_name = 'Imagen (key en R2)')
    image_size                  =   models.PositiveIntegerField(default = 0, verbose_name = 'Tamaño de imagen (bytes)')
    is_active                   =   models.BooleanField(default = True, verbose_name = 'Visible')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'catalog'
        verbose_name            =   'Producto'
        verbose_name_plural     =   'Productos'
        ordering                =   ['name', 'id']
        indexes                 =   [
            models.Index(fields = ['store', 'is_active'], name = 'idx_product_store_active'),
            models.Index(fields = ['category'], name = 'idx_product_category'),
            models.Index(fields = ['brand'], name = 'idx_product_brand'),
        ]
        constraints             =   [
            models.CheckConstraint(condition = models.Q(price__gte = 0), name = 'ck_product_price_gte_0'),
        ]
    def __str__(self):
        return f'{self.name} ({self.store.slug})'
