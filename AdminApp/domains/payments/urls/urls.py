from rest_framework import routers
from AdminApp.domains.payments.views import PaymentViewSet, DailyRevenueViewSet, MonthlyRevenueViewSet

router  =   routers.DefaultRouter()

#PAYMENTS ROUTER
router.register(r'payments', PaymentViewSet, basename = 'Payments')
router.register(r'daily-revenues', DailyRevenueViewSet, basename = 'DailyRevenues')
router.register(r'monthly-revenues', MonthlyRevenueViewSet, basename = 'MonthlyRevenues')


#PATTERNS
urlpatterns = [] + router.urls
