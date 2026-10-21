
from rest_framework import serializers
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.locations.models import Province, City
from django.contrib.auth.models import User
from .mixins import (
    #USER MODEL MIXINS
    UsersValidatorsMixins, UserPasswordUpdateMethod, UserPasswordValidateMixin, UserUpdateMethod,
    #PROFILE MODEL MIXINS
    UserProfileValidatorsMixins,
    #REGISTER MIXINS
     UserRegisterValidate,UserRegisterCreateMethod)
from .config_fields import (
    #USER FIELDS 
    UserFieldsConfig, UserPasswordFieldsConfig, UserPasswordValidators,
    #PROFILE FIELDS
    UserProfileFieldsConfig)



"""
USER PROFILE SERIALIZERS
En este apartado configuramos cada serializador del model UserProfile del dominio  para tareas esepecificas como:
-Actualización                  (Datos de perfil)
"""
#===================================
# USER PROFILE SERIALIZER
#===================================
class UserProfileSerializer(UserProfileValidatorsMixins,serializers.ModelSerializer):
    user                =   serializers.HiddenField(default = serializers.CurrentUserDefault())
    tax_condition       =   serializers.ChoiceField(**UserProfileFieldsConfig['tax_condition'])
    business_name       =   serializers.CharField(**UserProfileFieldsConfig['business_name'])
    type_document       =   serializers.ChoiceField(**UserProfileFieldsConfig['type_document'])
    document            =   serializers.CharField(**UserProfileFieldsConfig['document'])
    first_name          =   serializers.CharField(**UserProfileFieldsConfig['first_name'])
    last_name           =   serializers.CharField(**UserProfileFieldsConfig['last_name'])
    province            =   serializers.PrimaryKeyRelatedField(**UserProfileFieldsConfig['province'])
    city                =   serializers.PrimaryKeyRelatedField(**UserProfileFieldsConfig['city'])
    address             =   serializers.CharField(**UserProfileFieldsConfig['address'])
    phone               =   serializers.CharField(**UserProfileFieldsConfig['phone'])
    #TERMS (solo lectura: se sellan en el registro, no se editan desde el perfil)
    terms_accepted      =   serializers.BooleanField(read_only = True)
    terms_accepted_at   =   serializers.DateTimeField(read_only = True)
    terms_version       =   serializers.CharField(read_only = True)
    class Meta:
        model           =   UserProfile
        fields          =   ['user', 'tax_condition', 'business_name', 'type_document', 'document', 'first_name', 'last_name',
                             'province', 'city', 'address', 'phone', 'terms_accepted', 'terms_accepted_at', 'terms_version']

    
#=============================#=============================#=============================#=============================
"""
USER SERIALIZERS
En este apartado configuramos cada serializador del model user de django para tareas esepecificas como:
-lectura                        (datos de usuario + perfil)
-actualizacion                  (Correo modelo User)
-Actualización de contraseña    
-Registro de usuario            (User + Perfil)
"""
#=============================
# USER SERIALIZER (GET)
#=============================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model   =    User
        fields  =   ['id', 'username', 'email', 'is_staff']
#=============================
# USER UPDATE SERIALIZER
#=============================
class UserUpdateSerializer(UsersValidatorsMixins,UserUpdateMethod,serializers.ModelSerializer):
    email               =   serializers.EmailField(**UserFieldsConfig['email'])
    class Meta:
        model           =   User
        fields          =   ['email']

#=============================
# USER UPDATE PASSWORD
#=============================
class UserUpdatePasswordSerializer(UserPasswordValidateMixin,UserPasswordUpdateMethod,serializers.Serializer):
    old_password        =   serializers.CharField(**UserPasswordFieldsConfig['old_password'])
    new_password        =   serializers.CharField(**UserPasswordFieldsConfig['new_password'])
    confirm_password    =   serializers.CharField(**UserPasswordFieldsConfig['confirm_password'])

#=============================
# REGISTER USER SERIALIZER
#=============================
class RegisterUserSerializer(UsersValidatorsMixins,UserProfileValidatorsMixins, UserRegisterValidate,UserRegisterCreateMethod, serializers.ModelSerializer):
    username            =   serializers.CharField(**UserFieldsConfig['username'])
    email               =   serializers.EmailField(**UserFieldsConfig['email'])
    password            =   serializers.CharField(**UserFieldsConfig['password'])
    confirm_password    =   serializers.CharField(**UserFieldsConfig['confirm_password'])
    first_name          =   serializers.CharField(**UserProfileFieldsConfig['first_name'])
    last_name           =   serializers.CharField(**UserProfileFieldsConfig['last_name'])
    tax_condition       =   serializers.ChoiceField(**UserProfileFieldsConfig['tax_condition'])
    business_name       =   serializers.CharField(**UserProfileFieldsConfig['business_name'])
    type_document       =   serializers.ChoiceField(**UserProfileFieldsConfig['type_document'])
    document            =   serializers.CharField(**UserProfileFieldsConfig['document'])
    province            =   serializers.PrimaryKeyRelatedField(**UserProfileFieldsConfig['province'])
    city                =   serializers.PrimaryKeyRelatedField(**UserProfileFieldsConfig['city'])
    address             =   serializers.CharField(**UserProfileFieldsConfig['address'])
    phone               =   serializers.CharField(**UserProfileFieldsConfig['phone'])
    accept_terms        =   serializers.BooleanField(**UserFieldsConfig['accept_terms'])
    class Meta:
        model           =   User
        fields          =   ['username','email', 'password', 'confirm_password','first_name', 'last_name',
                            'tax_condition', 'business_name', 'type_document', 'document', 'province', 'city', 'address', 'phone',
                            'accept_terms']