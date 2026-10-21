from django.urls import path
from rest_framework import routers
from SuscriptionApp.domains.benefits.views import PlanCatalogViewSet

router  =   routers.DefaultRouter()

#BENEFITS ROUTER
router.register(r'plans', PlanCatalogViewSet, basename = 'Plans')


#PATTERNS
urlpatterns = [] + router.urls
