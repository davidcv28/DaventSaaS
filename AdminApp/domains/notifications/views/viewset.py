import uuid

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from AdminApp.domains.notifications.models import ChangelogEntry
from AdminApp.domains.notifications.serializers import (
    ChangelogEntrySerializer,
    NotificationSerializer,
)
from AdminApp.domains.notifications.services import (
    mark_reviews_seen,
    sync_subscription_notification,
    unread_reviews_count,
)

"""
Viewsets del dominio notifications.

- GET  /api/notifications/          → avisos del usuario + unread +
                                      unread_reviews (badge de Opiniones).
                                      Sincroniza el aviso de suscripción
                                      antes de responder (espejo del cron
                                      de mails, pero en tiempo real).
- POST /api/notifications/read/     → {id} marca uno, {all:true} todos.
- POST /api/notifications/reviews-seen/ → el dueño abrió Opiniones:
                                      reviews_seen_at=now y badge en 0.
- GET  /api/changelog/              → novedades publicadas (auth).
- POST /api/changelog/              → staff: crear/borrar borradores.
"""

#=========================================
# THROTTLE (polling del panel: scope propio, ver settings)
#=========================================
class NotificationPollThrottle(ScopedRateThrottle):
    scope   =   'notifications'


#=========================================
# NOTIFICATION VIEWSET
#=========================================
class NotificationViewSet(viewsets.GenericViewSet):
    permission_classes      =   [IsAuthenticated]
    throttle_classes        =   [NotificationPollThrottle]
    serializer_class        =   NotificationSerializer

    def list(self, request):
        #El aviso de fin de período se sincroniza acá (cada lectura del
        #panel): no depende del cron diario de los mails.
        sync_subscription_notification(request.user)
        qs          =   request.user.notifications.order_by('-created_at', '-id')[:50]
        unread      =   request.user.notifications.filter(read_at__isnull = True).count()
        store       =   getattr(getattr(request.user, 'profile', None), 'store', None)
        return Response({
            'notifications' :   NotificationSerializer(qs, many = True).data,
            'unread'        :   unread,
            'unread_reviews':   unread_reviews_count(request.user),
            #Marca "sin leer" por opinión: null = la tienda nunca abrió
            #la sección (todas cuentan como nuevas, igual que el badge).
            'reviews_seen_at': store.reviews_seen_at if store is not None else None,
        })

    @action(detail = False, methods = ['post'], url_path = 'read')
    def read(self, request):
        qs      =   request.user.notifications.filter(read_at__isnull = True)
        nid     =   request.data.get('id')
        if nid is not None:
            qs  =   qs.filter(pk = nid)
        elif not request.data.get('all'):
            return Response({'detail': 'Falta id o all.'}, status = status.HTTP_400_BAD_REQUEST)
        qs.update(read_at = timezone.now())
        return Response({'ok': True})

    @action(detail = False, methods = ['post'], url_path = 'reviews-seen')
    def reviews_seen(self, request):
        #Solo marca el timestamp: no requiere el beneficio de opiniones —
        #sin él unread_reviews_count ya devuelve 0.
        remaining   =   mark_reviews_seen(request.user)
        return Response({'ok': True, 'unread_reviews': remaining})


#=========================================
# CHANGELOG VIEWSET (lectura auth; escritura staff)
#=========================================
class ChangelogViewSet(viewsets.GenericViewSet):
    serializer_class    =   ChangelogEntrySerializer

    def get_queryset(self):
        qs  =   ChangelogEntry.objects.all()
        if not self.request.user.is_staff:
            #Novedades publicadas + todo el roadmap (los items de
            #"Próximamente" siempre son visibles, no usan is_published).
            qs  =   qs.filter(
                Q(is_published = True, kind = ChangelogEntry.KIND_RELEASE)
                | Q(kind = ChangelogEntry.KIND_ROADMAP)
            )
        return qs.order_by('position', '-published_at', '-created_at')

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def list(self, request):
        qs          =   self.get_queryset()
        #El changelog es corto por naturaleza: se devuelve entero (sin
        #paginado) — el front lo muestra como lista cronológica.
        return Response(self.get_serializer(qs[:100], many = True).data)

    def create(self, request):
        #Publicar (is_published=True) dispara el fan-out de notificaciones
        #en ChangelogEntry.save() — una sola vez por entrada.
        serializer  =   self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_201_CREATED)

    @action(detail = True, methods = ['post', 'delete'], url_path = 'image')
    def image(self, request, pk = None):
        """
        POST   /api/changelog/<id>/image/  → staff: sube la foto de la
                                             novedad a R2 (multipart
                                             'image'). Reemplaza la anterior.
        DELETE /api/changelog/<id>/image/  → staff: quita la foto.
        """
        from StoreApp.domains.stores.services.storage import (
            _delete_object,
            object_url,
            put_object,
            validate_image_file,
        )
        entry   =   self.get_object()
        if request.method == 'DELETE':
            if entry.image_key:
                _delete_object(entry.image_key)
                entry.image_key   =   ''
                entry.save(update_fields = ['image_key', 'updated_at'])
            return Response({'ok': True, 'image_url': None})
        upload      =   request.FILES.get('image')
        if upload is None:
            return Response({'detail': 'Falta el archivo image.'}, status = status.HTTP_400_BAD_REQUEST)
        error       =   validate_image_file(upload)
        if error:
            return Response({'detail': error}, status = status.HTTP_400_BAD_REQUEST)
        ext         =   upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else 'jpg'
        old         =   entry.image_key
        entry.image_key =   put_object(f'changelog/{uuid.uuid4()}.{ext}', upload.read(), upload.content_type)
        entry.save(update_fields = ['image_key', 'updated_at'])
        _delete_object(old)
        return Response({'ok': True, 'image_url': object_url(entry.image_key)})
