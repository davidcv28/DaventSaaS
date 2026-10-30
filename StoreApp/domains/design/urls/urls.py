from rest_framework import routers

from StoreApp.domains.design.views import DesignPatternViewSet, DesignStyleViewSet

router  =   routers.DefaultRouter()

#DESIGN ROUTERS (catálogo de patrones/estilos; lectura autenticada, escritura staff)
router.register(r'design/styles',  DesignStyleViewSet,   basename = 'StoreDesignStyles')
router.register(r'design/patterns', DesignPatternViewSet, basename = 'StoreDesignPatterns')


#PATTERNS
urlpatterns = [] + router.urls
