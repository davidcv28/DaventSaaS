import re

from rest_framework import serializers

"""
Validadores personalizados para los serializers del dominio Legal.

Contiene validaciones de datos del denunciante, URL denunciada, descripción
y declaración de buena fe aplicadas antes de persistir la denuncia.
"""

#===============================
# CONTENT REPORT VALIDATORS
#===============================
def validate_reporter_name(value):
    name_val    =   value.strip()
    errors      =   []
    if len(name_val) < 3:
        errors.append('El nombre del denunciante es demasiado corto')
    if re.search(r'[^a-zA-Z\sñÑáéíóúÁÉÍÓÚ]', name_val):
        errors.append('En este campo solo se aceptan letras')
    if errors:
        raise serializers.ValidationError(errors)
    return name_val

def validate_reported_url(value):
    url_val     =   value.strip()
    if not re.match(r'^https?://', url_val):
        raise serializers.ValidationError(
            'La URL del contenido debe comenzar con http:// o https://'
        )
    return url_val

def validate_description(value):
    description_val     =   value.strip()
    if len(description_val) < 20:
        raise serializers.ValidationError(
            'La descripción debe tener al menos 20 caracteres'
        )
    return description_val

def validate_good_faith(value):
    if value is not True:
        raise serializers.ValidationError(
            'Debés declarar de buena fe que la información de la denuncia es veraz'
        )
    return value

LegalValidators     =   {
    'reporter_name' :   validate_reporter_name,
    'reported_url'  :   validate_reported_url,
    'description'   :   validate_description,
    'good_faith'    :   validate_good_faith,
}
