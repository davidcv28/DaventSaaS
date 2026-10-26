from rest_framework import routers
from StoreApp.domains.catalog.views import CategoryViewSet, BrandViewSet, ProductViewSet, DiscountViewSet, ReviewViewSet

router  =   routers.DefaultRouter()

#CATALOG ROUTERS (dueño autenticado; scope a su tienda)
router.register(r'categories', CategoryViewSet, basename = 'Categories')
router.register(r'brands',     BrandViewSet,    basename = 'Brands')
router.register(r'products',   ProductViewSet,  basename = 'Products')
router.register(r'discounts',  DiscountViewSet, basename = 'Discounts')
router.register(r'reviews',    ReviewViewSet,   basename = 'Reviews')


#PATTERNS
urlpatterns = [] + router.urls
