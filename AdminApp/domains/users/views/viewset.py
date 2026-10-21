from .viewset_base import UserBaseViewSet, UserPassWordBaseViewSet, UserProfileBaseVieSet, RegisterUserBaseViewSet
from .viewset_config import UserViewSetConfig, UserPassWordViewSetConfig, UserProfileVieSetConfig, UserRegisterViewSetConfig

"""

En este modulo simplemente asignamos la view_config para cada base viewset

"""
#=============================
# USER VIEWSET
#=============================
class UserViewSet(UserBaseViewSet):
    view_config = UserViewSetConfig

#=============================
# USER PASSWORD VIEWSET
#=============================
class UserPassWordViewSet(UserPassWordBaseViewSet):
    view_config = UserPassWordViewSetConfig

#=============================
# USER PROFILE VIEWSET
#=============================
class UserProfileViewSet(UserProfileBaseVieSet):
    view_config = UserProfileVieSetConfig

#=============================
# REGISTER USER VIEWSET
#=============================
class RegisterUserViewSet(RegisterUserBaseViewSet):
    view_config = UserRegisterViewSetConfig
