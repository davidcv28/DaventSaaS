from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.throttling import PublicReadThrottle, ResilientAnonRateThrottle
from StoreApp.domains.customers.authentication import CustomerJWTAuthentication, IsCustomer
from StoreApp.domains.feed.models import FeedComment, FeedPollOption, FeedPost
from StoreApp.domains.feed.serializers import (
    FeedCommentModerationSerializer,
    FeedCommentWriteSerializer,
    FeedPostWriteSerializer,
    FeedVoteSerializer,
)
from StoreApp.domains.feed.services import (
    FEED_PAGE_SIZE,
    comment_payload,
    delete_post_media,
    delete_post_media_objects,
    feed_enabled,
    owner_post_payload,
    post_payload,
    public_feed_store_or_404,
    upload_post_media,
)
from StoreApp.domains.stores.models import Store

"""

Vistas del dominio Feed.

Dueño (JWT DAVENT — su tienda, IDOR 404, gate has_feed → 403):
- GET/POST   /api/store-feed/posts/               lista / crear post
- PATCH/DELETE /api/store-feed/posts/<id>/        editar caption/embed/opciones / borrar
- POST/DELETE /api/store-feed/posts/<id>/media/   subir / quitar imagen o video
- GET        /api/store-feed/comments/            bandeja de comentarios (?post=)
- PATCH/DELETE /api/store-feed/comments/<id>/     ocultar/mostrar / borrar

Público (web de la tienda):
- GET  /api/stores/public/<slug>/feed/                    posts publicados
- GET  /api/stores/public/<slug>/feed/<id>/comments/      comentarios visibles
- POST /api/stores/public/<slug>/feed/<id>/comments/      comentar (customer JWT)
- DELETE /api/stores/public/<slug>/feed/comments/<id>/    borrar el propio (customer JWT)
- POST /api/stores/public/<slug>/feed/<id>/like/          toggle like (customer JWT)
- POST /api/stores/public/<slug>/feed/<id>/vote/          votar encuesta (customer JWT)

"""

#=========================================
# THROTTLES
#=========================================
class FeedWriteThrottle(ResilientAnonRateThrottle):
    #Escrituras de comprador (comentar/likear/votar): reusa el scope
    #antispam de opiniones de producto (10/hour por IP).
    scope   =   'store_review'
#=========================================
# HELPERS
#=========================================
def _my_store(request):
    return get_object_or_404(Store, user__user = request.user)
def _deny_without_feed(store):
    if not feed_enabled(store.user):
        return Response(
            {'detail': 'La página de novedades está disponible desde el plan Premium.'},
            status = status.HTTP_403_FORBIDDEN,
        )
    return None
def _public_post(slug, pk):
    store   =   public_feed_store_or_404(slug)
    return store, get_object_or_404(FeedPost, pk = pk, store = store, is_published = True)
def _public_queryset(store):
    return FeedPost.objects.filter(store = store, is_published = True).prefetch_related(
        'poll_options', 'poll_votes', 'likes', 'comments',
    )[:FEED_PAGE_SIZE]
def _notify_published(store, post):
    #Aviso in-app a los miembros de la tienda cuando un post pasa a
    #publicado (dedupe por post: republicar no re-avisa). Best-effort:
    #una falla acá nunca puede romper el alta/edición.
    if not getattr(post, 'is_published', False):
        return
    try:
        from StoreApp.domains.customers.services.notifications import notify_store_feed_post
        notify_store_feed_post(store, post)
    except Exception:
        pass
#=========================================
# DUEÑO — POSTS
#=========================================
class StoreFeedPostsView(APIView):
    permission_classes  =   [IsAuthenticated]
    def get(self, request):
        store   =   _my_store(request)
        denied  =   _deny_without_feed(store)
        if denied: return denied
        posts   =   store.feed_posts.prefetch_related('poll_options', 'poll_votes', 'likes', 'comments').all()
        return Response({'posts': [owner_post_payload(p) for p in posts]}, status = status.HTTP_200_OK)
    def post(self, request):
        store   =   _my_store(request)
        denied  =   _deny_without_feed(store)
        if denied: return denied
        serializer  =   FeedPostWriteSerializer(data = request.data, context = {'store': store})
        serializer.is_valid(raise_exception = True)
        post    =   serializer.save(store = store)
        _notify_published(store, post)
        return Response({'Exito': 'Publicación creada', 'item': owner_post_payload(post)}, status = status.HTTP_201_CREATED)
class StoreFeedPostDetailView(APIView):
    permission_classes  =   [IsAuthenticated]
    def _post(self, request, pk):
        store   =   _my_store(request)
        denied  =   _deny_without_feed(store)
        if denied: return None, denied
        return get_object_or_404(FeedPost, pk = pk, store = store), None
    def patch(self, request, pk):
        post, denied    =   self._post(request, pk)
        if denied: return denied
        serializer  =   FeedPostWriteSerializer(post, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        post    =   serializer.save()
        _notify_published(store, post)
        return Response({'Exito': 'Publicación actualizada', 'item': owner_post_payload(post)}, status = status.HTTP_200_OK)
    def delete(self, request, pk):
        post, denied    =   self._post(request, pk)
        if denied: return denied
        delete_post_media_objects(post)
        post.delete()
        return Response({'Exito': 'Publicación eliminada'}, status = status.HTTP_200_OK)
class StoreFeedPostMediaView(APIView):
    permission_classes  =   [IsAuthenticated]
    parser_classes      =   [MultiPartParser, FormParser]
    def post(self, request, pk):
        store   =   _my_store(request)
        denied  =   _deny_without_feed(store)
        if denied: return denied
        post    =   get_object_or_404(FeedPost, pk = pk, store = store)
        upload  =   request.FILES.get('file')
        if upload is None:
            return Response({'file': 'Adjuntá la imagen o el video.'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            upload_post_media(store, post, upload)
        except ValueError as exc:
            return Response({'file': str(exc)}, status = status.HTTP_400_BAD_REQUEST)
        return Response({'Exito': 'Archivo subido', 'item': owner_post_payload(post)}, status = status.HTTP_200_OK)
    def delete(self, request, pk):
        store   =   _my_store(request)
        denied  =   _deny_without_feed(store)
        if denied: return denied
        post    =   get_object_or_404(FeedPost, pk = pk, store = store)
        delete_post_media(store, post)
        return Response({'Exito': 'Archivo eliminado', 'item': owner_post_payload(post)}, status = status.HTTP_200_OK)
#=========================================
# DUEÑO — MODERACIÓN DE COMENTARIOS
#=========================================
class StoreFeedCommentsView(APIView):
    permission_classes  =   [IsAuthenticated]
    def get(self, request):
        store   =   _my_store(request)
        denied  =   _deny_without_feed(store)
        if denied: return denied
        comments    =   FeedComment.objects.filter(post__store = store).select_related('customer', 'post')
        post_id =   request.query_params.get('post')
        if post_id:
            comments    =   comments.filter(post_id = post_id)
        return Response({'comments': [comment_payload(c, owner = True) for c in comments[:500]]}, status = status.HTTP_200_OK)
class StoreFeedCommentDetailView(APIView):
    permission_classes  =   [IsAuthenticated]
    def _comment(self, request, pk):
        store   =   _my_store(request)
        denied  =   _deny_without_feed(store)
        if denied: return None, denied
        return get_object_or_404(FeedComment, pk = pk, post__store = store), None
    def patch(self, request, pk):
        comment, denied     =   self._comment(request, pk)
        if denied: return denied
        serializer  =   FeedCommentModerationSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        comment.is_hidden   =   serializer.validated_data['is_hidden']
        comment.save(update_fields = ['is_hidden'])
        return Response({'Exito': 'Comentario actualizado', 'item': comment_payload(comment, owner = True)}, status = status.HTTP_200_OK)
    def delete(self, request, pk):
        comment, denied     =   self._comment(request, pk)
        if denied: return denied
        comment.delete()
        return Response({'Exito': 'Comentario eliminado'}, status = status.HTTP_200_OK)
#=========================================
# PÚBLICO — FEED
#=========================================
class PublicFeedView(APIView):
    #CustomerJWT opcional: si viene Bearer válido setea request.customer
    #(my_like/my_vote); sin header sigue anónimo. Un token inválido da
    #401 — mismo comportamiento que el resto de endpoints de comprador.
    authentication_classes    =   [CustomerJWTAuthentication]
    permission_classes        =   [AllowAny]
    throttle_classes          =   [PublicReadThrottle]
    def get(self, request, slug):
        store   =   public_feed_store_or_404(slug)
        customer    =   getattr(request, 'customer', None)
        posts   =   [post_payload(p, customer = customer) for p in _public_queryset(store)]
        return Response({'posts': posts}, status = status.HTTP_200_OK)
class PublicFeedCommentsView(APIView):
    #Bearer opcional en GET (marca `mine`); en POST es obligatorio por el
    #permiso — un token inválido da 401 igual que en opiniones.
    authentication_classes    =   [CustomerJWTAuthentication]
    def get_permissions(self):
        return [IsCustomer()] if self.request.method == 'POST' else [AllowAny()]
    def get_throttles(self):
        klass   =   FeedWriteThrottle if self.request.method == 'POST' else PublicReadThrottle
        return [klass()]
    def get(self, request, slug, pk):
        _store, post    =   _public_post(slug, pk)
        customer    =   getattr(request, 'customer', None)
        comments    =   post.comments.filter(is_hidden = False).select_related('customer')
        return Response({'comments': [comment_payload(c, customer = customer) for c in comments]}, status = status.HTTP_200_OK)
    def post(self, request, slug, pk):
        _store, post    =   _public_post(slug, pk)
        serializer  =   FeedCommentWriteSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        comment     =   FeedComment.objects.create(
            post        =   post,
            customer    =   request.customer,
            body        =   serializer.validated_data['body'],
        )
        return Response({'item': comment_payload(comment, customer = request.customer)}, status = status.HTTP_201_CREATED)
class PublicFeedMyCommentView(APIView):
    """DELETE /api/stores/public/<slug>/feed/comments/<id>/ — borrar el propio."""
    authentication_classes    =   [CustomerJWTAuthentication]
    permission_classes        =   [IsCustomer]
    def delete(self, request, slug, pk):
        store   =   public_feed_store_or_404(slug)
        comment =   get_object_or_404(FeedComment, pk = pk, post__store = store, customer = request.customer)
        comment.delete()
        return Response(status = status.HTTP_204_NO_CONTENT)
class PublicFeedLikeView(APIView):
    authentication_classes    =   [CustomerJWTAuthentication]
    permission_classes        =   [IsCustomer]
    throttle_classes          =   [FeedWriteThrottle]
    def post(self, request, slug, pk):
        _store, post    =   _public_post(slug, pk)
        like, created   =   post.likes.get_or_create(customer = request.customer)
        if not created:
            like.delete()
        return Response({'liked': created, 'likes_count': post.likes.count()}, status = status.HTTP_200_OK)
class PublicFeedVoteView(APIView):
    authentication_classes    =   [CustomerJWTAuthentication]
    permission_classes        =   [IsCustomer]
    throttle_classes          =   [FeedWriteThrottle]
    def post(self, request, slug, pk):
        _store, post    =   _public_post(slug, pk)
        if post.kind != FeedPost.KIND_POLL:
            return Response({'detail': 'Esta publicación no es una encuesta.'}, status = status.HTTP_400_BAD_REQUEST)
        serializer  =   FeedVoteSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        option      =   get_object_or_404(FeedPollOption, pk = serializer.validated_data['option'], post = post)
        with transaction.atomic():
            #Cambio de voto: el unique (post, customer) hace que un voto
            #anterior en otra opción se reemplace atómicamente.
            post.poll_votes.filter(customer = request.customer).delete()
            post.poll_votes.create(option = option, customer = request.customer)
        return Response(post_payload(post, customer = request.customer)['poll'], status = status.HTTP_200_OK)
