from rest_framework import routers
from AdminApp.domains.users.views import UserViewSet, UserPassWordViewSet, UserProfileViewSet, RegisterUserViewSet
router = routers.DefaultRouter()

#USER ENDPOINTS
router.register(r'user', UserViewSet, basename = 'User' )
router.register(r'password_update', UserPassWordViewSet, basename = 'password_update')
#PROFILE ENDPOINTS
router.register(r'profile', UserProfileViewSet, basename = 'Profile')
#REGISTER ENDPOINT
router.register(r'register', RegisterUserViewSet, basename = 'Register')

#===========================
urlpatterns = [] + router.urls