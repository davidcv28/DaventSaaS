
from rest_framework import serializers
from AdminApp.domains.users.models import UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from .mixins import (
    #USER MODEL MIXINS
    UsersValidatorsMixins, UserPasswordUpdateMethod, UserPasswordValidateMixin, UserUpdateMethod,
    #PROFILE MODEL MIXINS
    UserProfileValidatorsMixins, UserProfileUpdateMethod,
    #REGISTER MIXINS
     UserRegisterValidate,UserRegisterCreateMethod)
from .config_fields import (
    #USER FIELDS 
    UserFieldsConfig, UserPasswordFieldsConfig, UserProfileFieldsConfig)



"""
USER PROFILE SERIALIZERS
En este apartado configuramos cada serializador del model UserProfile del dominio  para tareas esepecificas como:
-Actualización                  (Datos de perfil)
"""
#===================================
# USER PROFILE SERIALIZER
#===================================
class UserProfileSerializer(UserProfileValidatorsMixins,UserProfileUpdateMethod,serializers.ModelSerializer):
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
    #EMAIL VERIFICATION (solo lectura: se marca desde el link firmado del correo)
    email_verified      =   serializers.BooleanField(read_only = True)
    email_verified_at   =   serializers.DateTimeField(read_only = True)
    #WHATSAPP DIGEST (opt-in del resumen diario; el ENVÍO lo fuerza el beneficio
    #has_whatsapp_digest del plan en el job — el flag queda guardado igual para
    #retomarlo apenas sube de plan. sent_at solo lectura: lo marca el job.)
    whatsapp_digest         =   serializers.BooleanField(required = False)
    whatsapp_digest_sent_at =   serializers.DateTimeField(read_only = True)
    class Meta:
        model           =   UserProfile
        fields          =   ['user', 'tax_condition', 'business_name', 'type_document', 'document', 'first_name', 'last_name',
                             'province', 'city', 'address', 'phone', 'terms_accepted', 'terms_accepted_at', 'terms_version',
                             'email_verified', 'email_verified_at', 'whatsapp_digest', 'whatsapp_digest_sent_at']

    
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
# PASSWORD RESET SERIALIZERS
#=============================
#REQUEST: pide el link por correo (la respuesta de la vista es siempre genérica)
class PasswordResetRequestSerializer(serializers.Serializer):
    email               =   serializers.EmailField()

#CONFIRM: valida uid+token firmado, policy de password y resuelve el User
class PasswordResetConfirmSerializer(serializers.Serializer):
    uid                 =   serializers.CharField()
    token               =   serializers.CharField()
    new_password        =   serializers.CharField(trim_whitespace = False)
    confirm_password    =   serializers.CharField(trim_whitespace = False)

    def validate(self, attrs):
        errors  =   {}
        try:
            uid     =   force_str(urlsafe_base64_decode(attrs['uid']))
            user    =   User.objects.get(pk = uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user    =   None
        if user is None or not default_token_generator.check_token(user, attrs['token']):
            errors['token']             =   'El enlace es inválido o ya venció. Pedí uno nuevo.'
        if attrs['new_password'] != attrs['confirm_password']:
            errors['confirm_password']  =   'Las contraseñas no coinciden'
        #Policy de contraseña de Django (AUTH_PASSWORD_VALIDATORS), igual que
        #exige el frontend: largo, no común, no numérica, no similar al usuario.
        if user is not None:
            try:
                validate_password(attrs['new_password'], user = user)
            except DjangoValidationError as exc:
                errors['new_password']  =   exc.messages
        if errors:
            raise serializers.ValidationError(errors)
        attrs['user']   =   user
        attrs.pop('confirm_password')
        attrs.pop('token')
        return attrs

#=============================
# REGISTER USER SERIALIZER
#=============================
#ALTA MINIMAL: solo lo necesario para crear la cuenta + el ancla anti-abuso
#(phone) + los TyC. Los datos fiscales/de facturación (nombre, documento,
#condición fiscal, provincia/ciudad) se piden recién al iniciar un pago —
#el gate billing_required de payments los exige antes de crear el cobro.
class RegisterUserSerializer(UsersValidatorsMixins,UserProfileValidatorsMixins, UserRegisterValidate,UserRegisterCreateMethod, serializers.ModelSerializer):
    username            =   serializers.CharField(**UserFieldsConfig['username'])
    email               =   serializers.EmailField(**UserFieldsConfig['email'])
    password            =   serializers.CharField(**UserFieldsConfig['password'])
    confirm_password    =   serializers.CharField(**UserFieldsConfig['confirm_password'])
    phone               =   serializers.CharField(**UserProfileFieldsConfig['phone'])
    accept_terms        =   serializers.BooleanField(**UserFieldsConfig['accept_terms'])
    class Meta:
        model           =   User
        fields          =   ['username','email', 'password', 'confirm_password', 'phone', 'accept_terms']