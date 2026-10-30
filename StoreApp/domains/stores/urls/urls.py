from rest_framework import routers

from StoreApp.domains.stores.views import StoreViewSet

router  =   routers.DefaultRouter()

#STORES ROUTER
router.register(r'stores', StoreViewSet, basename = 'Stores')


#PATTERNS
urlpatterns = [] + router.urls
