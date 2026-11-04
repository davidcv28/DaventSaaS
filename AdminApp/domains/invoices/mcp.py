"""
Tools MCP del dominio invoices — solo las facturas del usuario en sesión.
"""

from McpApp.domains.skills.services.services import clamp_limit

TOOLS   =   [
    {
        'name'          :   'my_invoices',
        'description'   :   'Tus últimas facturas: tipo, número, total, fecha de emisión y estado ARCA.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10}},
        },
    },
]


def my_invoices(user, limit : int = 10) -> dict:
    from AdminApp.domains.invoices.models import Invoice
    profile =   getattr(user, 'profile', None)
    if profile is None:
        return {'invoices': []}
    rows    =   Invoice.objects.filter(user = profile).order_by('-created_at')[:clamp_limit(limit)]
    return {
        'invoices': [
            {
                'type'          :   i.type,
                'number'        :   i.number,
                'total'         :   str(i.total),
                'issued_at'     :   i.issued_at.isoformat(),
                'afip_status'   :   i.afip_status,
            }
            for i in rows
        ],
    }


def call(name : str, args : dict, user) -> dict:
    if name == 'my_invoices':
        return my_invoices(user, limit = args.get('limit', 10))
    raise ValueError(f'Herramienta desconocida en invoices: {name}')
