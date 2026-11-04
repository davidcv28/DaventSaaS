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
# SPECIAL OFFER CAMPAIGN MODEL (calendario de ofertas especiales: sistema,
# no pertenece a ninguna tienda — Hot Sale, Black Friday, Navidad, etc.)
#=========================================
class SpecialOfferCampaign(models.Model):
    """
    Campaña comercial del calendario (datos del sistema, cargados por
    seed_special_offers). El descuento del dueño puede etiquetarse con una
    campaña: si la campaña no está vigente, el descuento no se aplica
    (regla en running_discounts_of) — así una promo "Black Friday" no
    puede quedar corriendo en marzo.
    month/day marcan el inicio recurrente anual; duration_days la ventana
    (soporta cruzar fin de año: Año Nuevo arranca en diciembre y termina
    en enero). La etiqueta (label_key) vive en R2 bajo system/offers/ —
    arte propio, no consume cuota de ninguna tienda.
    """
    slug                        =   models.SlugField(max_length = 40, unique = True)
    name                        =   models.CharField(max_length = 80, verbose_name = 'Nombre')
    description                 =   models.CharField(max_length = 200, blank = True, verbose_name = 'Descripción')
    accent                      =   models.CharField(max_length = 7, default = '#E64415', verbose_name = 'Color de acento')
    label_key                   =   models.CharField(max_length = 200, blank = True, verbose_name = 'Etiqueta (key en R2)')
    label_alt                   =   models.CharField(max_length = 120, blank = True, verbose_name = 'Texto alternativo')
    label_width                 =   models.PositiveSmallIntegerField(default = 0)
    label_height                =   models.PositiveSmallIntegerField(default = 0)
    month                       =   models.PositiveSmallIntegerField(verbose_name = 'Mes de inicio')
    day                         =   models.PositiveSmallIntegerField(verbose_name = 'Día de inicio')
    duration_days               =   models.PositiveSmallIntegerField(default = 4, verbose_name = 'Duración (días)')
    is_recurring                =   models.BooleanField(default = True, verbose_name = 'Se repite cada año')
    is_active                   =   models.BooleanField(default = True, verbose_name = 'Activa')
    position                    =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'catalog'
        verbose_name            =   'Campaña de ofertas'
        verbose_name_plural     =   'Campañas de ofertas'
        ordering                =   ['position', 'id']
    def __str__(self):
        return self.name
    def starts_at(self, moment = None):
        """Inicio de la ocurrencia anual vigente o próxima (aware)."""
        moment  =   moment or timezone.now()
        return timezone.datetime(moment.year, self.month, self.day, tzinfo = moment.tzinfo)
    def ends_at(self, moment = None):
        start   =   self.starts_at(moment)
        return start + timezone.timedelta(days = self.duration_days)
    def is_running(self, moment = None):
        """
        Vigente en `moment` (ahora por defecto). Se evalúa la ocurrencia del
        año en curso y la del anterior: una campaña que arranca en diciembre
        y cruza a enero (Año Nuevo) sigue corriendo en enero aunque el
        starts_at del año nuevo todavía no llegó.
        """
        if not self.is_active:
            return False
        moment      =   moment or timezone.now()
        duration    =   timezone.timedelta(days = self.duration_days)
        for year in (moment.year, moment.year - 1):
            try:
                start   =   timezone.datetime(year, self.month, self.day, tzinfo = moment.tzinfo)
            except ValueError:
                #29 de febrero en año no bisiesto: ese año no corre.
                continue
            if start <= moment < start + duration:
                return True
        return False
    def next_starts_at(self, moment = None):
        """Próximo inicio (el del año en curso si no pasó; si no, el siguiente)."""
        moment  =   moment or timezone.now()
        try:
            start   =   timezone.datetime(moment.year, self.month, self.day, tzinfo = moment.tzinfo)
        except ValueError:
            start   =   None
        if start is None or start <= moment:
            start   =   timezone.datetime(moment.year + 1, self.month, self.day, tzinfo = moment.tzinfo)
        return start
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
    campaign                    =   models.ForeignKey(
        SpecialOfferCampaign,
        on_delete       =   models.SET_NULL,
        related_name    =   'discounts',
        null            =   True,
        blank           =   True,
        verbose_name    =   'Campaña',
    )
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


def _bust_public_campaigns(sender, instance, **kwargs):
    #La campaña es global: toca el payload de TODAS las tiendas a la vez.
    from StoreApp.domains.stores.public_cache import bump_public_epoch
    bump_public_epoch()
post_save.connect(_bust_public_campaigns, sender = SpecialOfferCampaign)
post_delete.connect(_bust_public_campaigns, sender = SpecialOfferCampaign)
