from rest_framework import routers

from AdminApp.domains.legal.views import ContentReportViewSet

router  =   routers.DefaultRouter()

#CONTENT REPORTS ROUTER (denuncias de copyright / contenido ilegal)
router.register(r'content-reports', ContentReportViewSet, basename = 'ContentReports')


#PATTERNS
urlpatterns = [] + router.urls
