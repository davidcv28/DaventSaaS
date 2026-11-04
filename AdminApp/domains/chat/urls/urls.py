from rest_framework import routers

from AdminApp.domains.chat.views import AssistantViewSet, SupportChatViewSet

router  =   routers.DefaultRouter()

#SUPPORT CHAT ROUTER (cliente <-> staff)
router.register(r'chat', SupportChatViewSet, basename = 'SupportChat')

#TU ASISTENTE (bot MCP por usuario — hilo separado del soporte)
router.register(r'assistant', AssistantViewSet, basename = 'Assistant')


#PATTERNS
urlpatterns = [] + router.urls
