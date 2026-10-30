from django.contrib.auth.models import User
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.users.serializers import (
    #REGISTER SERIALIZER
    RegisterUserSerializer,
    #USER PROFILE
    UserProfileSerializer,
    #USER SERIALIZER
    UserSerializer,
    UserUpdatePasswordSerializer,
    UserUpdateSerializer,
)
from AdminApp.permissions import IsAnonimous

#=============================
# USER VIEWSET CONFIG
#=============================
UserViewSetConfig       =   {
    'list'              :   {
        'serializer'    :   UserSerializer,
        'queryset'      :   User.objects.all(),
        'permissions'   :   [IsAuthenticated, IsAdminUser]
    },
    'get'               :   {
        'serializer'    :   UserSerializer,
        'queryset'      :   User.objects.all(),
        'permissions'   :   [IsAuthenticated, IsAdminUser]
    },
    'retrieve'          :   {
        'serializer'    :   UserSerializer,
        'queryset'      :   lambda view : User.objects.filter(id = view.request.user.id).first(),
        'permissions'   :   [IsAuthenticated]
    },
    'update'            :   {
        'serializer'    :   UserUpdateSerializer,
        'queryset'      :   lambda view : User.objects.filter(id = view.request.user.id).first(),
        'permissions'   :   [IsAuthenticated],
        'message'       :   'Datos actualizados correctamente'
    }
}
# UPDATE PASSWORD
UserPassWordViewSetConfig     =   {
    'create'            :   {
        'serializer'    :   UserUpdatePasswordSerializer,
        'queryset'      :   lambda view : User.objects.filter(id = view.request.user.id).first(),
        'permissions'   :   [IsAuthenticated],
        'message'       :   'Contraseña actualizada correctamente'
    }
}
#=============================
# USER PROFILE VIEWSET CONFIG
#=============================
UserProfileVieSetConfig =   {
    'retrieve'          :   {
        'serializer'    :   UserProfileSerializer,
        'queryset'      :   lambda view: UserProfile.objects.select_related('user').filter(user = view.request.user).first(),
        'permissions'   :   [IsAuthenticated]
    },
    'update'            :   {
        'serializer'    :   UserProfileSerializer,
        'queryset'      :   lambda view: UserProfile.objects.select_related('user').filter(user = view.request.user).first(),
        'permissions'   :   [IsAuthenticated],
        'message'       :   'Perfil actualizado correctamente'
    }
}
#=============================
# USER REGISTER VIEWSET CONFIG
#=============================
UserRegisterViewSetConfig   =   {
    'create'                :   {
        'serializer'        :   RegisterUserSerializer,
        'queryset'          :   User.objects.all(),
        'permissions'       :   [IsAnonimous],
        'message'           :   'Usuario creado correctamente'
    }
}