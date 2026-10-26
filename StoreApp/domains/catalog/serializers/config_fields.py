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
    'feature_schema'        :   {'required': False},
}
#=========================================
# FEATURE LIMITS (espejo en frontend/src/api/catalog.api.js)
#=========================================
FeatureLimits               =   {
    'schema_max'            :   15,   # máx. atributos en la plantilla de la categoría
    'schema_name_max'       :   40,   # largo máx. del nombre del atributo
    'entries_max'           :   20,   # máx. pares nombre/valor por producto
    'name_max'              :   40,   # largo máx. de la clave
    'value_max'             :   120,  # largo máx. del valor
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
    'offer_price'           :   {
        'label'             :   'Precio de oferta',
        'required'          :   False,
        'allow_null'        :   True,
        'min_value'         :   0,
        'max_digits'        :   12,
        'decimal_places'    :   2,
        'error_messages'    :   {
            'min_value'     :   'La oferta no puede ser negativa',
        },
    },
    'category'              :   {'required': False, 'allow_null': True},
    'brand'                 :   {'required': False, 'allow_null': True},
    'is_active'             :   {'required': False},
    'features'              :   {'required': False},
}
#=========================================
# DISCOUNT FIELDS (espejo en frontend/src/api/catalog.api.js)
#=========================================
DiscountLimits              =   {
    'percent_min'           :   1,
    'percent_max'           :   99,
    'products_max'          :   500,  # tope defensivo de la selección manual
}
DiscountFields              =   {
    'name'                  :   {
        'label'             :   'Nombre',
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   2,
        'max_length'        :   60,
        'error_messages'    :   {
            'required'      :   'El descuento necesita un nombre',
            'blank'         :   'El descuento necesita un nombre',
            'min_length'    :   'El nombre es demasiado corto',
            'max_length'    :   'El nombre admite hasta 60 caracteres',
        },
    },
    'percent'               :   {
        'label'             :   'Descuento (%)',
        'required'          :   True,
        'min_value'         :   DiscountLimits['percent_min'],
        'max_value'         :   DiscountLimits['percent_max'],
        #Los % del mensaje van escapados (%%): DRF interpola error.message
        #% params y un % suelto rompe el formateo con ValueError.
        'error_messages'    :   {
            'required'      :   'Indicá el porcentaje de descuento',
            'min_value'     :   'El descuento mínimo es 1%%',
            'max_value'     :   'El descuento máximo es 99%%',
        },
    },
    'starts_at'             :   {
        'label'             :   'Empieza',
        'required'          :   True,
        'error_messages'    :   {
            'required'      :   'Indicá cuándo empieza el descuento',
            'invalid'       :   'La fecha de inicio no es válida',
        },
    },
    'ends_at'               :   {
        'label'             :   'Termina',
        'required'          :   False,
        'allow_null'        :   True,
        'error_messages'    :   {'invalid': 'La fecha de fin no es válida'},
    },
    'is_active'             :   {'required': False},
    'category'              :   {'required': False, 'allow_null': True},
    'brand'                 :   {'required': False, 'allow_null': True},
}
#=========================================
# REVIEW FIELDS (opiniones de visitantes, formulario público)
#=========================================
ReviewLimits              =   {
    'text_max'              :   600,
    'list_max'              :   50,   # reseñas que viajan en la ficha pública
}
ReviewFields              =   {
    'is_positive'           :   {
        'label'             :   'Valoración',
        'required'          :   False,
        'allow_null'        :   True,
        'error_messages'    :   {'invalid': 'Indicá si te gustó o no'},
    },
    'text'                  :   {
        'label'             :   'Comentario',
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   ReviewLimits['text_max'],
        'error_messages'    :   {'max_length': 'El comentario admite hasta 600 caracteres'},
    },
    'name'                  :   {
        'label'             :   'Nombre',
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   2,
        'max_length'        :   80,
        'error_messages'    :   {
            'required'      :   'Contanos tu nombre',
            'blank'         :   'Contanos tu nombre',
            'min_length'    :   'El nombre es demasiado corto',
            'max_length'    :   'El nombre admite hasta 80 caracteres',
        },
    },
    'surname'               :   {
        'label'             :   'Apellido',
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   2,
        'max_length'        :   80,
        'error_messages'    :   {
            'required'      :   'Contanos tu apellido',
            'blank'         :   'Contanos tu apellido',
            'min_length'    :   'El apellido es demasiado corto',
            'max_length'    :   'El apellido admite hasta 80 caracteres',
        },
    },
    'email'                 :   {
        'label'             :   'Email',
        'required'          :   True,
        'error_messages'    :   {
            'required'      :   'Contanos tu email',
            'blank'         :   'Contanos tu email',
            'invalid'       :   'Ingresá un email válido',
        },
    },
}
