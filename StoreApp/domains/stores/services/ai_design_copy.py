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
