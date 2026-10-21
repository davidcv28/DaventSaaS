from django.urls import path
from rest_framework import routers
from AdminApp.domains.suscriptions.views import SuscriptionViewSet, SuscriptionPlanViewSet

router  =   routers.DefaultRouter()

#SUSCRIPTION ROUTER
router.register(r'suscriptions', SuscriptionViewSet, basename = 'Suscriptions')
router.register(r'suscription-plans', SuscriptionPlanViewSet, basename = 'SuscriptionPlans')


#PATTNERS
urlpatterns = [] + router.urls