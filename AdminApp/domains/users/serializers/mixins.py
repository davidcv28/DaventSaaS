
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.users.services import (
    #USER QUERYS
    UpdateUserQuery, UpdatePasswordUserQuery, RegisterUserQuery
)
from .operations import ProvinceAndCityComparation, DocumentFormat, TypeDocumentSelect, BusinessNameRequired
import re

"""

Configuramos los mixins para el dominio users

"""

#=================================
#  USER MIXINS VALIDATE
#=================================

class UsersValidatorsMixins:
    def validate_username(self, value):
        username_val    =   value.strip()
        queryset        =   User.objects.filter(username = username_val)
        errors          =   []
        if self.instance:
            queryset    =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            errors.append('El nombre de usuario ingresado ya se encuentra en uso')
        if errors:
            raise serializers.ValidationError(errors)
        return username_val

    def validate_email(self, value):
        email_val       =   value.strip()
        queryset        =   User.objects.filter(email = email_val)
        errors          =   []
        if self.instance:
            queryset    =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            errors.append('El correo ingresado ya se encuentra en uso')
        if errors:
            raise serializers.ValidationError(errors)
        return email_val

    def validate(self, attrs):
        password1   =   attrs.get('password')
        password2   =   attrs.get('confirm_password')
        errors      =   {}
        if password1 != password2:
            errors['confirm_password'] = 'Las contraseñas no coinciden'
        if errors:
            raise serializers.ValidationError(errors)
        #Default None: UserUpdateSerializer (solo email) comparte este mixin y
        #sin el default explotaba con KeyError -> 500 al actualizar el correo.
        attrs.pop('confirm_password', None)
        return attrs

#=================================
#  USER UPDATE METHOD
#=================================
class UserUpdateMethod:
    def update(self, instance, validated_data):
        return UpdateUserQuery(instance, validated_data)
#=================================
# USER PASSWORD VALIDATE MIXIN
#================================= 
class UserPasswordValidateMixin:
    def validate(self, attrs):
        user                =   self.context.get('request').user
        old_password        =   attrs.get('old_password')
        new_password        =   attrs.get('new_password')
        confirm_password    =   attrs.get('confirm_password')
        errors              =   {}
        if not user.check_password(old_password):
            errors['old_password']      =   'Contraseña actual ingresada no es correcta'
        if old_password == new_password:
            errors['new_password']      =   'No puedes utilizar la contraseña actual como nueva'
        if new_password != confirm_password:
            errors['confirm_password']  =   'Las contraseñas no coinciden'
        #Policy de contraseña (AUTH_PASSWORD_VALIDATORS): mismo criterio que
        #el reset — sin esto se podía volver a una clave débil después del alta.
        try:
            validate_password(new_password, user = user)
        except DjangoValidationError as exc:
            if 'new_password' in errors:
                errors['new_password']  =   [errors['new_password'], *exc.messages]
            else:
                errors['new_password']  =   exc.messages
        if errors:
            raise serializers.ValidationError(errors)
        attrs.pop('old_password')
        attrs.pop('confirm_password')
        return attrs
    
#=================================
# USER PASSWORD UPDATE METHOD
#================================= 
class UserPasswordUpdateMethod:
    #El viewset pasa siempre instance -> save() despacha a update(), no a
    #create(): sin este método el cambio de clave explotaba con 500.
    def update(self, instance, validated_data):
       return UpdatePasswordUserQuery(instance, validated_data)
    def create(self, instance, validated_data):
       return UpdatePasswordUserQuery(instance, validated_data)

#=================================#=================================#=================================#=================================
#=================================
# USER PROFILE  MIXINS VALIDATORS
#=================================
class UserProfileValidatorsMixins:
    def validate_document(self, value):
        document_val        =   value.strip()
        queryset            =   UserProfile.objects.filter(document = document_val)
        errors              =   []
        if self.instance:
            queryset        =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            errors.append('El documento ingresado ya se encuentra en uso')
        if re.search(r'[^0-9]', document_val):
            errors.append('En este campo solo se aceptan números')
        if errors:
            raise serializers.ValidationError(errors)
        return document_val
    def validate_phone(self, value):
        if not value:
            return None
        phone_val           =   value.strip()
        queryset            =   UserProfile.objects.filter(phone = phone_val)
        if self.instance:
            queryset        =   queryset.exclude(pk = self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('El número de celular ingresado ya se encuentra en uso')
        return phone_val
    def validate(self, attrs):
        tax_condition   =   attrs.get('tax_condition')
        type_document   =   attrs.get('type_document')
        business_name   =   attrs.get('business_name')
        province_select =   attrs.get('province')
        city_select     =   attrs.get('city')
        document        =   attrs.get('document')
        errors          =   {}
        type_document   =   TypeDocumentSelect(tax_condition, type_document)
        attrs['type_document']          =   type_document
        if not BusinessNameRequired(tax_condition, business_name):
            errors['business_name']     = 'Este campo es obligatorio para tu condición fiscal'
        errors.update(DocumentFormat(type_document, document))
        if not ProvinceAndCityComparation(province_select, city_select):
            errors['city']              =   f'La ciudad seleccionada no pertenece a la provincia de {province_select.name_province} '
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
#=================================#=================================#=================================#=================================

#=================================
# USER REGISTER VALIDATE
#=================================
class UserRegisterValidate:
    def validate(self, attrs):
        attrs       =   UsersValidatorsMixins.validate(self, attrs)
        attrs       =   UserProfileValidatorsMixins.validate(self, attrs)
        #Policy de contraseña (AUTH_PASSWORD_VALIDATORS): igual que en reset y
        #cambio de clave. Se evalúa contra un User no persistido para el
        #validador de similitud (username/email).
        try:
            validate_password(
                attrs['password'],
                user = User(username = attrs['username'], email = attrs['email']),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

#=================================
# USER REGISTER CREATE METHOD
#=================================
class UserRegisterCreateMethod:
    def create(self, validated_data):
        return RegisterUserQuery(validated_data)