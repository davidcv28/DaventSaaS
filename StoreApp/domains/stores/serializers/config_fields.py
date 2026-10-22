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
    'display_name'          :   {
        'label'             :   'Nombre visible',
        'style'             :   {'placeholder': 'El nombre que ven tus clientes'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   60,
        'error_messages'    :   {'max_length': 'El nombre admite hasta 60 caracteres'},
    },
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
    'about_title'           :   {
        'label'             :   'Título de la sección Sobre nosotros',
        'style'             :   {'placeholder': 'Ej. Sobre nosotros'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   80,
        'error_messages'    :   {'max_length': 'El título admite hasta 80 caracteres'},
    },
    'about_text'            :   {
        'label'             :   'Texto de la sección Sobre nosotros',
        'required'          :   False,
        'allow_blank'       :   True,
        'max_length'        :   2000,
        'error_messages'    :   {'max_length': 'El texto admite hasta 2000 caracteres'},
    },
    'show_about'            :   {
        'label'             :   'Mostrar sección Sobre nosotros',
        'required'          :   False,
    },
    'show_gallery'          :   {
        'label'             :   'Mostrar sección Galería',
        'required'          :   False,
    },
    'contact_email'         :   {
        'label'             :   'Email de contacto público',
        'style'             :   {'placeholder': 'contacto@tunegocio.com'},
        'required'          :   False,
        'allow_blank'       :   True,
    },
    'show_contact'          :   {
        'label'             :   'Mostrar sección de contacto',
        'required'          :   False,
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
    'tiktok'                :   {
        'label'             :   'TikTok',
        'style'             :   {'placeholder': 'tu.negocio'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   40,
    },
    'facebook'              :   {
        'label'             :   'Facebook',
        'style'             :   {'placeholder': 'tu.negocio'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   60,
    },
}
