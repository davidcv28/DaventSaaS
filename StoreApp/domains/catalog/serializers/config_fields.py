"""

Configuración de campos de los serializers del dominio Catalog.

"""
#=========================================
# CATALOG FIELDS
#=========================================
TaxonomyFields              =   {
    'name'                  :   {
        'label'             :   'Nombre',
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   2,
        'max_length'        :   60,
        'error_messages'    :   {
            'required'      :   'Tenés que escribir un nombre',
            'blank'         :   'Tenés que escribir un nombre',
            'min_length'    :   'El nombre es demasiado corto',
            'max_length'    :   'El nombre admite hasta 60 caracteres',
        },
    },
}
ProductFields               =   {
    'name'                  :   {
        'label'             :   'Nombre',
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   2,
        'max_length'        :   120,
        'error_messages'    :   {
            'required'      :   'El producto necesita un nombre',
            'blank'         :   'El producto necesita un nombre',
            'min_length'    :   'El nombre es demasiado corto',
            'max_length'    :   'El nombre admite hasta 120 caracteres',
        },
    },
    'description'           :   {
        'label'             :   'Descripción',
        'required'          :   False,
        'allow_blank'       :   True,
        'max_length'        :   600,
        'error_messages'    :   {'max_length': 'La descripción admite hasta 600 caracteres'},
    },
    'price'                 :   {
        'label'             :   'Precio',
        'required'          :   True,
        'min_value'         :   0,
        'max_digits'        :   12,
        'decimal_places'    :   2,
        'error_messages'    :   {
            'required'      :   'El producto necesita un precio',
            'min_value'     :   'El precio no puede ser negativo',
        },
    },
    'category'              :   {'required': False, 'allow_null': True},
    'brand'                 :   {'required': False, 'allow_null': True},
    'is_active'             :   {'required': False},
}
