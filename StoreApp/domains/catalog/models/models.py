from django.db import models
from django.utils import timezone

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
    offer_price                 =   models.DecimalField(max_digits = 12, decimal_places = 2, null = True, blank = True, verbose_name = 'Precio de oferta')
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
            models.CheckConstraint(condition = models.Q(offer_price__isnull = True) | models.Q(offer_price__gte = 0), name = 'ck_product_offer_price_gte_0'),
        ]
    def __str__(self):
        return f'{self.name} ({self.store.slug})'
#=========================================
# DISCOUNT MODEL (descuento programado: se activa/vence solo por fecha)
#=========================================
class Discount(models.Model):
    """
    Descuento porcentual que el dueño programa sobre su catálogo. La
    ventana [starts_at, ends_at) se evalúa al leer (nunca se materializa
    en offer_price): el descuento entra y sale de vigencia solo, sin
    tareas programadas. ends_at=None = no vence hasta pausarlo.
    """
    class Scope(models.TextChoices):
        ALL         =   'all',      'Todo el catálogo'
        CATEGORY    =   'category', 'Una categoría'
        BRAND       =   'brand',    'Una marca'
        PRODUCTS    =   'products', 'Productos elegidos'
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'discounts', db_index = False)
    name                        =   models.CharField(max_length = 60, verbose_name = 'Nombre')
    percent                     =   models.PositiveSmallIntegerField(verbose_name = 'Descuento (%)')
    scope                       =   models.CharField(max_length = 10, choices = Scope.choices, default = Scope.ALL, verbose_name = 'Alcance')
    category                    =   models.ForeignKey(Category, on_delete = models.SET_NULL, related_name = 'discounts', null = True, blank = True, db_index = False)
    brand                       =   models.ForeignKey(Brand, on_delete = models.SET_NULL, related_name = 'discounts', null = True, blank = True, db_index = False)
    products                    =   models.ManyToManyField(Product, related_name = 'discounts', blank = True)
    starts_at                   =   models.DateTimeField(verbose_name = 'Empieza')
    ends_at                     =   models.DateTimeField(null = True, blank = True, verbose_name = 'Termina')
    is_active                   =   models.BooleanField(default = True, verbose_name = 'Activo')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'catalog'
        verbose_name            =   'Descuento'
        verbose_name_plural     =   'Descuentos'
        ordering                =   ['-starts_at', '-id']
        indexes                 =   [
            models.Index(fields = ['store', 'is_active', 'starts_at'], name = 'idx_discount_window'),
        ]
        constraints             =   [
            models.CheckConstraint(condition = models.Q(percent__gte = 1, percent__lte = 99), name = 'ck_discount_percent_range'),
        ]
    def __str__(self):
        return f'-{self.percent}% {self.name} ({self.store.slug})'
    def is_running(self, moment = None):
        """Vigente en `moment` (ahora por defecto): activo y dentro de la ventana."""
        moment  =   moment or timezone.now()
        return self.is_active and self.starts_at <= moment and (self.ends_at is None or self.ends_at > moment)
#=========================================
# PRODUCT REVIEW MODEL (valoraciones y comentarios de visitantes)
#=========================================
class ProductReview(models.Model):
    """
    Opinión de un visitante sobre un producto de la web pública: like/dislike
    (is_positive, solo si la tienda habilitó valoraciones) y/o texto (solo
    con comentarios premium). Se publica directo — el dueño modera
    borrando desde su panel (no hay pre-aprobación).
    El alta pide nombre+apellido+email+captcha (fricción antispam); el
    email nunca sale en la API pública (solo lo ve el dueño al moderar).
    """
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'product_reviews', db_index = False)
    product                     =   models.ForeignKey(Product, on_delete = models.CASCADE, related_name = 'reviews', db_index = False)
    is_positive                 =   models.BooleanField(null = True, blank = True, verbose_name = 'Le gustó')
    text                        =   models.CharField(max_length = 600, blank = True, verbose_name = 'Comentario')
    name                        =   models.CharField(max_length = 80, verbose_name = 'Nombre')
    surname                     =   models.CharField(max_length = 80, verbose_name = 'Apellido')
    email                       =   models.EmailField(verbose_name = 'Email')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'catalog'
        verbose_name            =   'Opinión de producto'
        verbose_name_plural     =   'Opiniones de productos'
        ordering                =   ['-created_at', '-id']
        indexes                 =   [
            models.Index(fields = ['store', 'created_at'], name = 'idx_review_store_date'),
            models.Index(fields = ['product', 'created_at'], name = 'idx_review_product_date'),
        ]
        constraints             =   [
            #Una opinión sin voto ni texto no aporta nada (también lo
            #valida el serializer; la constraint es la segunda capa).
            models.CheckConstraint(
                condition       =   models.Q(is_positive__isnull = False) | ~models.Q(text = ''),
                name            =   'ck_review_vote_or_text',
            ),
        ]
    def __str__(self):
        return f'{self.name} sobre {self.product.name} ({self.store.slug})'
#=========================================
# PUBLIC CACHE BUST (ver stores/public_cache.py: editar/borrar catálogo,
# marcas, categorías, ofertas u opiniones refresca la web pública al toque)
#=========================================
from django.db.models.signals import post_delete, post_save


def _bust_public_catalog(sender, instance, **kwargs):
    from StoreApp.domains.stores.public_cache import bump_public_store
    bump_public_store(instance.store_id)
for _model in (Category, Brand, Product, Discount, ProductReview):
    post_save.connect(_bust_public_catalog, sender = _model)
    post_delete.connect(_bust_public_catalog, sender = _model)
del _model
