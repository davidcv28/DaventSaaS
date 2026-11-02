from McpApp.domains.skills.services.services import (
    apply_style,
    catalog_summary,
    design_payload,
    get_design_pattern,
    get_design_style,
    list_categories,
    list_design_patterns,
    list_design_styles,
    pattern_payload,
    propose_design,
    search_design_styles,
)

"""
Herramientas MCP del dominio skills.

Un único lugar declara el contrato (nombre, descripción y JSON Schema) y
el handler que lo ejecuta. Lo consumen:
  - McpApp/mcp_server.py (transporte stdio, para agentes locales)
  - POST /api/mcp/ (JSON-RPC sobre HTTP, para agentes remotos)
"""

SERVER_NAME     =   'davent-skills'
SERVER_VERSION  =   '1.0.0'

#=========================================
# TOOL SCHEMAS
#=========================================
TOOLS   =   [
    {
        'name'          :   'list_design_styles',
        'description'   :   'Lista los estilos de diseño disponibles, opcionalmente filtrados por categoría (moda, tecnologia, alimentos, ...).',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {
                'categoria' :   {'type': 'string', 'description': 'Categoría exacta del estilo.'},
                'limit'     :   {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10},
            },
        },
    },
    {
        'name'          :   'search_design_styles',
        'description'   :   'Búsqueda semántica por texto libre y tags (ej: "oscuro neon gamer"). Devuelve los estilos más afines.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {
                'query'     :   {'type': 'string', 'description': 'Texto libre: rubro, tono, color, adjetivo.'},
                'categoria' :   {'type': 'string'},
                'tags'      :   {'type': 'array', 'items': {'type': 'string'}},
                'limit'     :   {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10},
            },
        },
    },
    {
        'name'          :   'get_design_style',
        'description'   :   'Devuelve un estilo completo por slug: tokens de diseño y bloques HTML por componente.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {'slug': {'type': 'string', 'description': 'Slug único del estilo (ej: cyberpunk-dark).'}},
            'required'  :   ['slug'],
        },
    },
    {
        'name'          :   'apply_design_style',
        'description'   :   'Devuelve el estilo en formato aplicable (tokens + componentes + instrucciones) para generar componentes nuevos coherentes.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {'slug': {'type': 'string'}},
            'required'  :   ['slug'],
        },
    },
    {
        'name'          :   'list_design_categories',
        'description'   :   'Lista las categorías de diseño con la cantidad de estilos de cada una.',
        'inputSchema'   :   {'type': 'object', 'properties': {}},
    },
    {
        'name'          :   'design_catalog_summary',
        'description'   :   'Catálogo compacto (slug, nombre, categoría, tags) para inyectar en el contexto de un modelo.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 50}},
        },
    },
    {
        'name'          :   'list_design_patterns',
        'description'   :   'Lista los patrones de diseño reales del producto (DesignPattern activos): plantilla, tier, tags y si tienen markup propio.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {
                'categoria' :   {'type': 'string'},
                'limit'     :   {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10},
            },
        },
    },
    {
        'name'          :   'get_design_pattern',
        'description'   :   'Devuelve un patrón completo por slug: layout por superficie, tokens del contrato y estilo asociado.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {'slug': {'type': 'string'}},
            'required'  :   ['slug'],
        },
    },
    {
        'name'          :   'propose_design',
        'description'   :   'Resuelve el diseño que elegiría el wizard "Diseño asistido" para un pedido {rubro, goals[], tone, audience, must_have[], notes}: patrón + estilo con layout y tokens.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {
                'rubro'     :   {'type': 'string', 'description': 'Id del rubro (ej: gastronomia, moda, tecnologia).'},
                'goals'     :   {'type': 'array', 'items': {'type': 'string'}},
                'tone'      :   {'type': 'string'},
                'audience'  :   {'type': 'string'},
                'must_have' :   {'type': 'array', 'items': {'type': 'string'}},
                'notes'     :   {'type': 'string'},
            },
        },
    },
]


#=========================================
# DISPATCH
#=========================================
def call_tool(name : str, arguments : dict | None = None) -> dict:
    args    =   arguments or {}
    if name == 'list_design_styles':
        rows    =   list_design_styles(categoria = args.get('categoria', ''), limit = args.get('limit', 10))
        return {'styles': [design_payload(s, full = False) for s in rows]}
    if name == 'search_design_styles':
        rows    =   search_design_styles(
            query       =   args.get('query', ''),
            categoria   =   args.get('categoria', ''),
            tags        =   args.get('tags') or [],
            limit       =   args.get('limit', 10),
        )
        return {'styles': [design_payload(s, full = False) for s in rows]}
    if name == 'get_design_style':
        style   =   get_design_style(args.get('slug', ''))
        if style is None:
            raise ValueError(f'No existe el estilo "{args.get("slug", "")}".')
        return design_payload(style, full = True)
    if name == 'apply_design_style':
        style   =   apply_style(args.get('slug', ''))
        if style is None:
            raise ValueError(f'No existe el estilo "{args.get("slug", "")}".')
        return style
    if name == 'list_design_categories':
        return {'categories': list_categories()}
    if name == 'design_catalog_summary':
        return {'catalog': catalog_summary(limit = args.get('limit', 50))}
    if name == 'list_design_patterns':
        return {'patterns': [
            pattern_payload(p) for p in list_design_patterns(
                categoria = args.get('categoria', ''), limit = args.get('limit', 10),
            )
        ]}
    if name == 'get_design_pattern':
        pattern =   get_design_pattern(args.get('slug', ''))
        if pattern is None:
            raise ValueError(f'No existe el patrón "{args.get("slug", "")}".')
        return pattern_payload(pattern, full = True)
    if name == 'propose_design':
        proposal    =   propose_design(args)
        if proposal is None:
            raise ValueError('Sin patrón elegible para ese pedido (catálogo vacío).')
        return proposal
    raise ValueError(f'Herramienta desconocida: {name}')


def tools_list() -> list[dict]:
    return TOOLS
