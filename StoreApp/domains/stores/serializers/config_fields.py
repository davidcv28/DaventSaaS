from AdminApp.domains.suscriptions.serializers.mixins import CurrentUserProfileDefault
"""

Configuración de campos de los serializers del dominio Stores.

"""
#=========================================
# STORES FIELDS
#=========================================
StoresFields                =   {
    'user'                  :   {
        'default'           :   CurrentUserProfileDefault(),
    },
    'slug'                  :   {
        'label'             :   'Link público',
        'style'             :   {'placeholder': 'mi-negocio'},
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   3,
        'max_length'        :   60,
        'error_messages'    :   {
            'required'      :   'Tenés que elegir tu link',
            'min_length'    :   'El link es demasiado corto',
            'max_length'    :   'El link es demasiado largo'
        }
    },
    'is_published'          :   {
        'label'             :   'Link activo',
        'required'          :   False,
    },
}
#=========================================
# CUSTOMIZATION FIELDS
#=========================================
CustomizationFields           =   {
    'headline'              :   {
        'label'             :   'Titular',
        'style'             :   {'placeholder': 'Ej. Indumentaria y calzado en Salta'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   140,
        'error_messages'    :   {'max_length': 'El titular admite hasta 140 caracteres'},
    },
    'description'           :   {
        'label'             :   'Descripción',
        'style'             :   {'placeholder': 'Contale a tus clientes qué ofrecés'},
        'required'          :   False,
        'allow_blank'       :   True,
        'max_length'        :   800,
        'error_messages'    :   {'max_length': 'La descripción admite hasta 800 caracteres'},
    },
    'whatsapp'              :   {
        'label'             :   'WhatsApp',
        'style'             :   {'placeholder': '+5493871551234'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   20,
    },
    'instagram'             :   {
        'label'             :   'Instagram',
        'style'             :   {'placeholder': 'tu.negocio'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   40,
    },
}
