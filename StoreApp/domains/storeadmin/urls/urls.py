from django.urls import path
from rest_framework import routers

from StoreApp.domains.storeadmin.views import (
    SalesDailyView,
    SalesExportView,
    SalesSummaryView,
    StoreAdminCustomerViewSet,
)

#=========================================
# STOREADMIN URLS (se incluyen bajo /api/)
#=========================================
#Panel del dueño: /api/store-admin/... — todo JWT del dueño, scope de
#tienda resuelto por request (ver views/owner.py).
router  =   routers.DefaultRouter()
router.register(r'store-admin/customers', StoreAdminCustomerViewSet, basename = 'store-admin-customers')
urlpatterns = [
    path('store-admin/sales/summary/',    SalesSummaryView.as_view(),    name = 'storeadmin-sales-summary'),
    path('store-admin/sales/daily/',      SalesDailyView.as_view(),      name = 'storeadmin-sales-daily'),
    path('store-admin/sales/export.csv',  SalesExportView.as_view(),     name = 'storeadmin-sales-export'),
] + router.urls
