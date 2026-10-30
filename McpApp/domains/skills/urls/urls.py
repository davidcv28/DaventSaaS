from django.urls import path
from rest_framework import routers

from McpApp.domains.skills.views import DesignStyleViewSet, McpEndpointView

router  =   routers.DefaultRouter()

#SKILLS ROUTER (catálogo de estilos de diseño)
router.register(r'design-styles', DesignStyleViewSet, basename = 'DesignStyles')


#PATTERNS
urlpatterns = [
    path('mcp/', McpEndpointView.as_view(), name = 'mcp-endpoint'),
] + router.urls
