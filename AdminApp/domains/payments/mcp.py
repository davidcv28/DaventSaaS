"""
Tools MCP del dominio payments — solo los pagos del usuario en sesión.
"""

from McpApp.domains.skills.services.services import clamp_limit

TOOLS   =   [
    {
        'name'          :   'my_payments',
        'description'   :   'Tus últimos pagos: monto, moneda, estado y fecha.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10}},
        },
    },
]


def my_payments(user, limit : int = 10) -> dict:
    from AdminApp.domains.payments.models import Payment
    profile =   getattr(user, 'profile', None)
    if profile is None:
        return {'payments': []}
    rows    =   Payment.objects.filter(user = profile).order_by('-created_at')[:clamp_limit(limit)]
    return {
        'payments': [
            {
                'amount'    :   str(p.amount),
                'currency'  :   p.currency,
                'status'    :   p.status,
                'paid_at'   :   p.paid_at.isoformat() if p.paid_at else None,
                'created_at':   p.created_at.isoformat(),
            }
            for p in rows
        ],
    }


def call(name : str, args : dict, user) -> dict:
    if name == 'my_payments':
        return my_payments(user, limit = args.get('limit', 10))
    raise ValueError(f'Herramienta desconocida en payments: {name}')
