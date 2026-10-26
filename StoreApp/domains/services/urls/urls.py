from rest_framework import routers
from StoreApp.domains.services.views import ServiceViewSet

router  =   routers.DefaultRouter()

#SERVICES ROUTERS (dueño autenticado; scope a su tienda)
router.register(r'services', ServiceViewSet, basename = 'Services')


#PATTERNS
urlpatterns = [] + router.urls
