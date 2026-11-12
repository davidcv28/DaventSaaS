from decimal import Decimal

from django.core.management import BaseCommand, CommandError
from django.db import transaction

from StoreApp.domains.catalog.models import Brand, Category, Product
from StoreApp.domains.stores.models import Store

"""

Seed de datos ficticios para la tienda de demostración de aceitunas
"Don Humberto" (Valles Calchaquíes, Salta): identidad de marca, secciones
de marketing de la portada, página de servicios, categorías, marca y
catálogo de productos.

Idempotente: categorías, marca y productos se hacen update_or_create por
(store, name) y la personalización se sobreescribe por campo. Solo toca
la tienda indicada por --store (default 'davent').

Uso:
    manage.py seed_don_humberto --dry-run
    manage.py seed_don_humberto
    manage.py seed_don_humberto --store <slug>

"""
#=========================================
# CONFIG
#=========================================
DEFAULT_STORE       =   'davent'
BUSINESS_NAME       =   'Don Humberto'

CUSTOMIZATION       =   {
    'display_name'          :   'Don Humberto',
    'headline'              :   'Aceitunas y aceite de oliva de los Valles Calchaquíes',
    'description'           :   ('Don Humberto es una almazara familiar de Cafayate, Salta. '
                                 'Desde 1974 cultivamos Arauco y Manzanilla a 1.700 msnm: '
                                 'aceitunas en salmuera natural, aceite de oliva virgen extra '
                                 'prensado en frío el mismo día de la cosecha y una alacena de '
                                 'conservas hechas a mano en la finca. Venta por menor y mayor, '
                                 'envíos a todo el país y degustaciones guiadas en la almazara.'),
    'about_title'           :   'De la finca a tu mesa',
    'about_text'            :   ('Todo empezó con Humberto Ibazeta y doce hectáreas de olivos '
                                 'plantados a la sombra de los cerros de Cafayate. Tres '
                                 'generaciones después seguimos haciendo lo mismo: cosechar a '
                                 'mano, curar las aceitunas en salmuera de agua de vertiente y '
                                 'prensar la fruta el mismo día que se cosecha.\n\n'
                                 'No compramos aceitunas de terceros ni mezclamos cosechas: cada '
                                 'frasco y cada botella sale de nuestra propia finca, con lote y '
                                 'fecha de envasado. La almazara abre al público todos los '
                                 'sábados para degustaciones y visita guiada del olivar.'),
    'about_years'           :   50,
    'about_mission'         :   'Que la aceituna de los Valles Calchaquíes llegue a cada mesa argentina como sale de la finca: sin atajos, sin mezclas, con nombre y apellido.',
    'about_specialties'     :   'Aceitunas en salmuera natural, aceite de oliva virgen extra de cosecha propia, tapenades y conservas de la huerta',
    'contact_email'         :   'hola@donhumberto.com.ar',
    'whatsapp'              :   '+5493874123456',
    'instagram'             :   'donhumberto.olivas',
    'facebook'              :   'donhumberto.aceitunas',
    'tiktok'                :   '',
    'services_title'        :   'Lo que hacemos',
    'services'              :   [
        {'icon': 'store',       'title': 'Alacena de finca',      'text': 'Aceitunas, oliva virgen extra, tapenades y conservas envasadas en la almazara, con lote y fecha.'},
        {'icon': 'package',     'title': 'Venta mayorista',       'text': 'Baldes de 5 y 10 kg de aceitunas y oliva a granel para restaurantes, hoteles y almacenes gourmet.'},
        {'icon': 'truck',       'title': 'Envíos a todo el país', 'text': 'Despachamos por correo en 48 h; en Salta Capital entregamos en el día con cadete propio.'},
        {'icon': 'users',       'title': 'Degustaciones guiadas', 'text': 'Visitas al olivar y a la almazara todos los sábados, con cata de aceites y tabla de aceitunas.'},
    ],
    'stats'                 :   [
        {'value': '50+',  'label': 'Años de tradición olivícola'},
        {'value': '120',  'label': 'Hectáreas de olivar propio'},
        {'value': '4',    'label': 'Variedades cultivadas'},
        {'value': '300+', 'label': 'Puntos de venta en el país'},
    ],
    'benefits'              :   [
        {'icon': 'truck',        'title': 'Envío gratis',        'text': 'En compras desde $45.000 a todo el país.'},
        {'icon': 'shield-check', 'title': 'Prensado en frío',    'text': 'El oliva se extrae el mismo día de la cosecha.'},
        {'icon': 'credit-card',  'title': 'Pago seguro',         'text': 'Tarjetas, transferencia y Mercado Pago.'},
        {'icon': 'badge-check',  'title': 'Origen garantizado',  'text': 'Todo sale de nuestra finca, con lote y fecha.'},
    ],
    'timeline'              :   [
        {'label': '1974', 'text': 'Humberto Ibazeta planta las primeras doce hectáreas de olivos en Cafayate.'},
        {'label': '1992', 'text': 'La familia empieza a envasar aceitunas en salmuera para las ferias de Salta.'},
        {'label': '2010', 'text': 'Se inaugura la almazara propia: el aceite se prensa el mismo día de la cosecha.'},
        {'label': '2024', 'text': 'Don Humberto abre su tienda online y empieza a despachar a todo el país.'},
    ],
    'team'                  :   [
        {'name': 'Humberto Ibazeta',    'role': 'Fundador'},
        {'name': 'Martina Ibazeta',     'role': 'Maestra almazarera'},
        {'name': 'Rodolfo Ibazeta',     'role': 'Venta mayorista y logística'},
    ],
    'plans_title'           :   'Club Don Humberto',
    'plans'                 :   [
        {'name': 'Caja de la Alacena',  'price': '$18.000/mes',   'note': 'Para probar todo lo de la finca', 'items': ['2 frascos de aceitunas de estación', '1 tapenade o conserva sorpresa', 'Envío incluido']},
        {'name': 'Club del Oliva',      'price': '$32.000/mes',   'note': 'Para cocinar con oliva de verdad', 'items': ['1 litro de oliva virgen extra', '1 frasco de aceitunas Arauco', 'Acceso a cosechas limitadas', 'Envío incluido']},
        {'name': 'Caja Familiar',       'price': '$45.000/mes',   'note': 'La alacena completa, todos los meses', 'items': ['1 litro de oliva + infusionado', '3 frascos de aceitunas y pastas', '2 conservas de la huerta', 'Envío incluido']},
    ],
    'testimonials'          :   [
        {'name': 'Graciela Funes',      'detail': 'Salta Capital',        'text': 'Las Arauco de Don Humberto no tienen comparación: carnosas, sabrosas y sin exceso de sal. Compro todos los meses para el almacén.'},
        {'name': 'Matías Correa',       'detail': 'Chef, Tucumán',        'text': 'Uso el oliva virgen extra en el restaurante desde hace dos años. La cosecha nueva es un producto de otro nivel.'},
        {'name': 'Paula y Andrés',      'detail': 'Córdoba',              'text': 'Pedimos la caja del club y llega siempre impecable. Se nota que está hecho a mano: cada frasco trae su lote y fecha.'},
        {'name': 'José Luis Pereyra',   'detail': 'Cafayate',             'text': 'Conozco la finca desde chico. La degustación de los sábados vale el viaje: aceites, aceitunas y la vista del olivar.'},
    ],
    'faqs'                  :   [
        {'q': '¿Las aceitunas son de producción propia?', 'a': 'Sí, todo sale de nuestra finca en Cafayate: no compramos fruta de terceros ni mezclamos cosechas. Cada frasco trae lote y fecha de envasado.'},
        {'q': '¿Hacen envíos a todo el país?', 'a': 'Sí, despachamos por correo en 48 horas. En Salta Capital entregamos en el día con cadete propio y el envío es gratis desde $45.000 en todo el país.'},
        {'q': '¿Qué significa que el aceite es virgen extra?', 'a': 'Que se obtiene solo por prensado en frío de aceitunas sanas, sin procesos químicos ni refinado, con acidez menor a 0,8°. El nuestro se prensa el mismo día de la cosecha.'},
        {'q': '¿Venden por mayor a restaurantes?', 'a': 'Sí: baldes de 5 y 10 kg de aceitunas y oliva a granel con precio mayorista. Escribinos por WhatsApp y te pasamos la lista.'},
        {'q': '¿Se puede visitar la almazara?', 'a': 'Sí, todos los sábados hacemos visita guiada del olivar y degustación con tabla de aceitunas y cata de aceites. Se reserva por WhatsApp.'},
        {'q': '¿Cómo conservo las aceitunas una vez abiertas?', 'a': 'Siempre en heladera, cubiertas por su salmuera. Así duran hasta 60 días sin perder textura ni sabor.'},
    ],
    'hours'                 :   [
        {'label': 'Lunes a viernes',  'value': '9 a 18 h'},
        {'label': 'Sábados',          'value': '9 a 13 h y degustación 16 h'},
        {'label': 'Domingos',         'value': 'Cerrado'},
    ],
    'announcements'         :   [
        {'icon': 'truck', 'text': 'Envío gratis desde $45.000 a todo el país'},
        {'icon': 'star',  'text': 'Cosecha 2025 ya disponible: oliva virgen extra recién prensado'},
        {'icon': 'users', 'text': 'Degustaciones en la almazara todos los sábados'},
    ],
    'service_steps'         :   [
        {'icon': 'message-circle', 'title': 'Escribinos por WhatsApp', 'text': 'Contanos qué necesitás: menor, mayorista o caja del club.'},
        {'icon': 'check',          'title': 'Coordinamos el pedido',   'text': 'Te confirmamos stock, precio final y forma de pago en el día.'},
        {'icon': 'truck',          'title': 'Despachamos o entregamos','text': 'Correo a todo el país en 48 h o cadete en Salta Capital en el día.'},
    ],
    'service_days'          :   ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
    'service_slots'         :   ['9 a 13 h', '14 a 18 h'],
    'service_ask_address'   :   True,
    'service_price_note'    :   'Precios mayoristas según volumen: pasanos la lista y te cotizamos.',
    'service_pay_note'      :   'Aceptamos transferencia, tarjetas y Mercado Pago.',
    'cta_title'             :   'Llevá la finca a tu mesa',
    'cta_text'              :   'Pedí aceitunas, oliva virgen extra y conservas de Don Humberto por WhatsApp o recorré el catálogo completo.',
    'cta_label'             :   'Hacer un pedido',
    'catalog_note'          :   'Todo sale de nuestra finca en Cafayate: cada frasco y botella trae lote y fecha de envasado.',
    'footer_text'           :   'Don Humberto — almazara familiar de los Valles Calchaquíes desde 1974.',
    'show_about'            :   True, 'show_contact'      : True, 'show_services': True,
    'show_stats'            :   True, 'show_testimonials' : True, 'show_faq'     : True,
    'show_hours'            :   True, 'show_cta'          : True, 'show_benefits': True,
    'show_timeline'         :   True, 'show_team'         : True, 'show_plans'   : True,
    'show_announcements'    :   True, 'show_highlights'   : True,
}

CATEGORIES            =   [
    ('Aceitunas',           ['Variedad', 'Envase', 'Curado']),
    ('Aceites de oliva',    ['Variedad', 'Acidez', 'Envase']),
    ('Tapenades y pastas',  ['Ingredientes', 'Envase']),
    ('Conservas de finca',  ['Ingredientes', 'Envase']),
]
BRAND                   =   'Don Humberto'

#(nombre, categoría, precio, offer_price, stock, descripción, features)
PRODUCTS              =   [
    ('Aceitunas negras Arauco en salmuera 500 g', 'Aceitunas', 8500,  None,  None,
     'La variedad criolla por excelencia, curada en salmuera de agua de vertiente durante 12 meses. Carnosa, intensa, de sal justa.',
     ['Variedad Arauco de cosecha propia', 'Salmuera natural, sin conservantes', 'Frasco de vidrio 500 g']),
    ('Aceitunas verdes Manzanilla rellenas de morrón 350 g', 'Aceitunas', 6900,  5900, None,
     'Manzanilla deshuesada a mano y rellena con morrón asado de la huerta. El clásico de la picada.',
     ['Variedad Manzanilla', 'Relleno de morrón asado', 'Frasco de vidrio 350 g']),
    ('Aceitunas verdes aliñadas a la criolla 500 g', 'Aceitunas', 7200,  None,  None,
     'Verdes crocantes marinadas en oliva con ajo, laurel, ají molido y orégano de la finca.',
     ['Aliño criollo de la casa', 'Con ajo, laurel y ají molido', 'Frasco de vidrio 500 g']),
    ('Mix de aceitunas de la casa 500 g', 'Aceitunas', 7900,  None,  8,
     'Arauco negra, Manzanilla verde y verdes aliñadas en un solo frasco. Ideal para picadas y regalos.',
     ['Tres variedades en un frasco', 'Curado natural en salmuera', 'Frasco de vidrio 500 g']),
    ('Aceite de oliva virgen extra Cosecha 2025 — 500 ml', 'Aceites de oliva', 18500, None, None,
     'Primer prensado en frío de la cosecha 2025. Frutado verde con picor final, acidez 0,3°.',
     ['Prensado el mismo día de la cosecha', 'Acidez 0,3°, blend Arauco y Coratina', 'Botella 500 ml vidrio oscuro']),
    ('Aceite de oliva virgen extra Arauco 1 L', 'Aceites de oliva', 32900, 29900, None,
     'Varietal Arauco de perfil suave y dulzón: el oliva de todos los días, con el análisis de laboratorio de cada lote.',
     ['Monovarietal Arauco', 'Acidez menor a 0,4°', 'Botella 1 L vidrio oscuro']),
    ('Aceite de oliva infusionado Ajo y Ají 250 ml', 'Aceites de oliva', 14800, None, None,
     'Virgen extra infusionado en frío con ajo y ají de la huerta. Para dips, pizzas y marinadas.',
     ['Infusión en frío, sin esencias', 'Picor medio', 'Botella 250 ml vidrio oscuro']),
    ('Aceite de oliva infusionado Romero 250 ml', 'Aceites de oliva', 14800, None, None,
     'Virgen extra infusionado con romero fresco de la finca. Va con pan, papas y carnes al horno.',
     ['Infusión en frío, sin esencias', 'Romero de la finca', 'Botella 250 ml vidrio oscuro']),
    ('Tapenade de aceitunas negras 190 g', 'Tapenades y pastas', 9600, None, None,
     'Pasta rústica de Arauco negra con alcaparras, anchoa y nuestro oliva. Para untar o saltear pastas.',
     ['Aceituna Arauco de la finca', 'Con alcaparras y anchoa', 'Frasco de vidrio 190 g']),
    ('Pasta de aceitunas verdes y alcaparras 190 g', 'Tapenades y pastas', 9600, None, None,
     'Verdes molidas gruesas con alcaparras y un toque de limón. La tapenade fresca de la casa.',
     ['Aceituna verde Manzanilla', 'Con alcaparras y limón', 'Frasco de vidrio 190 g']),
    ('Tomates secos en aceite de oliva 220 g', 'Conservas de finca', 11200, None, None,
     'Tomates secados al sol de Cafayate y conservados en virgen extra con ajo y orégano.',
     ['Secado al sol', 'Cubierto en oliva virgen extra', 'Frasco de vidrio 220 g']),
    ('Berenjenas al escabeche 300 g', 'Conservas de finca', 8900, None, 5,
     'Berenjenas de la huerta en escabeche suave de vinagre de vino, ajo y ají molido.',
     ['Receta de la casa', 'Escabeche suave', 'Frasco de vidrio 300 g']),
    ('Ajos confitados en oliva 200 g', 'Conservas de finca', 9800, None, None,
     'Dientes de ajo cocidos a fuego lento en oliva hasta quedar cremosos. El aceite del frasco se usa entero.',
     ['Cocción lenta en oliva', 'Sabor dulce, sin picor', 'Frasco de vidrio 200 g']),
]
#=========================================
# COMMAND
#=========================================
class Command(BaseCommand):
    help    =   'Carga datos ficticios de la marca de aceitunas "Don Humberto" en una tienda.'

    def add_arguments(self, parser):
        parser.add_argument('--store', default = DEFAULT_STORE, help = f'Slug de la tienda (default: {DEFAULT_STORE})')
        parser.add_argument('--dry-run', action = 'store_true', help = 'Muestra el plan sin escribir')

    def handle(self, *args, **options):
        store           =   Store.objects.select_related('user', 'customization').filter(slug = options['store']).first()
        if store is None:
            raise CommandError(f'No existe la tienda "{options["store"]}".')
        profile         =   store.user
        customization   =   getattr(store, 'customization', None)
        if customization is None:
            raise CommandError(f'La tienda "{options["store"]}" no tiene StoreCustomization.')

        self.stdout.write(f'Tienda: {store.slug}')
        self.stdout.write(f'  business_name: {profile.business_name!r} -> {BUSINESS_NAME!r}')
        self.stdout.write(f'  customization: {len(CUSTOMIZATION)} campo(s) a escribir (display_name={CUSTOMIZATION["display_name"]!r})')
        self.stdout.write(f'  categorías: {[name for name, _ in CATEGORIES]}')
        self.stdout.write(f'  marca: {BRAND!r}')
        for name, category, price, offer_price, stock, _desc, _features in PRODUCTS:
            offer   =   f' (oferta {offer_price})' if offer_price else ''
            stock_s =   f' stock={stock}' if stock is not None else ''
            self.stdout.write(f'  producto: {name} — ${price}{offer}{stock_s} [{category}]')
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('[dry-run] No se escribió nada.'))
            return

        with transaction.atomic():
            profile.business_name   =   BUSINESS_NAME
            profile.save(update_fields = ['business_name'])
            for field, value in CUSTOMIZATION.items():
                setattr(customization, field, value)
            customization.save()
            categories  =   {}
            for position, (name, schema) in enumerate(CATEGORIES):
                categories[name], _   =   Category.objects.update_or_create(
                    store = store, name = name,
                    defaults = {'feature_schema': schema, 'position': position},
                )
            brand, _    =   Brand.objects.update_or_create(
                store = store, name = BRAND, defaults = {'position': 0},
            )
            for name, category_name, price, offer_price, stock, description, features in PRODUCTS:
                Product.objects.update_or_create(
                    store = store, name = name,
                    defaults = {
                        'category'    :   categories[category_name],
                        'brand'       :   brand,
                        'price'       :   Decimal(str(price)),
                        'offer_price' :   Decimal(str(offer_price)) if offer_price else None,
                        'stock'       :   stock,
                        'description' :   description,
                        'features'    :   features,
                        'is_active'   :   True,
                    },
                )
        self.stdout.write(self.style.SUCCESS(
            f'{store.slug}: Don Humberto cargado — {len(CATEGORIES)} categorías, '
            f'1 marca, {len(PRODUCTS)} productos, {len(CUSTOMIZATION)} campos de personalización.'
        ))
