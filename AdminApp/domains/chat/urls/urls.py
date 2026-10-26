from rest_framework import routers
from AdminApp.domains.chat.views import SupportChatViewSet

router  =   routers.DefaultRouter()

#SUPPORT CHAT ROUTER (cliente <-> staff)
router.register(r'chat', SupportChatViewSet, basename = 'SupportChat')


#PATTERNS
urlpatterns = [] + router.urls
