"""

Catálogo de beneficios y su valor por plan.
Los planes se matchean por name (único) contra SuscriptionPlan;
correr antes `manage.py suscriptions` para cargar los planes.

'limit' -> value numérico (None = ilimitado)
'flag'  -> enabled True/False

"""

dict_benefits = {
    'max_catalogs'      :   {'label': 'Cantidad de catálogos',              'kind': 'limit'},
    'has_public_link'   :   {'label': 'Link público del catálogo',          'kind': 'flag'},
    'has_qr'            :   {'label': 'Código QR del catálogo',             'kind': 'flag'},
    'max_products'      :   {'label': 'Cantidad máxima de productos',       'kind': 'limit'},
    'max_images'        :   {'label': 'Cantidad máxima de imágenes',        'kind': 'limit'},
    'max_storage_mb'    :   {'label': 'Almacenamiento de imágenes (MB)',    'kind': 'limit'},
    'max_gallery_images':   {'label': 'Imágenes de la galería de la web',   'kind': 'limit'},
    'has_stats'         :   {'label': 'Estadísticas de visitas',            'kind': 'flag'},
    'has_flyers'        :   {'label': 'Folletos publicitarios imprimibles', 'kind': 'flag'},
    'has_customization' :   {'label': 'Diseño web: logo, textos y contacto',    'kind': 'flag'},
    'has_location_map'  :   {'label': 'Mapa con la ubicación del negocio',      'kind': 'flag'},
    'has_design_advanced':  {'label': 'Diseño web avanzado: fuentes, color y carrusel', 'kind': 'flag'},
    'has_advanced_menu' :   {'label': 'Menú administrador avanzado',        'kind': 'flag'},
    'has_chatbot'       :   {'label': 'Chatbot con tus respuestas en la web', 'kind': 'flag'},
}

dict_plan_benefits = {
    #Plan de prueba (is_trial): se otorga solo en el registro, dura
    #SuscriptionPlan.TRIAL_DAYS y no es seleccionable ni reactivable.
    #Beneficios full Premium salvo los topes de imágenes y almacenamiento.
    'Plan de prueba':   {
        'benefits'      :   {
            'max_catalogs'      :   1,
            'has_public_link'   :   True,
            'has_qr'            :   True,
            'max_products'      :   None,
            'max_images'        :   50,
            'max_storage_mb'    :   200,
            'max_gallery_images':   15,
            'has_stats'         :   True,
            'has_flyers'        :   True,
            'has_customization' :   True,
            'has_location_map'  :   True,
            'has_design_advanced':  True,
            'has_advanced_menu' :   True,
            'has_chatbot'       :   True,
        },
        'presentation'  :   {
            'slug'          :   'prueba',
            'tagline'       :   'Probá todo gratis por 1 día',
            'cta_label'     :   'Incluido al registrarte',
            'featured'      :   False,
            'display_order' :   0,
            'bullets'       :   [
                '1 día gratis, sin tarjeta ni débito automático',
                'Todas las funciones del plan Premium',
                'Hasta 50 imágenes y 200 MB de almacenamiento',
                'Al vencer, elegí un plan para seguir publicado',
            ],
        },
    },
    'Plan basico'   :   {
        'benefits'      :   {
            'max_catalogs'      :   1,
            'has_public_link'   :   True,
            'has_qr'            :   False,
            'max_products'      :   100,
            'max_images'        :   120,
            'max_storage_mb'    :   400,
            'max_gallery_images':   2,
            'has_stats'         :   True,
            'has_flyers'        :   False,
            'has_customization' :   True,
            'has_location_map'  :   False,
            'has_design_advanced':  False,
            'has_advanced_menu' :   False,
            'has_chatbot'       :   False,
        },
        'presentation'  :   {
            'slug'          :   'basico',
            'tagline'       :   'Para empezar a vender',
            'cta_label'     :   'Elegir Básico',
            'featured'      :   False,
            'display_order' :   1,
            'bullets'       :   [
                'Tu propia web con catálogo y link público',
                'Hasta 100 productos y 120 imágenes',
                '400 MB de almacenamiento de imágenes',
                'Diseño web: logo, textos y modo oscuro',
                'Sección "Sobre nosotros" y formulario de contacto',
                'Galería de hasta 2 fotos en tu web',
                'Estadísticas de visitas de tu web',
            ],
        },
    },
    'Plan estandar' :   {
        'benefits'      :   {
            'max_catalogs'      :   1,
            'has_public_link'   :   True,
            'has_qr'            :   True,
            'max_products'      :   500,
            'max_images'        :   600,
            'max_storage_mb'    :   1024,
            'max_gallery_images':   5,
            'has_stats'         :   True,
            'has_flyers'        :   True,
            'has_customization' :   True,
            'has_location_map'  :   True,
            'has_design_advanced':  False,
            'has_advanced_menu' :   False,
            'has_chatbot'       :   False,
        },
        'presentation'  :   {
            'slug'          :   'estandar',
            'tagline'       :   'Para vender todos los días',
            'cta_label'     :   'Pasar a Estándar',
            'featured'      :   True,
            'display_order' :   2,
            'bullets'       :   [
                'Todo lo del plan Básico, y además:',
                'Hasta 500 productos y 600 imágenes',
                '1 GB de almacenamiento de imágenes',
                'Código QR de tu catálogo',
                'Galería de hasta 5 fotos en tu web',
                'Mapa con la ubicación de tu negocio en la web',
                'Folletos publicitarios listos para imprimir',
            ],
        },
    },
    'Plan premium'  :   {
        'benefits'      :   {
            'max_catalogs'      :   1,
            'has_public_link'   :   True,
            'has_qr'            :   True,
            'max_products'      :   None,
            'max_images'        :   None,
            'max_storage_mb'    :   1536,
            'max_gallery_images':   15,
            'has_stats'         :   True,
            'has_flyers'        :   True,
            'has_customization' :   True,
            'has_location_map'  :   True,
            'has_design_advanced':  True,
            'has_advanced_menu' :   True,
            'has_chatbot'       :   True,
        },
        'presentation'  :   {
            'slug'          :   'premium',
            'tagline'       :   'Para escalar tu marca',
            'cta_label'     :   'Pasar a Premium',
            'featured'      :   False,
            'display_order' :   3,
            'bullets'       :   [
                'Todo lo del plan Estándar, y además:',
                'Productos e imágenes ilimitados',
                '1.5 GB de almacenamiento de imágenes',
                'Galería de hasta 15 fotos en tu web',
                'Diseños web premium: distintas plantillas, color y fuentes',
                'Imagen de portada e imágenes decorativas en tu web',
                'Carrusel de banners en la portada',
                'Chatbot con tus respuestas para las visitas',
                'Menú administrador avanzado',
            ],
        },
    },
}
