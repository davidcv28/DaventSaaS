from rest_framework import routers

from AdminApp.domains.notifications.views import ChangelogViewSet, NotificationViewSet

router  =   routers.DefaultRouter()

#NOTIFICATIONS (avisos del sistema del panel — no son mensajes de chat)
router.register(r'notifications', NotificationViewSet, basename = 'Notifications')

#CHANGELOG (novedades publicadas; escritura solo staff)
router.register(r'changelog', ChangelogViewSet, basename = 'Changelog')


#PATTERNS
urlpatterns = [] + router.urls
