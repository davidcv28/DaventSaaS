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
    'about_years'           :   {
        'label'             :   'Años de trayectoria',
        'required'          :   False,
        'allow_null'        :   True,
        'min_value'         :   0,
        'max_value'         :   150,
        'error_messages'    :   {'min_value': 'Los años no pueden ser negativos', 'max_value': 'Los años admiten hasta 150'},
    },
    'about_mission'         :   {
        'label'             :   'Misión',
        'required'          :   False,
        'allow_blank'       :   True,
        'max_length'        :   400,
        'error_messages'    :   {'max_length': 'La misión admite hasta 400 caracteres'},
    },
    'about_specialties'     :   {
        'label'             :   'Especialidades',
        'style'             :   {'placeholder': 'Ej. Venta mayorista, Envíos, Atención personalizada'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   300,
        'error_messages'    :   {'max_length': 'Las especialidades admiten hasta 300 caracteres'},
    },
    'show_about'            :   {
        'label'             :   'Mostrar sección Sobre nosotros',
        'required'          :   False,
    },
    #===== Páginas de la web + página "Servicios" =====
    'site_templates'        :   {
        'label'             :   'Páginas de tu web',
        'required'          :   False,
    },
    'service_steps'         :   {
        'label'             :   'Pasos de cómo funciona',
        'required'          :   False,
    },
    'service_days'          :   {
        'label'             :   'Días de atención',
        'required'          :   False,
    },
    'service_slots'         :   {
        'label'             :   'Franjas horarias',
        'required'          :   False,
    },
    'service_ask_address'   :   {
        'label'             :   'Pedir dirección en el pedido',
        'required'          :   False,
    },
    'service_price_note'    :   {
        'label'             :   'Nota de precios orientativos',
        'style'             :   {'placeholder': 'Ej. Los precios son orientativos: el valor final se confirma al ver el trabajo'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   160,
        'error_messages'    :   {'max_length': 'La nota admite hasta 160 caracteres'},
    },
    'service_pay_note'      :   {
        'label'             :   'Nota de pago en persona',
        'style'             :   {'placeholder': 'Ej. Se paga al recibir: efectivo, débito o transferencia'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   160,
        'error_messages'    :   {'max_length': 'La nota admite hasta 160 caracteres'},
    },
    #===== Secciones de marketing ("Mi empresa") =====
    'services'              :   {
        'label'             :   'Qué ofrecemos',
        'required'          :   False,
    },
    'services_title'        :   {
        'label'             :   'Título de la sección Qué ofrecemos',
        'style'             :   {'placeholder': 'Ej. Qué ofrecemos'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   80,
        'error_messages'    :   {'max_length': 'El título admite hasta 80 caracteres'},
    },
    'stats'                 :   {
        'label'             :   'Números del negocio',
        'required'          :   False,
    },
    'testimonials'          :   {
        'label'             :   'Testimonios',
        'required'          :   False,
    },
    'testimonials_title'    :   {
        'label'             :   'Título de la sección Testimonios',
        'style'             :   {'placeholder': 'Ej. Lo que dicen nuestros clientes'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   80,
        'error_messages'    :   {'max_length': 'El título admite hasta 80 caracteres'},
    },
    'faqs'                  :   {
        'label'             :   'Preguntas frecuentes',
        'required'          :   False,
    },
    'faqs_title'            :   {
        'label'             :   'Título de la sección Preguntas frecuentes',
        'style'             :   {'placeholder': 'Ej. Preguntas frecuentes'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   80,
        'error_messages'    :   {'max_length': 'El título admite hasta 80 caracteres'},
    },
    'hours'                 :   {
        'label'             :   'Horarios de atención',
        'required'          :   False,
    },
    'cta_title'             :   {
        'label'             :   'Título del llamado a la acción',
        'style'             :   {'placeholder': 'Ej. ¿Listo para hacer tu pedido?'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   120,
        'error_messages'    :   {'max_length': 'El título admite hasta 120 caracteres'},
    },
    'cta_text'              :   {
        'label'             :   'Texto del llamado a la acción',
        'style'             :   {'placeholder': 'Ej. Escribinos y te armamos el pedido en el día'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   280,
        'error_messages'    :   {'max_length': 'El texto admite hasta 280 caracteres'},
    },
    'cta_label'             :   {
        'label'             :   'Texto del botón',
        'style'             :   {'placeholder': 'Ej. Escribinos por WhatsApp'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   40,
        'error_messages'    :   {'max_length': 'El texto del botón admite hasta 40 caracteres'},
    },
    'section_order'         :   {
        'label'             :   'Orden de las secciones de la portada',
        'required'          :   False,
    },
    'benefits'              :   {
        'label'             :   'Garantías y beneficios',
        'required'          :   False,
    },
    'timeline'              :   {
        'label'             :   'Hitos del negocio',
        'required'          :   False,
    },
    'team'                  :   {
        'label'             :   'Equipo',
        'required'          :   False,
    },
    'announcements'         :   {
        'label'             :   'Cinta de anuncios',
        'required'          :   False,
    },
    'video_url'             :   {
        'label'             :   'Video de la portada',
        'style'             :   {'placeholder': 'Link de YouTube o Vimeo'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   300,
        'error_messages'    :   {'max_length': 'El link del video admite hasta 300 caracteres'},
    },
    'video_title'           :   {
        'label'             :   'Título de la sección Video',
        'style'             :   {'placeholder': 'Ej. Mirá nuestro local en video'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   80,
        'error_messages'    :   {'max_length': 'El título admite hasta 80 caracteres'},
    },
    'catalog_note'          :   {
        'label'             :   'Aviso en el catálogo',
        'style'             :   {'placeholder': 'Ej. Envíos gratis superando $80.000'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   160,
        'error_messages'    :   {'max_length': 'El aviso admite hasta 160 caracteres'},
    },
    'footer_text'           :   {
        'label'             :   'Texto del pie',
        'style'             :   {'placeholder': 'Ej. Tienda familiar desde 1998'},
        'required'          :   False,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True,
        'max_length'        :   160,
        'error_messages'    :   {'max_length': 'El texto del pie admite hasta 160 caracteres'},
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
