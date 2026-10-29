#=========================================
# TEXTO DEL DISEÑO AUTOMÁTICO (sin LLM)
#=========================================
#Frases armadas con plantillas por rubro y tono, interpolando datos REALES
#del negocio (nombre, ciudad, especialidades, años, servicios, categorías).
#Si el dato falta no se inventa nada: se usa la frase neutra del rubro, y
#así el texto sigue siendo cierto. Respeta los max_length del modelo —
#recortar acá evita que el serializer rechace el borrador.

from . import ai_design_recipes as R

_HEADLINE_MAX               =   140
_DESCRIPTION_MAX            =   800
_CTA_TITLE_MAX              =   120
_CTA_TEXT_MAX               =   280
_CTA_LABEL_MAX              =   40
#Topes de los campos de negocio que rellena el autofill. Espejo de
#StoreCustomization (los importa el motor para no duplicar números acá).
_ABOUT_MAX                  =   2000
_MISSION_MAX                =   400
_FAQ_Q_MAX                  =   140
_FAQ_A_MAX                  =   500
_SERVICE_NAME_MAX           =   60
_SERVICE_DESC_MAX           =   160
_STEP_TITLE_MAX             =   60
_STEP_DESC_MAX              =   160
_ANNOUNCEMENT_MAX           =   60

#Cómo nombra cada rubro lo que vende: es la palabra que ordena casi todas
#las frases (evita decir "productos" en una peluquería).
RUBRO_COPY                  =   {
    'comercio': {
        'what': 'productos', 'place': 'tu tienda',
        'headlines': ('{name}: lo que buscás, cerca{place}', 'Tu tienda de confianza{place}', '{name}{place}'),
        'service_line': 'Tenemos {what} para todos los días{services}.',
        'cta_label': 'Ver el catálogo', 'cta_title': 'Llevate lo que necesitás hoy',
        'cta_text': 'Mirá el catálogo completo y coordinamos la entrega o el retiro.',
    },
    'gastronomia': {
        'what': 'platos', 'place': 'nuestra cocina',
        'headlines': ('{name}: cocina de verdad{place}', 'Comé rico{place}', '{name}{place}'),
        'service_line': 'Cocinamos {what} con materia prima fresca{services}.',
        'cta_label': 'Ver la carta', 'cta_title': 'Reservá tu mesa o pedí para llevar',
        'cta_text': 'Escribinos y te confirmamos disponibilidad, horarios y opciones del día.',
    },
    'indumentaria': {
        'what': 'prendas', 'place': 'nuestra colección',
        'headlines': ('{name}: nueva temporada{place}', 'Estilo que se nota{place}', '{name}{place}'),
        'service_line': 'Seleccionamos {what} para que te sienten bien{services}.',
        'cta_label': 'Ver la colección', 'cta_title': 'Encontrá tu próximo look',
        'cta_text': 'Mirá la colección disponible y consultanos por talles, colores y envíos.',
    },
    'servicios_profesionales': {
        'what': 'servicios', 'place': 'nuestro estudio',
        'headlines': ('{name}: soluciones claras{place}', 'Asesoría que resuelve{place}', '{name}{place}'),
        'service_line': 'Trabajamos en {what} con un proceso claro{services}.',
        'cta_label': 'Pedir una consulta', 'cta_title': 'Contanos qué necesitás resolver',
        'cta_text': 'Dejanos tu consulta y coordinamos una primera conversación sin compromiso.',
    },
    'salud': {
        'what': 'tratamientos', 'place': 'nuestro consultorio',
        'headlines': ('{name}: tu salud en buenas manos{place}', 'Cuidarte es nuestro trabajo{place}', '{name}{place}'),
        'service_line': 'Ofrecemos {what} con seguimiento profesional{services}.',
        'cta_label': 'Pedir un turno', 'cta_title': 'Reservá tu turno',
        'cta_text': 'Escribinos con el día que te queda cómodo y te confirmamos el horario.',
    },
    'belleza': {
        'what': 'servicios', 'place': 'nuestro espacio',
        'headlines': ('{name}: tu mejor versión{place}', 'Belleza con detalle{place}', '{name}{place}'),
        'service_line': 'Hacemos {what} pensados para vos{services}.',
        'cta_label': 'Reservar turno', 'cta_title': 'Reservá tu turno',
        'cta_text': 'Elegí el servicio y el día: te confirmamos el horario por WhatsApp.',
    },
    'construccion': {
        'what': 'obras', 'place': 'nuestro taller',
        'headlines': ('{name}: obras que duran{place}', 'Del plano a la obra{place}', '{name}{place}'),
        'service_line': 'Ejecutamos {what} con materiales de primera{services}.',
        'cta_label': 'Pedir presupuesto', 'cta_title': 'Pedí el presupuesto de tu obra',
        'cta_text': 'Contanos qué tenés en mente y te pasamos un presupuesto claro, sin sorpresas.',
    },
    'tecnologia': {
        'what': 'soluciones', 'place': 'nuestro equipo',
        'headlines': ('{name}: tecnología que funciona{place}', 'Menos fricción, más resultados{place}', '{name}{place}'),
        'service_line': 'Armamos {what} a medida de tu negocio{services}.',
        'cta_label': 'Ver soluciones', 'cta_title': 'Veamos cómo resolverlo',
        'cta_text': 'Contanos el problema y te proponemos un camino concreto para resolverlo.',
    },
    'educacion': {
        'what': 'cursos', 'place': 'nuestra institución',
        'headlines': ('{name}: aprendé con nosotros{place}', 'Formación que sirve{place}', '{name}{place}'),
        'service_line': 'Dictamos {what} con docentes en actividad{services}.',
        'cta_label': 'Ver cursos', 'cta_title': 'Inscribite al próximo curso',
        'cta_text': 'Consultá fechas, modalidad y aranceles: te respondemos con todo el detalle.',
    },
    'turismo': {
        'what': 'experiencias', 'place': 'nuestra agencia',
        'headlines': ('{name}: experiencias para recordar{place}', 'Salí a descubrir{place}', '{name}{place}'),
        'service_line': 'Organizamos {what} con todo resuelto{services}.',
        'cta_label': 'Ver experiencias', 'cta_title': 'Armemos tu próxima salida',
        'cta_text': 'Contanos fechas y cantidad de personas: te pasamos opciones y precios.',
    },
    'mascotas': {
        'what': 'productos y servicios', 'place': 'nuestro local',
        'headlines': ('{name}: cuidado con amor{place}', 'Todo para tu mascota{place}', '{name}{place}'),
        'service_line': 'Ofrecemos {what} para su bienestar{services}.',
        'cta_label': 'Ver productos', 'cta_title': 'Consultanos por tu mascota',
        'cta_text': 'Escribinos y te asesoramos según la edad, el tamaño y las necesidades.',
    },
    'arte': {
        'what': 'piezas', 'place': 'nuestro taller',
        'headlines': ('{name}: piezas únicas{place}', 'Hecho a mano, hecho para vos{place}', '{name}{place}'),
        'service_line': 'Creamos {what} de autor, una por una{services}.',
        'cta_label': 'Ver obras', 'cta_title': 'Conocé las piezas disponibles',
        'cta_text': 'Escribinos por la pieza que te gustó: coordinamos entrega y envío.',
    },
    'seguridad': {
        'what': 'equipos y servicios', 'place': 'nuestro local',
        'headlines': ('{name}: seguridad que responde{place}', 'Protegé lo que te importa{place}', '{name}{place}'),
        'service_line': 'Ofrecemos {what} de seguridad y prevención{services}.',
        'cta_label': 'Pedir asesoramiento', 'cta_title': 'Consultanos por tu seguridad',
        'cta_text': 'Escribinos y te asesoramos sobre extintores, recargas, EPP y certificaciones.',
    },
    'otro': {
        'what': 'servicios', 'place': 'nuestro negocio',
        'headlines': ('{name}: lo que hacemos, bien hecho{place}', 'Conocé lo que ofrecemos{place}', '{name}{place}'),
        'service_line': 'Ofrecemos {what} con atención personalizada{services}.',
        'cta_label': 'Consultar', 'cta_title': 'Hablemos de lo que necesitás',
        'cta_text': 'Dejanos tu consulta y te respondemos a la brevedad.',
    },
}

#Apertura y cierre de la descripción según el tono elegido. El cuerpo es
#siempre el mismo (datos reales); lo que cambia es cómo se dice.
TONE_COPY                   =   {
    'calido': {
        'open':     'En {name} te recibimos con tiempo y dedicación',
        'close':    'Pasá por {place} o escribinos: nos gusta explicar antes de que compres.',
        'headline': '',
    },
    'serio': {
        'open':     '{name} es un negocio dedicado a lo que hace',
        'close':    'Trabajamos con criterio y dejamos todo por escrito antes de avanzar.',
        'headline': '',
    },
    'moderno': {
        'open':     '{name} hace simple lo que otros complican',
        'close':    'Todo lo que necesitás, en un solo lugar y a un mensaje de distancia.',
        'headline': '',
    },
    'audaz': {
        'open':     '{name}. Sin vueltas',
        'close':    'Si buscás algo distinto, es por acá.',
        'headline': '',
    },
}

#Títulos por defecto de los bloques cuando el dueño no puso uno.
GENERIC_TITLES              =   {
    'featured': 'Destacados', 'categories': 'Categorías', 'services': 'Qué ofrecemos',
    'about': 'Sobre nosotros', 'stats': 'Nuestros números', 'benefits': 'Por qué elegirnos',
    'offers': 'Ofertas', 'brands': 'Marcas', 'gallery': 'Galería', 'testimonials': 'Opiniones',
    'faq': 'Preguntas frecuentes', 'team': 'Equipo', 'timeline': 'Trayectoria',
    'steps': 'Cómo funciona', 'video': 'Video', 'compare': 'Comparativa',
    'contact': 'Contacto', 'cta': 'Hablemos',
}


def _clip(text, limit):
    #Recorte limpio: nunca corta una palabra al medio y respeta el tope.
    text    =   ' '.join(str(text or '').split())
    if len(text) <= limit:
        return text
    cut     =   text[:limit]
    space   =   cut.rfind(' ')
    return (cut[:space] if space > limit * 0.6 else cut).rstrip(' ,.;:-')


def _name_of(store, customization):
    #Nombre visible primero; si no hay, el del perfil; nunca el slug crudo.
    profile =   getattr(store, 'user', None)
    return  (
        customization.display_name
        or (getattr(profile, 'first_name', '') or '').strip()
        or 'Nuestro negocio'
    )


def _city_of(store):
    #store.user es el UserProfile: la ciudad vive ahí (no en el auth User).
    city    =   getattr(getattr(store, 'user', None), 'city', None)
    return  getattr(city, 'name_city', '') or ''


def _context(store, customization, rubro, facts, stats):
    copy    =   RUBRO_COPY.get(rubro) or RUBRO_COPY['otro']
    name    =   _name_of(store, customization)
    city    =   _city_of(store)
    years   =   customization.about_years
    specs   =   (customization.about_specialties or '').strip()
    #Servicios como "A, B y C": dos alcanzan para dar idea sin enumerar todo.
    titles  =   [str(row.get('title') or '').strip() for row in (customization.services or []) if isinstance(row, dict)]
    titles  =   [t for t in titles if t][:2]
    return {
        'name'          :   name,
        'place'         :   f' de {city}' if city else '',
        'city'          :   city,
        'city_clause'   :   f' en {city}' if city else '',
        'years_clause'  :   f' desde hace {years} años' if years else '',
        'spec_clause'   :   f', especializados en {specs}' if specs else '',
        'services'      :   (' como ' + ', '.join(titles)) if titles else '',
        'what'          :   copy['what'],
        'place_name'    :   copy['place'],
        'products'      :   stats.get('products', 0),
        'categories'    :   stats.get('categories', 0),
        'images'        :   stats.get('images', 0),
        'gallery'       :   stats.get('gallery', 0),
    }


def build(store, customization, rubro, tone, facts, stats, rng):
    """
    Copy de la propuesta: {headline, description, cta_title, cta_text,
    cta_label}. Todo sale de plantillas + datos reales; la semilla solo
    elige entre variantes igual de válidas.
    """
    copy    =   RUBRO_COPY.get(rubro) or RUBRO_COPY['otro']
    flavor  =   TONE_COPY.get(tone) or TONE_COPY['moderno']
    ctx     =   _context(store, customization, rubro, facts, stats)

    headline    =   rng.choice(copy['headlines']).format(**ctx)
    #El titular con solo el nombre se queda corto: le sumamos el rubro.
    if ctx['name'] in headline and len(headline) < 18:
        headline    =   f"{ctx['name']}: {copy['what']} con atención directa{ctx['place']}"

    parts       =   [flavor['open'].format(**ctx) + ctx['city_clause'] + ctx['years_clause'] + ctx['spec_clause'] + '.']
    parts.append(copy['service_line'].format(**ctx))
    if facts.get('products'):
        parts.append(f'Hoy tenemos {ctx["products"]} {copy["what"]} publicados en el catálogo.')
    if facts.get('categories'):
        parts.append(f'Están organizados en {ctx["categories"]} categorías para encontrarlos rápido.')
    if facts.get('gallery') or facts.get('images'):
        parts.append('En la galería vas a ver cómo trabajamos.')
    if facts.get('testimonials'):
        parts.append('Y podés leer lo que dicen quienes ya nos eligieron.')
    parts.append(flavor['close'].format(**{**ctx, 'place': ctx['place_name']}))

    return {
        'headline'      :   _clip(headline, _HEADLINE_MAX),
        'description'   :   _clip(' '.join(parts), _DESCRIPTION_MAX),
        'cta_title'     :   _clip(copy['cta_title'], _CTA_TITLE_MAX),
        'cta_text'      :   _clip(copy['cta_text'], _CTA_TEXT_MAX),
        'cta_label'     :   _clip(copy['cta_label'], _CTA_LABEL_MAX),
    }


def title_for(block_id, rubro):
    """Título de sección para props.title del borrador (nunca inventa un bloque)."""
    specific    =   (R.BLOCK_TITLES.get(rubro) or {}).get(block_id)
    return _clip(specific or GENERIC_TITLES.get(block_id) or '', 80)


#=========================================
# BORRADORES DE NEGOCIO (autofill de "Diseñar con IA")
#=========================================
#Lo que el dueño "no sabe qué escribir": sobre nosotros, misión, FAQs,
#servicios, pasos y un anuncio. Frases es-AR neutras, sin números, precios
#ni promesas verificables (nada de horarios, envíos o garantías que el
#negocio no declaró). Son un punto de partida editable, no datos.
DRAFT_MISSIONS              =   {
    'comercio':     'Queremos que comprar acá sea simple: lo que buscás, con alguien que te asesora y te dice la verdad.',
    'gastronomia':  'Queremos que cada visita se sienta como en casa: cocina cuidada, atención con tiempo y ganas de que vuelvas.',
    'indumentaria': 'Queremos que encuentres prendas que te representen, elegidas con criterio y sin apuro.',
    'servicios_profesionales': 'Queremos resolver tu problema con un proceso claro: qué hacemos, cuánto lleva y qué necesitamos de vos.',
    'salud':        'Queremos que te sientas escuchado: atención con tiempo, explicaciones claras y seguimiento.',
    'belleza':      'Queremos que salgas conforme con lo que ves y con cómo te tratamos durante el turno.',
    'construccion': 'Queremos que la obra salga como la pensaste: presupuesto claro, plazos acordados y trabajo prolijo.',
    'tecnologia':   'Queremos que la tecnología te resuelva, no que te complique: soluciones concretas y explicadas sin tecnicismos.',
    'educacion':    'Queremos que aprendas de verdad: contenidos aplicables y acompañamiento durante el curso.',
    'turismo':      'Queremos que disfrutes el viaje y no te ocupes de la logística: todo coordinado y explicado antes de salir.',
    'mascotas':     'Queremos que tu mascota esté bien y que vos te vayas tranquilo, con indicaciones claras.',
    'arte':         'Queremos que cada pieza llegue a alguien que la valore: trabajo de autor, hecho de a una.',
    'seguridad':    'Queremos que estés cubierto: asesoramiento técnico, equipos certificados y respuesta cuando la necesitás.',
    'otro':         'Queremos que sepas qué esperar de nosotros: atención directa, trabajo cuidado y respuestas claras.',
}

#Primera pregunta frecuente por rubro (la que de verdad frena la consulta).
DRAFT_FIRST_FAQ             =   {
    'comercio':     ('¿Cómo hago un pedido?', 'Escribinos por el formulario de contacto o por WhatsApp y te confirmamos cómo seguir.'),
    'gastronomia':  ('¿Cómo reservo una mesa?', 'Escribinos por el formulario o por WhatsApp y te confirmamos la reserva.'),
    'indumentaria': ('¿Cómo consulto por un talle?', 'Escribinos por el formulario o por WhatsApp con el modelo que te interesa y te respondemos.'),
    'servicios_profesionales': ('¿Cómo pido una consulta?', 'Dejanos tu consulta en el formulario de la web y coordinamos una primera conversación.'),
    'salud':        ('¿Cómo pido un turno?', 'Escribinos por el formulario o por WhatsApp y te confirmamos el horario disponible.'),
    'belleza':      ('¿Cómo reservo un turno?', 'Elegí el servicio y escribinos por el formulario o por WhatsApp: te confirmamos el día.'),
    'construccion': ('¿Cómo pido un presupuesto?', 'Contanos qué tenés en mente por el formulario de la web y coordinamos una visita.'),
    'tecnologia':   ('¿Cómo empiezo?', 'Contanos el problema por el formulario y te proponemos un camino concreto.'),
    'educacion':    ('¿Cómo me inscribo?', 'Consultá por el formulario de la web: te pasamos fechas y modalidad.'),
    'turismo':      ('¿Cómo reservo una experiencia?', 'Escribinos con las fechas y la cantidad de personas y te pasamos las opciones.'),
    'mascotas':     ('¿Cómo pido un turno?', 'Escribinos por el formulario o por WhatsApp y coordinamos la atención.'),
    'arte':         ('¿Cómo consulto por una pieza?', 'Escribinos por la obra que te gustó y coordinamos la entrega.'),
    'seguridad':    ('¿Cómo pido un asesoramiento?', 'Contanos qué necesitás proteger por el formulario de la web y te asesoramos sin compromiso.'),
    'otro':         ('¿Cómo hago una consulta?', 'Escribinos por el formulario de contacto de la web y te respondemos a la brevedad.'),
}


def _about_text(ctx, copy, flavor, facts):
    parts   =   [flavor['open'].format(**ctx) + ctx['city_clause'] + ctx['years_clause'] + ctx['spec_clause'] + '.']
    parts.append(copy['service_line'].format(**ctx))
    parts.append('Cada consulta la responde alguien del negocio: sin intermediarios y con el detalle que necesitás.')
    if facts.get('products'):
        parts.append(f'En la web podés ver los {ctx["products"]} {copy["what"]} que tenemos publicados.')
    elif facts.get('gallery'):
        parts.append('En la galería vas a ver cómo trabajamos.')
    parts.append(flavor['close'].format(**{**ctx, 'place': ctx['place_name']}))
    return ' '.join(parts)


def _faqs(rubro, ctx, facts):
    first       =   DRAFT_FIRST_FAQ.get(rubro) or DRAFT_FIRST_FAQ['otro']
    rows        =   [
        {'q': _clip(first[0], _FAQ_Q_MAX), 'a': _clip(first[1], _FAQ_A_MAX)},
        {'q': '¿Cómo sé qué me conviene?', 'a': _clip('Contanos qué buscás y te orientamos: si algo no es para vos, te lo decimos.', _FAQ_A_MAX)},
    ]
    if facts.get('products') or facts.get('gallery'):
        rows.append({'q': '¿Puedo ver antes de decidir?', 'a': _clip('Sí: en el catálogo y la galería de la web vas a encontrar lo que hacemos.', _FAQ_A_MAX)})
    else:
        rows.append({'q': '¿Dónde puedo ver más?', 'a': _clip('Escribinos y te compartimos más detalles de lo que necesitás.', _FAQ_A_MAX)})
    return rows


def _services(copy, ctx):
    rows        =   [
        ('Asesoramiento personalizado', f'Te ayudamos a elegir {copy["what"]} según lo que necesitás.'),
        ('Atención directa', 'Hablás con el negocio, no con un robot: consultás por la web y te respondemos.'),
        ('Seguimiento', 'Después de tu consulta seguimos disponibles para lo que necesites.'),
    ]
    return [{'name': _clip(name, _SERVICE_NAME_MAX), 'desc': _clip(text.format(**ctx), _SERVICE_DESC_MAX)} for name, text in rows]


def _steps(ctx):
    rows        =   [
        ('Contanos qué necesitás', 'Escribinos por el formulario de contacto o por el botón de WhatsApp.'),
        ('Te respondemos', 'Confirmamos los detalles de lo que buscás, sin compromiso.'),
        ('Coordinamos', 'Acordamos cómo seguir: entrega, turno o visita, según tu caso.'),
    ]
    return [{'title': _clip(title, _STEP_TITLE_MAX), 'desc': _clip(text, _STEP_DESC_MAX)} for title, text in rows]


def draft_business_fields(store, customization, rubro, tone, facts, stats, rng):
    """
    copy_draft de la propuesta: SOLO los campos de negocio que están vacíos,
    con los topes del modelo. Nunca devuelve testimonios, cifras, precios,
    contacto, redes ni horarios — el motor no inventa datos del negocio.
    """
    copy        =   RUBRO_COPY.get(rubro) or RUBRO_COPY['otro']
    flavor      =   TONE_COPY.get(tone) or TONE_COPY['moderno']
    ctx         =   _context(store, customization, rubro, facts, stats)
    draft       =   {}
    if not str(customization.about_text or '').strip():
        draft['about_text']         =   _clip(_about_text(ctx, copy, flavor, facts), _ABOUT_MAX)
    if not str(customization.about_mission or '').strip():
        draft['about_mission']      =   _clip(DRAFT_MISSIONS.get(rubro, DRAFT_MISSIONS['otro']), _MISSION_MAX)
    if not (customization.faqs or []):
        draft['faqs']               =   _faqs(rubro, ctx, facts)
    if not (customization.services or []):
        draft['services']           =   _services(copy, ctx)
    if not (customization.service_steps or []):
        draft['steps']              =   _steps(ctx)
    if not (customization.announcements or []):
        draft['announcements']      =   [{'text': _clip(f'{ctx["name"]}: novedades y propuestas para vos', _ANNOUNCEMENT_MAX)}]
    return draft
