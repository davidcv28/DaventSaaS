import re
import uuid
from urllib.parse import quote, urlparse

from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404

from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services import plan_benefits_of, profile_has_benefit
from StoreApp.domains.stores.services.imaging import normalize_image
from StoreApp.domains.stores.services import storage as _storage
from StoreApp.domains.stores.services.storage import (
    object_url,
    store_storage_configured,
    validate_image_file,
)

"""

Servicios del dominio Feed.

- Gate por plan: el flag 'has_feed' habilita la página /novedades y el
  panel de publicaciones (Estándar en adelante).
- Media propia a R2 con la misma mecánica que la galería (key
  stores/<id>/feed/<uuid>.<ext>, cuota max_storage_mb, BYO storage). La
  imagen pasa por normalize_image (regla global WebP); el video va
  crudo con tope de peso — Pillow no procesa video.
- Embeds: whitelist cerrada de hosts (YouTube, TikTok, Instagram,
  Facebook, X). La URL original se guarda y la src del iframe se DERIVA
  en cada respuesta — nunca se sirve HTML del usuario.

"""

#Tope de un video propio del feed (consume la cuota max_storage_mb).
VIDEO_MAX_BYTES         =   120 * 1024 * 1024
VIDEO_CONTENT_TYPES     =   {
    'video/mp4'         :   'mp4',
    'video/webm'        :   'webm',
    'video/quicktime'   :   'mov',
}
POLL_OPTIONS_MIN        =   2
POLL_OPTIONS_MAX        =   6
FEED_PAGE_SIZE          =   50
#=========================================
# GATE (flag has_feed del plan vigente)
#=========================================
def feed_enabled(profile):
    """La página Novedades se habilita con el flag 'has_feed' (Estándar+)."""
    return bool(plan_benefits_of(profile).get('has_feed'))
def public_feed_store_or_404(slug):
    """
    Misma regla que legalpages.public_store_or_404 — tienda publicada, no
    bloqueada, con link público — más el flag has_feed del plan: sin el
    beneficio la página deja de existir aunque tenga posts guardados.
    """
    store   =   get_object_or_404(
        Store.objects.select_related('user__user', 'customization'),
        slug = slug, is_published = True, is_blocked = False,
    )
    if not profile_has_benefit(store.user, 'has_public_link'):
        raise Http404
    if not feed_enabled(store.user):
        raise Http404
    return store
#=========================================
# EMBEDS (whitelist de hosts + src del iframe derivada)
#=========================================
_EMBED_HOSTS    =   {
    'youtube'   :   {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', 'music.youtube.com'},
    'tiktok'    :   {'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'},
    'instagram' :   {'instagram.com', 'www.instagram.com'},
    'facebook'  :   {'facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.watch'},
    'x'         :   {'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'},
}
def detect_embed_provider(url):
    """Proveedor del embed por host, o '' si la URL no es de una red admitida."""
    try:
        host    =   (urlparse(url).hostname or '').lower()
    except ValueError:
        return ''
    for provider, hosts in _EMBED_HOSTS.items():
        if host in hosts:
            return provider
    return ''
_YT_ID      =   re.compile(r'^[A-Za-z0-9_-]{6,20}$')
_TT_ID      =   re.compile(r'^(\d{10,25})$')
_IG_CODE    =   re.compile(r'^[A-Za-z0-9_-]{5,20}$')
def embed_iframe_src(provider, url):
    """
    URL del iframe para el embed, o '' si no se puede derivar (la vista
    cae a una tarjeta de link). X/Twitter no tiene iframe simple: siempre
    tarjeta. Solo https — jamás javascript: ni esquemas raros.
    """
    try:
        parsed      =   urlparse(url)
    except ValueError:
        return ''
    if parsed.scheme not in ('http', 'https'):
        return ''
    path    =   parsed.path or ''
    if provider == 'youtube':
        video_id    =   ''
        if parsed.hostname in ('youtu.be',):
            video_id    =   path.strip('/').split('/')[0]
        else:
            parts   =   [p for p in path.split('/') if p]
            if parts and parts[0] in ('shorts', 'embed', 'live') and len(parts) > 1:
                video_id    =   parts[1]
            else:
                from urllib.parse import parse_qs
                video_id    =   (parse_qs(parsed.query).get('v') or [''])[0]
        if _YT_ID.match(video_id or ''):
            return f'https://www.youtube-nocookie.com/embed/{video_id}'
    elif provider == 'tiktok':
        match   =   re.search(r'/video/(\d{10,25})', path)
        if match and _TT_ID.match(match.group(1)):
            return f'https://www.tiktok.com/embed/v2/{match.group(1)}'
    elif provider == 'instagram':
        match   =   re.search(r'^/(p|reel|reels)/([A-Za-z0-9_-]{5,20})/?', path)
        if match and _IG_CODE.match(match.group(2)):
            return f'https://www.instagram.com/{match.group(1)}/{match.group(2)}/embed'
    elif provider == 'facebook':
        return 'https://www.facebook.com/plugins/video.php?href=' + quote(url, safe = '') + '&show_text=false'
    return ''
#=========================================
# MEDIA UPLOAD / DELETE (imagen WebP normalizada o video crudo → R2)
#=========================================
def upload_post_media(store, post, upload):
    """
    Sube/reemplaza la media del post. kind 'image' → normalize_image
    'gallery' (WebP ≤1600px); kind 'video' → crudo con whitelist de
    content-type y tope de peso. Libera la media anterior y ajusta la
    cuota de la tienda. Lanza ValueError con mensaje es-AR.
    """
    from StoreApp.domains.feed.models import FeedPost
    if post.kind not in FeedPost.MEDIA_KINDS:
        raise ValueError('Este tipo de publicación no admite archivo propio.')
    if not store_storage_configured(store):
        raise ValueError('El almacenamiento no está configurado. Avisale a soporte.')
    if post.kind == FeedPost.KIND_IMAGE:
        error   =   validate_image_file(upload)
        if error:
            raise ValueError(error)
        processed   =   normalize_image(upload, 'gallery')
        body, _ext, _ct =   processed
        incoming    =   len(body)
    else:
        content_type    =   getattr(upload, 'content_type', '') or ''
        if content_type not in VIDEO_CONTENT_TYPES:
            raise ValueError('Formato no admitido: usá un video MP4, WebM o MOV.')
        if upload.size > VIDEO_MAX_BYTES:
            raise ValueError(f'El video no puede pesar más de {VIDEO_MAX_BYTES // (1024 * 1024)} MB.')
        processed   =   None
        incoming    =   upload.size
    #Fast path + rechequeo bajo lock (misma mecánica que la galería):
    #dos uploads concurrentes no pasan la cuota.
    new_used    =   _storage._check_quota(store, incoming, replacing_bytes = post.media_size)
    key         =   _storage._put_object(store, 'feed', upload, processed)
    old_key, old_size   =   post.media_key, post.media_size
    try:
        with transaction.atomic():
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            locked_post =   post.__class__.objects.select_for_update().get(pk = post.pk)
            new_used    =   _storage._check_quota(locked, incoming, replacing_bytes = locked_post.media_size)
            locked_post.media_key   =   key
            locked_post.media_size  =   incoming
            locked_post.save(update_fields = ['media_key', 'media_size', 'updated_at'])
            _storage._consume_quota(locked, new_used)
            post.media_key, post.media_size =   key, incoming
    except ValueError:
        _storage._delete_object(key)
        raise
    if old_key and old_key != key:
        _storage._delete_object(old_key)
    store.storage_used_bytes    =   Store.objects.get(pk = store.pk).storage_used_bytes
    return post
def delete_post_media(store, post):
    """Borra la media del post en R2 y libera la cuota."""
    key, size   =   post.media_key, post.media_size
    with transaction.atomic():
        locked      =   Store.objects.select_for_update().get(pk = store.pk)
        locked_post =   post.__class__.objects.select_for_update().get(pk = post.pk)
        locked_post.media_key   =   ''
        locked_post.media_size  =   0
        locked_post.save(update_fields = ['media_key', 'media_size', 'updated_at'])
        _storage._consume_quota(locked, locked.storage_used_bytes - size)
    post.media_key, post.media_size     =   '', 0
    _storage._delete_object(key)
def delete_post_media_objects(post):
    """Borra el objeto R2 de un post que se elimina (antes del delete)."""
    if post.media_key:
        with transaction.atomic():
            locked      =   Store.objects.select_for_update().get(pk = post.store_id)
            _storage._consume_quota(locked, locked.storage_used_bytes - post.media_size)
        _storage._delete_object(post.media_key)
#=========================================
# SERIALIZACIÓN (payload público y del dueño)
#=========================================
def post_payload(post, *, customer = None):
    """
    Payload público del post: media_url firmada/pública, embed derivado,
    encuesta con votos, contadores y el estado del comprador actual
    (my_like / my_vote) cuando viene autenticado.
    """
    options     =   []
    if post.kind == post.KIND_POLL:
        counts  =   {row['option_id']: row['n'] for row in post.poll_votes.values('option_id').annotate(n = Count('option_id'))}
        my_vote =   None
        if customer is not None:
            vote    =   post.poll_votes.filter(customer = customer).first()
            my_vote =   vote.option_id if vote else None
        total   =   sum(counts.values())
        for option in post.poll_options.all():
            votes           =   counts.get(option.id, 0)
            options.append({
                'id'        :   option.id,
                'label'     :   option.label,
                'votes'     :   votes,
                'percent'   :   round(votes * 100 / total) if total else 0,
            })
        poll    =   {'options': options, 'total': total, 'my_vote': my_vote}
    else:
        poll    =   None
    embed       =   None
    if post.kind == post.KIND_EMBED and post.embed_url:
        embed   =   {
            'provider'  :   post.embed_provider,
            'url'       :   post.embed_url,
            'iframe'    :   embed_iframe_src(post.embed_provider, post.embed_url),
        }
    return {
        'id'            :   post.pk,
        'kind'          :   post.kind,
        'caption'       :   post.caption,
        'media_url'     :   object_url(post.media_key) if post.media_key else None,
        'media_kind'    :   post.kind if post.kind in post.MEDIA_KINDS and post.media_key else None,
        'embed'         :   embed,
        'poll'          :   poll,
        'likes_count'   :   post.likes.count(),
        'comments_count':   post.comments.filter(is_hidden = False).count(),
        'my_like'       :   bool(customer is not None and post.likes.filter(customer = customer).exists()),
        'created_at'    :   post.created_at.isoformat() if post.created_at else None,
    }
def owner_post_payload(post):
    """Payload del panel: lo público + is_published y peso de la media."""
    payload             =   post_payload(post)
    payload['is_published']     =   post.is_published
    payload['media_size']       =   post.media_size
    return payload
def comment_payload(comment, *, customer = None, owner = False):
    """
    Comentario visible: nombre + inicial de apellido (sin email).
    `mine` permite al comprador borrar su propio comentario; `is_hidden`
    solo viaja al dueño.
    """
    customer_obj    =   comment.customer
    first       =   (customer_obj.first_name or '').strip()
    last        =   (customer_obj.last_name or '').strip()
    display     =   first or (customer_obj.email or 'Cliente').split('@')[0]
    if last:
        display     =   f'{display} {last[0].upper()}.'
    payload     =   {
        'id'        :   comment.pk,
        'post'      :   comment.post_id,
        'author'    :   display,
        'avatar'    :   customer_obj.avatar,
        'body'      :   comment.body,
        'mine'      :   bool(customer is not None and comment.customer_id == customer.pk),
        'created_at':   comment.created_at.isoformat() if comment.created_at else None,
    }
    if owner:
        payload['is_hidden']    =   comment.is_hidden
        payload['email']        =   customer_obj.email
    return payload
def apply_poll_options(post, labels):
    """
    Reemplaza las opciones de una encuesta (create/update). Los votos de
    opciones borradas se pierden — el front lo advierte al editar.
    """
    post.poll_options.all().delete()
    FeedPollOption  =   post.poll_options.model
    FeedPollOption.objects.bulk_create([
        FeedPollOption(post = post, label = label.strip(), position = index)
        for index, label in enumerate(labels)
    ])
def new_media_key(store_id, ext):
    """Key R2 para media del feed (helper por si otro upload la necesita)."""
    return f'stores/{store_id}/feed/{uuid.uuid4().hex}.{ext}'
