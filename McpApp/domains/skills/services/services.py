from django.db.models import Count, Q

from McpApp.domains.skills.models import DesignModelMcp

"""
Servicios del dominio skills: búsqueda y lectura de estilos.

La búsqueda combina slug (exacto, indexado), categoría y tags (búsqueda
semántica simple por solapamiento de palabras clave). Nunca expone
consultas fuera del queryset: el MCP solo lee.
"""

DEFAULT_LIMIT   =   10
MAX_LIMIT       =   50


#=========================================
# SERIALIZACIÓN
#=========================================
def design_payload(style : DesignModelMcp, full : bool = True) -> dict:
    data    =   {
        'id'            :   style.id,
        'slug'          :   style.slug,
        'nombre'        :   style.nombre,
        'categoria'     :   style.categoria,
        'tags'          :   list(style.tags or []),
        'created_at'    :   style.created_at.isoformat(),
    }
    if full:
        data['html_componentes']    =   style.html_componentes or {}
        data['tokens_diseno']       =   style.tokens_diseno or {}
    return data


#=========================================
# LECTURA
#=========================================
def get_design_style(slug : str) -> DesignModelMcp | None:
    return DesignModelMcp.objects.filter(slug = slug).first()


def list_design_styles(categoria : str = '', limit : int = DEFAULT_LIMIT) -> list[DesignModelMcp]:
    qs  =   DesignModelMcp.objects.all()
    if categoria:
        qs  =   qs.filter(categoria__iexact = categoria)
    return list(qs[:clamp_limit(limit)])


def search_design_styles(query : str = '', categoria : str = '', tags : list | None = None, limit : int = DEFAULT_LIMIT) -> list[DesignModelMcp]:
    qs      =   DesignModelMcp.objects.all()
    if categoria:
        qs  =   qs.filter(categoria__iexact = categoria)
    terms   =   [t.strip().lower() for t in (query or '').replace(',', ' ').split() if t.strip()]
    if terms:
        #Cada término puede pegar en slug, nombre, categoría o tags.
        condition   =   Q()
        for term in terms:
            condition  |=  (
                Q(slug__icontains = term)
                | Q(nombre__icontains = term)
                | Q(categoria__icontains = term)
                | Q(tags__icontains = term)
            )
        qs  =   qs.filter(condition)
    if tags:
        for tag in [t.strip().lower() for t in tags if t and t.strip()]:
            qs  =   qs.filter(tags__icontains = tag)
    rows    =   list(qs.distinct()[:MAX_LIMIT * 4])
    if terms:
        #Relevancia: slug/nombre pesan más que categoría y tags. Sin esto
        #un match flojo de tag desplazaba al estilo que realmente buscaba.
        def score(style):
            haystack = ' '.join([style.slug, style.nombre, style.categoria, ' '.join(style.tags or [])]).lower()
            strong   = (style.slug + ' ' + style.nombre).lower()
            return sum((3 if term in strong else 1) for term in terms if term in haystack)
        rows.sort(key = score, reverse = True)
    return rows[:clamp_limit(limit)]


def list_categories() -> list[dict]:
    rows    =   (
        DesignModelMcp.objects
        .values('categoria')
        .annotate(total = Count('id'))
        .order_by('categoria')
    )
    return [{'categoria': row['categoria'], 'total': row['total']} for row in rows]


def catalog_summary(limit : int = MAX_LIMIT) -> list[dict]:
    #Catálogo compacto para el system prompt del asistente de diseño.
    return [
        {'slug': s.slug, 'nombre': s.nombre, 'categoria': s.categoria, 'tags': list(s.tags or [])}
        for s in DesignModelMcp.objects.all()[:clamp_limit(limit)]
    ]


def apply_style(slug : str) -> dict | None:
    style   =   get_design_style(slug)
    if style is None:
        return None
    return {
        'slug'              :   style.slug,
        'nombre'            :   style.nombre,
        'tokens_diseno'     :   style.tokens_diseno or {},
        'html_componentes'  :   style.html_componentes or {},
        'instrucciones'     :   (
            'Usá tokens_diseno como fuente de verdad para colores, fuentes y bordes. '
            'Reutilizá las clases Tailwind de html_componentes para componentes nuevos; '
            'no inventes colores fuera de la paleta.'
        ),
    }


def clamp_limit(value) -> int:
    try:
        value   =   int(value)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(value, MAX_LIMIT))
