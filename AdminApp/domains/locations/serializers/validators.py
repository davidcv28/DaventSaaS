from rest_framework import serializers
"""
Validadores personalizados para los serializers del dominio Locations.
Contiene validaciones de unicidad amigables antes de persistir.
"""


def validate_province_name(value):
    name_val = value.strip().upper()
    errors = []
    if len(name_val) < 3:
        errors.append('Nombre de provincia demasiado corto')
    if len(name_val) > 150:
        errors.append('Nombre de provincia demasiado largo')
    if errors:
        raise serializers.ValidationError(errors)
    return name_val


def validate_city_name(value):
    name_val = value.strip().upper()
    errors = []
    if len(name_val) < 2:
        errors.append('Nombre de ciudad demasiado corto')
    if len(name_val) > 150:
        errors.append('Nombre de ciudad demasiado largo')
    if errors:
        raise serializers.ValidationError(errors)
    return name_val


LocationValidators = {
    'province_name': validate_province_name,
    'city_name': validate_city_name,
}

