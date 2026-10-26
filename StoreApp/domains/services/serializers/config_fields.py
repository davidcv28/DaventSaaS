from StoreApp.domains.services.models import StoreService
"""

Configuración de campos de los serializers del dominio Services.
Espejo en frontend/src/api/services.api.js (SERVICE_LIMITS).

"""
#=========================================
# SERVICE FIELDS (ítem de la página Servicios del dueño)
#=========================================
ServiceFields               =   {
    'name'                  :   {
        'label'             :   'Nombre',
        'style'             :   {'placeholder': 'Ej. Limpieza a domicilio'},
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   2,
        'max_length'        :   StoreService.NAME_MAX,
        'error_messages'    :   {
            'required'      :   'El servicio necesita un nombre',
            'blank'         :   'El servicio necesita un nombre',
            'min_length'    :   'El nombre es demasiado corto',
            'max_length'    :   f'El nombre admite hasta {StoreService.NAME_MAX} caracteres',
        },
    },
    'description'           :   {
        'label'             :   'Descripción',
        'style'             :   {'placeholder': 'Ej. Incluye materiales y retiro del pedido'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   StoreService.DESCRIPTION_MAX,
        'error_messages'    :   {'max_length': f'La descripción admite hasta {StoreService.DESCRIPTION_MAX} caracteres'},
    },
    'price'                 :   {
        'label'             :   'Precio orientativo',
        'required'          :   False,
        'allow_null'        :   True,
        'min_value'         :   0,
        'max_digits'        :   12,
        'decimal_places'    :   2,
        'error_messages'    :   {
            'min_value'     :   'El precio no puede ser negativo',
            'invalid'       :   'Ingresá un precio válido',
        },
    },
    'duration'              :   {
        'label'             :   'Duración estimada',
        'style'             :   {'placeholder': 'Ej. ≈ 45 min'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   StoreService.DURATION_MAX,
        'error_messages'    :   {'max_length': f'La duración admite hasta {StoreService.DURATION_MAX} caracteres'},
    },
    'icon'                  :   {
        'label'             :   'Icono',
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   30,
    },
    'is_active'             :   {'required': False},
}
