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
    'max_storage_mb'    :   {'label': 'Almacenamiento de imágenes (MB)',    'kind': 'limit'},
    'has_stats'         :   {'label': 'Estadísticas de visitas',            'kind': 'flag'},
    'has_flyers'        :   {'label': 'Folletos publicitarios imprimibles', 'kind': 'flag'},
    'has_customization' :   {'label': 'Personalización web y logo',         'kind': 'flag'},
    'has_advanced_menu' :   {'label': 'Menú administrador avanzado',        'kind': 'flag'},
}

dict_plan_benefits = {
    'Plan basico'   :   {
        'benefits'      :   {
            'max_catalogs'      :   1,
            'has_public_link'   :   True,
            'has_qr'            :   False,
            'max_products'      :   100,
            'max_storage_mb'    :   400,
            'has_stats'         :   False,
            'has_flyers'        :   False,
            'has_customization' :   False,
            'has_advanced_menu' :   False,
        },
        'presentation'  :   {
            'slug'          :   'basico',
            'tagline'       :   'Para empezar a vender',
            'cta_label'     :   'Elegir Básico',
            'featured'      :   False,
            'display_order' :   1,
            'bullets'       :   [
                '1 catálogo con link público',
                'Hasta 100 productos',
                '400 MB de almacenamiento de imágenes',
            ],
        },
    },
    'Plan estandar' :   {
        'benefits'      :   {
            'max_catalogs'      :   1,
            'has_public_link'   :   True,
            'has_qr'            :   True,
            'max_products'      :   500,
            'max_storage_mb'    :   1024,
            'has_stats'         :   True,
            'has_flyers'        :   True,
            'has_customization' :   False,
            'has_advanced_menu' :   False,
        },
        'presentation'  :   {
            'slug'          :   'estandar',
            'tagline'       :   'Para vender todos los días',
            'cta_label'     :   'Pasar a Estándar',
            'featured'      :   True,
            'display_order' :   2,
            'bullets'       :   [
                '1 catálogo con link público + QR',
                'Hasta 500 productos',
                '1 GB de almacenamiento de imágenes',
                'Estadísticas de visitas',
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
            'max_storage_mb'    :   1536,
            'has_stats'         :   True,
            'has_flyers'        :   True,
            'has_customization' :   True,
            'has_advanced_menu' :   True,
        },
        'presentation'  :   {
            'slug'          :   'premium',
            'tagline'       :   'Para escalar tu marca',
            'cta_label'     :   'Pasar a Premium',
            'featured'      :   False,
            'display_order' :   3,
            'bullets'       :   [
                '1 catálogo con link público + QR',
                'Productos ilimitados',
                '1.5 GB de almacenamiento de imágenes',
                'Estadísticas de visitas',
                'Folletos publicitarios listos para imprimir',
                'Personalización web y logo',
                'Menú administrador avanzado',
            ],
        },
    },
}
