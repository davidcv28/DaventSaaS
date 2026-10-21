from rest_framework import routers
from AdminApp.domains.locations.views.viewset import ProvinceViewSet, CityViewSet, ZipCodeViewSet

router = routers.DefaultRouter()

#LOCATION ENDPOINTS (lectura pública para selects de registro)
router.register(r'provinces', ProvinceViewSet, basename='Province')
router.register(r'cities', CityViewSet, basename='City')
router.register(r'zipcodes', ZipCodeViewSet, basename='ZipCode')

#===========================
urlpatterns = [] + router.urls

