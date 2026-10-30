from rest_framework import routers

from AdminApp.domains.suscriptions.views import (
    CouponViewSet,
    SuscriptionPlanViewSet,
    SuscriptionViewSet,
)

router  =   routers.DefaultRouter()

#SUSCRIPTION ROUTER
router.register(r'suscriptions', SuscriptionViewSet, basename = 'Suscriptions')
router.register(r'suscription-plans', SuscriptionPlanViewSet, basename = 'SuscriptionPlans')
router.register(r'coupons', CouponViewSet, basename = 'Coupons')


#PATTNERS
urlpatterns = [] + router.urls