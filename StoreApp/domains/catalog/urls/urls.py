from rest_framework import routers

from StoreApp.domains.catalog.views import (
    BrandViewSet,
    CategoryViewSet,
    DiscountViewSet,
    ProductViewSet,
    ReviewViewSet,
    SpecialOfferCampaignViewSet,
)

router  =   routers.DefaultRouter()

#CATALOG ROUTERS (dueño autenticado; scope a su tienda)
router.register(r'categories', CategoryViewSet, basename = 'Categories')
router.register(r'brands',     BrandViewSet,    basename = 'Brands')
router.register(r'products',   ProductViewSet,  basename = 'Products')
router.register(r'discounts',  DiscountViewSet, basename = 'Discounts')
router.register(r'reviews',    ReviewViewSet,   basename = 'Reviews')
#OFFERS (calendario de campañas: lectura pública, escritura staff)
router.register(r'offers',     SpecialOfferCampaignViewSet, basename = 'Offers')


#PATTERNS
urlpatterns = [] + router.urls
