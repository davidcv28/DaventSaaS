from AdminApp.domains.locations.models import Province, ZipCode
from .validators import LocationValidators
"""
Módulo de configuración de campos para los serializers del dominio Locations.
Define diccionarios reutilizables listos para desempaquetar con ** en el serializer.
"""
#==============================
# LOCATION FIELDS CONFIG
#==============================
LocationFieldsConfig = {
    'province_name': {
        'label': 'Provincia',
        'style': {'placeholder': 'Ej. Salta'},
        'required': True,
        'trim_whitespace': True,
        'min_length': 3,
        'max_length': 150,
        'validators': [LocationValidators['province_name']],
        'error_messages': {
            'required': 'Este campo es obligatorio',
            'min_length': 'Nombre de provincia demasiado corto',
            'max_length': 'Nombre de provincia demasiado largo',
        },
    },
    'city_name': {
        'label': 'Ciudad',
        'style': {'placeholder': 'Ej. Salta Capital'},
        'required': True,
        'trim_whitespace': True,
        'min_length': 2,
        'max_length': 150,
        'validators': [LocationValidators['city_name']],
        'error_messages': {
            'required': 'Este campo es obligatorio',
        },
    },
    'zipcode': {
        'label': 'Código postal',
        'style': {'placeholder': 'Ej. 4400'},
        'required': True,
        'trim_whitespace': True,
        'min_length': 4,
        'max_length': 4,
        'error_messages': {
            'required': 'Este campo es obligatorio',
        },
    },
    'province': {
        'label': 'Provincia',
        'queryset': Province.objects.all(),
    },
    'zipcode_rel': {
        'label': 'Código postal',
        'queryset': ZipCode.objects.all(),
    },
}

