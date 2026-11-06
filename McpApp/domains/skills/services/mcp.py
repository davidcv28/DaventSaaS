from McpApp.domains.skills.services.dashboard_map import DASHBOARD_MAP
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
    search_design_styles,
)

"""
Herramientas MCP del dominio skills.

Un único lugar declara el contrato (nombre, descripción y JSON Schema) y
el handler que lo ejecuta. Lo consumen:
  - McpApp/mcp_server.py (transporte stdio, para agentes locales)
  - POST /api/mcp/ (JSON-RPC sobre HTTP, para agentes remotos)
"""

from McpApp.domains.skills.services.user_tools import (
    call_user_tool,
    mcp_user_access,
    user_tool_names,
    user_tool_schemas,
)

SERVER_NAME     =   'davent-skills'
SERVER_VERSION  =   '1.0.0'

#Tools de usuario: las declara cada dominio en <dominio>/mcp.py y las
#agrega user_tools. Solo corren con `user` inyectado por el transporte y
#suscripción vigente no-trial (mcp_user_access); nunca leen datos ajenos.
def _user_tools() -> set:
    return user_tool_names()

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
        'name'          :   'dashboard_guide',
        'description'   :   'Mapa del dashboard de DAVENT: secciones del menú lateral, pestañas internas y deep links. Solo orientación de UI — no devuelve datos de ninguna cuenta.',
        'inputSchema'   :   {'type': 'object', 'properties': {}},
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
]


#=========================================
# DISPATCH
#=========================================
def call_tool(name : str, arguments : dict | None = None, user = None) -> dict:
    args    =   arguments or {}
    if name in _user_tools():
        #Fail-closed: sin sesión con plan pago vigente la tool no corre.
        if not mcp_user_access(user):
            raise ValueError('Esta herramienta requiere sesión con un plan vigente (básico, estándar o premium).')
        return call_user_tool(name, args, user)
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
    if name == 'dashboard_guide':
        return {'guide': DASHBOARD_MAP}
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
    raise ValueError(f'Herramienta desconocida: {name}')


def tools_list(user = None) -> list[dict]:
    #Sin acceso de usuario las tools personales ni se anuncian: un agente
    #ajeno no puede ni descubrir su contrato.
    if not mcp_user_access(user):
        return TOOLS
    return TOOLS + user_tool_schemas()
