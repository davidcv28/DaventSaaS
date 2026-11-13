from django.db import models

"""

Feed social de la tienda (página /novedades de la web pública).

El dueño publica posts de cinco tipos: 'text' (solo texto), 'image' y
'video' (archivo propio en R2 — las imágenes pasan por normalize_image,
los videos van crudos con tope de peso), 'embed' (URL de TikTok,
YouTube, Instagram, Facebook o X — se renderiza embebido o como tarjeta
de link) y 'poll' (encuesta: la caption es la pregunta y las opciones
viven en FeedPollOption).

La interacción es solo de compradores registrados (customers.Customer,
JWT propio): FeedLike (un like por post por cuenta), FeedPollVote (un
voto por encuesta por cuenta — se guarda el post desnormalizado para el
unique) y FeedComment (visible salvo que el dueño lo oculte, is_hidden).
Los posts son cronológicos (-created_at): no hay reorden manual.

"""

#=========================================
# FEED POST
#=========================================
class FeedPost(models.Model):
    KIND_TEXT           =   'text'
    KIND_IMAGE          =   'image'
    KIND_VIDEO          =   'video'
    KIND_EMBED          =   'embed'
    KIND_POLL           =   'poll'
    KIND_CHOICES        =   [
        (KIND_TEXT,   'Texto'),
        (KIND_IMAGE,  'Imagen'),
        (KIND_VIDEO,  'Video'),
        (KIND_EMBED,  'Publicación de red social'),
        (KIND_POLL,   'Encuesta'),
    ]
    MEDIA_KINDS         =   {KIND_IMAGE, KIND_VIDEO}
    store                   =   models.ForeignKey('stores.Store', on_delete = models.CASCADE, related_name = 'feed_posts')
    kind                    =   models.CharField(max_length = 10, choices = KIND_CHOICES, verbose_name = 'Tipo')
    #Texto del post; en las encuestas es la pregunta.
    caption                 =   models.CharField(max_length = 2200, blank = True, default = '', verbose_name = 'Texto')
    #Media propia (imagen WebP normalizada o video crudo) — key/tamaño
    #en R2, mismo patrón que StoreGalleryImage.
    media_key               =   models.CharField(max_length = 200, blank = True, default = '', verbose_name = 'Media (key en R2)')
    media_size              =   models.PositiveIntegerField(default = 0, verbose_name = 'Tamaño (bytes)')
    #Embed de red social: URL original + proveedor detectado (la src del
    #iframe se deriva, no se guarda).
    embed_url               =   models.URLField(max_length = 500, blank = True, default = '', verbose_name = 'URL de la publicación')
    embed_provider          =   models.CharField(max_length = 20, blank = True, default = '', verbose_name = 'Proveedor')
    is_published            =   models.BooleanField(default = True, verbose_name = 'Publicado')
    created_at              =   models.DateTimeField(auto_now_add = True)
    updated_at              =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label           =   'feed'
        verbose_name        =   'Publicación del feed'
        verbose_name_plural =   'Publicaciones del feed'
        ordering            =   ['-created_at', '-id']
        indexes             =   [
            models.Index(fields = ['store', 'is_published', '-created_at'], name = 'idx_feedpost_store_pub'),
        ]
    def __str__(self):
        return f'feed:{self.store.slug}#{self.pk}:{self.kind}'
#=========================================
# POLL OPTION / VOTE
#=========================================
class FeedPollOption(models.Model):
    post                    =   models.ForeignKey(FeedPost, on_delete = models.CASCADE, related_name = 'poll_options')
    label                   =   models.CharField(max_length = 90, verbose_name = 'Opción')
    position                =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    class Meta:
        app_label           =   'feed'
        verbose_name        =   'Opción de encuesta'
        verbose_name_plural =   'Opciones de encuesta'
        ordering            =   ['position', 'id']
    def __str__(self):
        return f'poll:{self.post_id}#{self.position}'
class FeedPollVote(models.Model):
    #post desnormalizado: el unique por encuesta es (post, customer) —
    #cambiar de opción borra el voto anterior en la misma transacción.
    post                    =   models.ForeignKey(FeedPost, on_delete = models.CASCADE, related_name = 'poll_votes')
    option                  =   models.ForeignKey(FeedPollOption, on_delete = models.CASCADE, related_name = 'votes')
    customer                =   models.ForeignKey('customers.Customer', on_delete = models.CASCADE, related_name = 'feed_poll_votes')
    created_at              =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label           =   'feed'
        verbose_name        =   'Voto de encuesta'
        verbose_name_plural =   'Votos de encuestas'
        constraints         =   [
            models.UniqueConstraint(fields = ['post', 'customer'], name = 'uniq_feedpollvote_post_customer'),
        ]
#=========================================
# LIKE
#=========================================
class FeedLike(models.Model):
    post                    =   models.ForeignKey(FeedPost, on_delete = models.CASCADE, related_name = 'likes')
    customer                =   models.ForeignKey('customers.Customer', on_delete = models.CASCADE, related_name = 'feed_likes')
    created_at              =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label           =   'feed'
        verbose_name        =   'Like'
        verbose_name_plural =   'Likes'
        constraints         =   [
            models.UniqueConstraint(fields = ['post', 'customer'], name = 'uniq_feedlike_post_customer'),
        ]
#=========================================
# COMMENT (consultas/comentarios de compradores — moderable por el dueño)
#=========================================
class FeedComment(models.Model):
    post                    =   models.ForeignKey(FeedPost, on_delete = models.CASCADE, related_name = 'comments')
    customer                =   models.ForeignKey('customers.Customer', on_delete = models.CASCADE, related_name = 'feed_comments')
    body                    =   models.CharField(max_length = 600, verbose_name = 'Comentario')
    #El dueño lo oculta sin borrarlo (la moderación queda auditada).
    is_hidden               =   models.BooleanField(default = False, verbose_name = 'Oculto')
    created_at              =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label           =   'feed'
        verbose_name        =   'Comentario'
        verbose_name_plural =   'Comentarios'
        ordering            =   ['created_at', 'id']
        indexes             =   [
            models.Index(fields = ['post', 'is_hidden', 'created_at'], name = 'idx_feedcomment_post_vis'),
        ]
    def __str__(self):
        return f'comment:{self.post_id}#{self.pk}'
