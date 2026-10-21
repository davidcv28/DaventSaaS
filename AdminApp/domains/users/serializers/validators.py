from rest_framework import serializers
import re
"""
Validadores personalizados para los serializers del dominio Users.

Contiene validaciones de contrasena, telefono, documento y condicion fiscal,
aplicadas sobre los campos antes de persistir los datos.
"""

#===============================
# USER VALIDATORS
#===============================
def validate_password(value):
    password_val    =   value
    errors          =   []
    if not re.search(r'[a-z]', password_val):
        errors.append('La contrasena debe contener al menos una letra minuscula')
    if not re.search(r'[A-Z]', password_val):
        errors.append('La contrasena debe contener al menos una letra mayuscula')
    if not re.search(r'[0-9]', password_val):
        errors.append('La contrasena debe contener al menos un numero')
    if not re.search(r'[^a-zA-Z0-9]', password_val):
        errors.append('La contrasena debe tener al menos un caracter especial')
    if errors:
        raise serializers.ValidationError(errors)
    return password_val

#===============================
# TERMS AND CONDITIONS VALIDATOR
#===============================
def validate_accept_terms(value):
    if value is not True:
        raise serializers.ValidationError(
            'Debés aceptar los Términos y condiciones para crear tu cuenta'
        )
    return value

UserValidators      =   {
    'password'      :   validate_password,
    'accept_terms'  :   validate_accept_terms
}

#===============================
# USER PASSWORD VALIDATORS
#===============================
def validate_new_password(value):
    password_val    =   value
    errors          =   []
    if not re.search(r'[a-z]', password_val):
        errors.append('La contrasena debe contener al menos una letra minuscula')
    if not re.search(r'[A-Z]', password_val):
        errors.append('La contrasena debe contener al menos una letra mayuscula')
    if not re.search(r'[0-9]', password_val):
        errors.append('La contrasena debe contener al menos un numero')
    if not re.search(r'[^a-zA-Z0-9]', password_val):
        errors.append('La contrasena debe tener al menos un caracter especial')
    if errors:
        raise serializers.ValidationError(errors)
    return password_val

UserPasswordValidators      =   {
    'new_password'      :   validate_new_password
}

#===============================
# USER PROFILE VALIDATORS
#===============================
def validate_business_name(value):
    bussines_name_val   =   value.strip().upper()
    errors              =   []
    if len(bussines_name_val) < 3:
        errors.append('Nombre comercial demasiado corto')
    if len(bussines_name_val) > 255:
        errors.append('Nombre comercial demasiado largo')
    if not re.match(r'^[a-zA-Z0-9\s,.\-&]+$', bussines_name_val):
        errors.append('El nombre comercial contiene caracteres no validos')
    if errors:
        raise serializers.ValidationError(errors)
    return bussines_name_val
def validate_first_name(value):
    name_val    =   value.strip().upper()
    errors      =   []
    if re.search(r'[^a-zA-Z\sñÑáéíóúÁÉÍÓÚ]', name_val):
        errors.append('En este campo solo se aceptan letras')
    if errors:
        raise serializers.ValidationError(errors)
    return name_val
def validate_last_name(value):
    last_name_val    =   value.strip().upper()
    errors      =   []
    if re.search(r'[^a-zA-Z\sñÑáéíóúÁÉÍÓÚ]', last_name_val):
        errors.append('En este campo solo se aceptan letras')
    if errors:
        raise serializers.ValidationError(errors)
    return last_name_val
def validate_phone(value):
    phone_val   =   value.strip()
    if not re.match(r'^\+54\d{10,13}$', phone_val):
        raise serializers.ValidationError(
            'Ingresa un numero valido en formato internacional. Ej. +5493871551234'
        )
    return phone_val

UserProfileValidators   =   {
    'business_name' :   validate_business_name,
    'phone'         :   validate_phone,
}