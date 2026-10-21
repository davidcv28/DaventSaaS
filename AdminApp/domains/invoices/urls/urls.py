from django.urls import path
from rest_framework import routers
from AdminApp.domains.invoices.views import InvoiceViewSet, InvoiceAdminViewSet

router  =   routers.DefaultRouter()

#INVOICES ROUTER
router.register(r'invoices', InvoiceViewSet, basename = 'Invoices')

#INVOICES ADMIN ROUTER
router.register(r'invoices-admin', InvoiceAdminViewSet, basename = 'InvoicesAdmin')

#PATTERNS
urlpatterns = [] + router.urls
